"""
app/services/ocr_pipeline.py
Orchestrates the full OCR pipeline:

  Upload
  → Create ocr_processing record (PENDING)
  → Download file from storage
  → Call GeminiReceiptExtractor (PROCESSING → EXTRACTED)
  → Normalize (NORMALIZED)
  → Validate
  → Persist to claim_extracted_data (COMPLETED)
  → Update claims.ocr_status

Idempotency:
  - If document already has COMPLETED processing, returns existing result.
  - If FAILED, allows reprocessing.
  - Does not create duplicate extracted_data for the same processing attempt.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

from app.core.database import supabase
from app.core.logging import get_logger
from app.services.extraction import get_extractor, ExtractionResult
from app.services.normalization import normalize_receipt_data
from app.services.validation import validate_receipt
from app.services import storage as storage_service
from app.services.verification.engine import run_verification

logger = get_logger(__name__)


class OcrPipelineError(Exception):
    """Raised when the OCR pipeline encounters a non-retryable error."""
    pass


def _json_serialise(obj):
    """JSON serialiser that handles Decimal, date, etc."""
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def _to_json_safe(data: dict | list) -> dict | list:
    """Convert a dict/list to JSON-safe format (no Decimals/dates)."""
    return json.loads(json.dumps(data, default=_json_serialise))


def process_document(
    document_id: str,
    force_reprocess: bool = False,
    file_data: bytes | None = None,
    mime_type: str | None = None,
) -> dict:
    """
    Run the full OCR pipeline for a document.

    Returns a dict with:
      - document_id
      - status
      - extracted_data (if successful)
      - message
    """
    import time
    start_time = time.time()

    # 1. Fetch the document record
    logger.info(f"[OCR Pipeline] >>> Request to process document_id={document_id} (force_reprocess={force_reprocess})")
    doc_result = supabase.table("claim_documents") \
        .select("*").eq("id", document_id).single().execute()
    if not doc_result.data:
        logger.error(f"[OCR Pipeline] Document {document_id} not found in database")
        raise OcrPipelineError(f"Document {document_id} not found")

    doc = doc_result.data
    claim_id = doc["claim_id"]
    filename = doc.get("file_name", "unknown")

    # 2. Check for existing COMPLETED processing (idempotency)
    if not force_reprocess:
        existing = supabase.table("ocr_processing") \
            .select("*").eq("document_id", document_id) \
            .eq("status", "COMPLETED").execute()

        if existing.data:
            logger.info(
                f"[OCR Pipeline] Document already processed (status=COMPLETED). "
                f"Returning cached extracted data for document_id={document_id}"
            )

            # Fetch extracted data
            extracted = supabase.table("claim_extracted_data") \
                .select("*").eq("document_id", document_id).execute()

            return {
                "document_id": document_id,
                "status": "COMPLETED",
                "message": "Document already processed. Use force_reprocess=true to re-extract.",
                "extracted_data": extracted.data[0] if extracted.data else None,
                "ocr_processing": existing.data[0],
            }

    # 3. Create or reuse ocr_processing record
    processing_id = _get_or_create_processing(document_id, force_reprocess)
    now = datetime.now(timezone.utc).isoformat()
    logger.info(f"[OCR Pipeline] Processing run initialized: processing_id={processing_id}")

    try:
        # 4. Mark as PROCESSING
        _update_processing(processing_id, {
            "status": "PROCESSING",
            "started_at": now,
            "error_code": None,
            "error_message": None,
        })

        # 5. File source (in-memory or download from storage)
        if file_data is None:
            storage_path = doc.get("storage_path")
            if not storage_path:
                raise OcrPipelineError("Document has no storage_path — was it uploaded via Storage?")

            t_dl = time.time()
            logger.info(f"[OCR Pipeline] [1/5] Downloading '{filename}' from Supabase Storage: '{storage_path}'...")
            file_data = storage_service.download_receipt(storage_path)
            mime_type = doc.get("mime_type", "application/pdf")
            logger.info(f"[OCR Pipeline] [1/5] Downloaded {len(file_data):,} bytes ({mime_type}) in {time.time() - t_dl:.2f}s")
        else:
            mime_type = mime_type or doc.get("mime_type", "application/pdf")
            logger.info(f"[OCR Pipeline] [1/5] Using in-memory file data ({len(file_data):,} bytes, {mime_type}) — skipped Supabase Storage download!")

        # 6. Extract via Gemini
        t_ext = time.time()
        extractor = get_extractor()
        model_name = getattr(extractor, "_model", "Gemini")
        logger.info(f"[OCR Pipeline] [2/5] Sending file to Gemini Vision AI ({model_name})...")
        result: ExtractionResult = extractor.extract(file_data, mime_type)
        raw_ext = result.extracted_data or {}
        logger.info(
            f"[OCR Pipeline] [2/5] Gemini extraction finished in {time.time() - t_ext:.2f}s | "
            f"Raw Merchant='{raw_ext.get('merchant')}', Total={raw_ext.get('total')}, "
            f"Currency='{raw_ext.get('currency')}', Date='{raw_ext.get('transaction_date')}', "
            f"Items={len(raw_ext.get('line_items') or [])}"
        )

        # Store raw response
        _update_processing(processing_id, {
            "status": "EXTRACTED",
            "raw_response": _to_json_safe(result.raw_response),
        })

        # 7. Normalize
        logger.info("[OCR Pipeline] [3/5] Normalizing extracted fields...")
        normalized = normalize_receipt_data(result.extracted_data)
        logger.info(
            f"[OCR Pipeline] [3/5] Normalization complete -> "
            f"Merchant: '{normalized.get('merchant_normalized')}', "
            f"Total: {normalized.get('total')} {normalized.get('currency')}, "
            f"Date: {normalized.get('transaction_date')}, "
            f"Invoice#: '{normalized.get('invoice_number')}'"
        )

        _update_processing(processing_id, {"status": "NORMALIZED"})

        # 8. Validate
        logger.info("[OCR Pipeline] [4/5] Running deterministic validation checks...")
        validation_warnings = validate_receipt(normalized)
        error_count = sum(1 for w in validation_warnings if w.get("severity") == "ERROR")
        warn_count = sum(1 for w in validation_warnings if w.get("severity") == "WARNING")
        info_count = sum(1 for w in validation_warnings if w.get("severity") == "INFO")
        logger.info(
            f"[OCR Pipeline] [4/5] Validation checks: {error_count} error(s), {warn_count} warning(s), {info_count} info"
        )
        for w in validation_warnings:
            logger.info(f"    -> [{w.get('severity')}] {w.get('code')}: {w.get('message')}")

        # 9. Persist extracted data
        logger.info("[OCR Pipeline] [5/5] Persisting extracted data into database...")
        extracted_record = _persist_extracted_data(
            claim_id=claim_id,
            document_id=document_id,
            processing_id=processing_id,
            normalized_data=normalized,
            confidence_scores=result.confidence_scores,
            validation_warnings=validation_warnings,
        )

        # 10. Mark COMPLETED
        _update_processing(processing_id, {
            "status": "COMPLETED",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

        # 11. Update claim ocr_status
        supabase.table("claims").update({
            "ocr_status": "COMPLETED",
        }).eq("id", claim_id).execute()

        total_duration = time.time() - start_time
        logger.info(
            f"[OCR Pipeline] <<< SUCCESS for document_id={document_id} in {total_duration:.2f}s "
            f"(extracted_record_id={extracted_record.get('id')})"
        )

        return {
            "document_id": document_id,
            "status": "COMPLETED",
            "message": "Receipt extracted and validated successfully.",
            "extracted_data": extracted_record,
            "ocr_processing_id": processing_id,
        }

    except Exception as exc:
        total_duration = time.time() - start_time
        error_msg = str(exc)
        error_code = type(exc).__name__

        logger.error(
            f"[OCR Pipeline] <<< FAILED for document_id={document_id} after {total_duration:.2f}s: "
            f"[{error_code}] {error_msg}",
            exc_info=exc,
        )

        # Mark FAILED
        _update_processing(processing_id, {
            "status": "FAILED",
            "error_code": error_code,
            "error_message": error_msg[:2000],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })

        # Update claim ocr_status
        supabase.table("claims").update({
            "ocr_status": "FAILED",
        }).eq("id", claim_id).execute()

        return {
            "document_id": document_id,
            "status": "FAILED",
            "message": f"OCR processing failed: {error_msg}",
            "extracted_data": None,
        }


def _get_or_create_processing(document_id: str, force_reprocess: bool) -> str:
    """Get existing PENDING/FAILED processing record or create a new one."""
    if force_reprocess:
        # If forcing, always create a new record and increment retry count
        existing = supabase.table("ocr_processing") \
            .select("retry_count").eq("document_id", document_id) \
            .order("created_at", desc=True).limit(1).execute()

        retry_count = (existing.data[0]["retry_count"] + 1) if existing.data else 0

        result = supabase.table("ocr_processing").insert({
            "document_id": document_id,
            "status": "PENDING",
            "retry_count": retry_count,
        }).execute()
        return result.data[0]["id"]

    # Check for existing non-completed record
    existing = supabase.table("ocr_processing") \
        .select("*").eq("document_id", document_id) \
        .in_("status", ["PENDING", "FAILED"]) \
        .order("created_at", desc=True).limit(1).execute()

    if existing.data:
        return existing.data[0]["id"]

    # Create new record
    result = supabase.table("ocr_processing").insert({
        "document_id": document_id,
        "status": "PENDING",
    }).execute()
    return result.data[0]["id"]


def _update_processing(processing_id: str, updates: dict) -> None:
    """Update an ocr_processing record."""
    supabase.table("ocr_processing").update(updates).eq("id", processing_id).execute()


def _persist_extracted_data(
    claim_id: str,
    document_id: str,
    processing_id: str,
    normalized_data: dict,
    confidence_scores: dict,
    validation_warnings: list[dict],
) -> dict:
    """Insert a row into claim_extracted_data. Returns the inserted record."""
    # Remove any existing extracted data for this document (idempotency on reprocess)
    supabase.table("claim_extracted_data") \
        .delete().eq("document_id", document_id).execute()

    # Convert Decimals and dates for JSON storage
    safe_normalized = _to_json_safe(normalized_data)
    safe_line_items = safe_normalized.get("line_items", [])
    safe_confidence = _to_json_safe(confidence_scores)
    safe_warnings = _to_json_safe(validation_warnings)

    record = {
        "claim_id": claim_id,
        "document_id": document_id,
        "ocr_processing_id": processing_id,
        "merchant": normalized_data.get("merchant"),
        "merchant_normalized": normalized_data.get("merchant_normalized"),
        "invoice_number": normalized_data.get("invoice_number"),
        "transaction_date": str(normalized_data["transaction_date"]) if normalized_data.get("transaction_date") else None,
        "currency": normalized_data.get("currency"),
        "subtotal": float(normalized_data["subtotal"]) if normalized_data.get("subtotal") is not None else None,
        "tax": float(normalized_data["tax"]) if normalized_data.get("tax") is not None else None,
        "total": float(normalized_data["total"]) if normalized_data.get("total") is not None else None,
        "line_items": safe_line_items,
        "normalized_data": safe_normalized,
        "confidence_scores": safe_confidence,
        "validation_warnings": safe_warnings,
    }

    result = supabase.table("claim_extracted_data").insert(record).execute()
    return result.data[0]


def process_and_verify_receipt(
    claim_id: str,
    file_data: bytes,
    filename: str,
    content_type: str | None = None,
) -> dict:
    """
    Unified end-to-end receipt pipeline:
    1. Validates claim & file format/size.
    2. Uploads file to Supabase Storage once.
    3. Directly feeds in-memory bytes to Gemini OCR (no re-downloading!).
    4. Normalizes and deterministically validates extracted receipt data.
    5. Feeds in-memory extracted data directly into VerificationEngine (no extra DB queries!).
    6. Persists evidence, updates claim state, and returns unified summary.
    """
    # 1. Verify claim exists
    claim_res = supabase.table("claims").select("*").eq("id", claim_id).single().execute()
    if not claim_res.data:
        raise ValueError(f"Claim {claim_id} not found")
    claim = claim_res.data

    # 2. Validate file format and compute checksum
    mime_type = storage_service.validate_file(file_data, filename, content_type)
    checksum = storage_service.compute_checksum(file_data)

    # 3. Check for duplicate upload (same claim + same checksum)
    existing = (
        supabase.table("claim_documents")
        .select("id, file_name")
        .eq("claim_id", claim_id)
        .eq("checksum", checksum)
        .execute()
    )
    if existing.data:
        raise ValueError(
            f"A file with the same content already exists for this claim "
            f"(document_id: {existing.data[0]['id']}, file: {existing.data[0]['file_name']})."
        )

    # 4. Insert document record
    doc_record = supabase.table("claim_documents").insert({
        "claim_id": claim_id,
        "document_type": "RECEIPT",
        "file_name": filename,
        "file_size_bytes": len(file_data),
        "mime_type": mime_type,
        "checksum": checksum,
    }).execute()
    doc_id = doc_record.data[0]["id"]

    # 5. Upload to Supabase Storage
    storage_path = storage_service.upload_receipt(
        claim_id=claim_id,
        document_id=doc_id,
        file_data=file_data,
        filename=filename,
        mime_type=mime_type,
    )
    file_url = storage_service.get_public_url(storage_path)
    supabase.table("claim_documents").update({
        "storage_path": storage_path,
        "file_url": file_url,
    }).eq("id", doc_id).execute()

    doc_obj = {
        "id": doc_id,
        "claim_id": claim_id,
        "file_name": filename,
        "file_size_bytes": len(file_data),
        "mime_type": mime_type,
        "checksum": checksum,
        "storage_path": storage_path,
        "file_url": file_url,
    }

    # 6. Run OCR with in-memory bytes (skips re-downloading from storage!)
    ocr_result = process_document(
        document_id=doc_id,
        force_reprocess=True,
        file_data=file_data,
        mime_type=mime_type,
    )
    extracted = ocr_result.get("extracted_data")
    ocr_status = ocr_result.get("status")

    # 7. Run Verification Engine with in-memory claim, extracted, and doc (skips 3 DB read queries!)
    verification_res = None
    if ocr_status == "COMPLETED" and extracted:
        # Update claim dictionary and DB to reflect OCR extracted values
        claim["ocr_status"] = "COMPLETED"
        claim_sync = {"ocr_status": "COMPLETED"}
        if extracted.get("merchant_normalized") and (not claim.get("merchant") or claim.get("merchant") == "Unknown"):
            claim["merchant"] = extracted["merchant_normalized"]
            claim_sync["merchant"] = extracted["merchant_normalized"]
        if extracted.get("total") and (not claim.get("amount") or float(claim.get("amount") or 0) == 0.0):
            claim["amount"] = float(extracted["total"])
            claim_sync["amount"] = float(extracted["total"])
        if extracted.get("transaction_date") and not claim.get("claim_date"):
            claim["claim_date"] = str(extracted["transaction_date"])
            claim_sync["claim_date"] = str(extracted["transaction_date"])

        try:
            supabase.table("claims").update(claim_sync).eq("id", claim_id).execute()
        except Exception as e:
            logger.warning(f"[Pipeline] Could not sync extracted fields to claim: {e}")

        verification_res = run_verification(
            claim_id=claim_id,
            in_memory_claim=claim,
            in_memory_extracted=extracted,
            in_memory_doc=doc_obj,
        )

    logger.info(
        f"========== [Pipeline] Unified processing finished for claim_id={claim_id} | "
        f"OCR={ocr_status} | Verification={verification_res.decision.value if verification_res else 'SKIPPED'} =========="
    )

    return {
        "claim_id": claim_id,
        "document": doc_obj,
        "ocr_status": ocr_status,
        "extracted_data": extracted,
        "verification": verification_res.model_dump(mode="json") if verification_res else None,
        "message": (
            f"Receipt uploaded, extracted, and verified -> {verification_res.decision.value}"
            if verification_res
            else f"Receipt uploaded, OCR status: {ocr_status}"
        ),
    }

