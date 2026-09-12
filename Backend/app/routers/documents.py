"""
app/routers/documents.py
Receipt upload and OCR processing endpoints.

POST /api/v1/claims/{claim_id}/documents                        Upload receipt
GET  /api/v1/claims/{claim_id}/documents/{document_id}          Get document detail + OCR
POST /api/v1/claims/{claim_id}/documents/{document_id}/process  Trigger OCR pipeline
GET  /api/v1/claims/{claim_id}/documents/{document_id}/extracted Get extracted data only
"""
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.core.database import supabase
from app.core.logging import get_logger
from app.models.documents import (
    DocumentDetailOut,
    DocumentUploadResponse,
    ExtractedDataOut,
    ProcessingResponse,
    UnifiedPipelineResponse,
)
from app.core.config import settings
from app.models.enums import OcrProcessingStatus
from app.services import storage as storage_service
from app.services.storage import FileValidationError, StorageError
from app.services.ocr_pipeline import (
    process_document,
    process_and_verify_receipt,
    OcrPipelineError,
)
from app.services.extraction import GeminiReceiptExtractor
from app.services.normalization import normalize_receipt_data
from app.services.validation import validate_receipt

router = APIRouter(tags=["Documents & OCR"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_claim_or_404(claim_id: str) -> dict:
    """Fetch a claim or raise 404."""
    result = supabase.table("claims").select("*").eq("id", claim_id).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return result.data


def _get_document_or_404(document_id: str, claim_id: str) -> dict:
    """Fetch a document belonging to a specific claim, or raise 404."""
    result = supabase.table("claim_documents").select("*") \
        .eq("id", document_id).eq("claim_id", claim_id).single().execute()
    if not result.data:
        raise HTTPException(
            status_code=404,
            detail=f"Document {document_id} not found for claim {claim_id}",
        )
    return result.data


def _infer_category(merchant: str, description: str = "", text: str = "") -> str:
    combined = f"{merchant} {description} {text}".lower()
    if any(k in combined for k in ["uber", "ola", "flight", "train", "makemytrip", "irctc", "indigo", "air", "cab", "taxi", "fare"]):
        return "Travel"
    if any(k in combined for k in ["swiggy", "zomato", "restaurant", "cafe", "coffee", "lunch", "dinner", "food", "dining", "meal", "starbucks", "mcdonald"]):
        return "Meals"
    if any(k in combined for k in ["hotel", "marriott", "oyo", "stay", "room", "lodging", "airbnb", "resort"]):
        return "Accommodation"
    if any(k in combined for k in ["amazon", "flipkart", "supplies", "stationery", "paper", "keyboard", "mouse", "monitor", "hardware"]):
        return "Office Supplies"
    if any(k in combined for k in ["zoom", "slack", "aws", "cloud", "google", "microsoft", "github", "subscription", "software", "license", "saas", "adobe"]):
        return "Software & Subscriptions"
    if any(k in combined for k in ["training", "conference", "course", "udemy", "coursera", "workshop", "event", "summit"]):
        return "Training & Conferences"
    if any(k in combined for k in ["ad", "ads", "marketing", "google ads", "meta ads", "campaign"]):
        return "Marketing"
    return "Other"


# ---------------------------------------------------------------------------
# Direct Analyze (Standalone before/during claim creation)
# ---------------------------------------------------------------------------
@router.post(
    "/documents/analyze",
    summary="Analyze receipt using Gemini OCR and return structured expense fields",
    description="Accepts a receipt file, runs Gemini Vision extraction, normalizes fields, and infers category.",
)
async def analyze_receipt_document(
    file: UploadFile = File(..., description="Receipt file (PDF, PNG, JPG, WEBP)"),
):
    try:
        filename = file.filename or "receipt"
        logger.info(f"[API:Analyze] Received receipt for instant analysis: filename='{filename}'")
        file_data = await file.read()
        content_type = file.content_type

        # Validate file
        try:
            mime_type = storage_service.validate_file(file_data, filename, content_type)
        except FileValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Extract using Gemini
        extracted_raw = {}
        confidence_scores = {}
        try:
            extractor = GeminiReceiptExtractor(api_key=settings.GEMINI_API_KEY)
            result = extractor.extract(file_data, mime_type)
            extracted_raw = result.extracted_data or {}
            confidence_scores = result.confidence_scores or {}
        except Exception as e:
            logger.warning(f"[API:Analyze] Gemini extraction warning: {e}")

        # Normalize data
        normalized = normalize_receipt_data(extracted_raw)
        warnings = validate_receipt(normalized)

        merchant = normalized.get("merchant") or normalized.get("merchant_normalized") or ""
        total_amt = normalized.get("total")
        if total_amt is None:
            total_amt = normalized.get("subtotal")
        amount = float(total_amt) if total_amt is not None else None

        date_str = str(normalized.get("transaction_date")) if normalized.get("transaction_date") else ""
        currency = normalized.get("currency") or "INR"
        category = _infer_category(merchant, "", filename)

        desc = f"Expense at {merchant}" if merchant else f"Receipt {filename}"
        if normalized.get("invoice_number"):
            desc += f" (Invoice #{normalized.get('invoice_number')})"

        return {
            "merchant": merchant,
            "amount": amount,
            "date": date_str,
            "currency": currency,
            "category": category,
            "description": desc,
            "invoice_number": normalized.get("invoice_number"),
            "confidence_scores": confidence_scores,
            "line_items": normalized.get("line_items", []),
            "warnings": warnings,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[API:Analyze] Failed to analyze receipt: {exc}", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Upload (Standard & Unified)
# ---------------------------------------------------------------------------
@router.post(
    "/claims/{claim_id}/documents/upload-and-verify",
    response_model=UnifiedPipelineResponse,
    status_code=201,
    summary="Upload receipt, extract data via OCR, and run deterministic verification in one step",
    description=(
        "Streamlined in-memory pipeline: uploads receipt to storage, extracts data via Gemini "
        "without re-downloading, deterministically validates, and runs verification against historical claims."
    ),
)
async def upload_and_verify_document(
    claim_id: UUID,
    file: UploadFile = File(..., description="Receipt file (PDF, PNG, JPG, WEBP)"),

):
    try:
        filename = file.filename or "receipt"
        logger.info(f"[API:UploadAndVerify] Received receipt for claim_id={claim_id}, filename='{filename}'")

        _get_claim_or_404(str(claim_id))
        file_data = await file.read()
        content_type = file.content_type

        result = process_and_verify_receipt(
            claim_id=str(claim_id),
            file_data=file_data,
            filename=filename,
            content_type=content_type,
        )

        return UnifiedPipelineResponse(**result)

    except FileValidationError as e:
        logger.warning(f"[API:UploadAndVerify] File validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        err_msg = str(e)
        if "already exists" in err_msg.lower():
            raise HTTPException(status_code=409, detail=err_msg)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=404, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)
    except StorageError as e:
        logger.error(f"[API:UploadAndVerify] Storage error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[API:UploadAndVerify] Pipeline error: {exc}", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/claims/{claim_id}/documents",
    response_model=DocumentUploadResponse | UnifiedPipelineResponse,
    status_code=201,
    summary="Upload a receipt/invoice document",
    description=(
        "Upload a receipt file (PDF, PNG, JPG, WEBP) to Supabase Storage "
        "and create a claim_documents record. Pass ?auto_verify=true to automatically "
        "run OCR and verification in a single streamlined pass."
    ),
)
async def upload_document(
    claim_id: UUID,
    file: UploadFile = File(..., description="Receipt file (PDF, PNG, JPG, WEBP)"),
    auto_verify: bool = Query(False, description="Automatically run OCR and verification in-memory"),
):
    try:
        filename = file.filename or "receipt"
        logger.info(f"[API:Upload] Received receipt upload: claim_id={claim_id}, filename='{filename}', auto_verify={auto_verify}")

        # 1. Verify claim exists
        _get_claim_or_404(str(claim_id))

        # 2. Read file contents
        file_data = await file.read()
        content_type = file.content_type

        # If auto_verify requested, use streamlined pipeline
        if auto_verify:
            result = process_and_verify_receipt(
                claim_id=str(claim_id),
                file_data=file_data,
                filename=filename,
                content_type=content_type,
            )
            return UnifiedPipelineResponse(**result)

        # 3. Validate file
        try:
            mime_type = storage_service.validate_file(file_data, filename, content_type)
        except FileValidationError as e:
            logger.warning(f"[API:Upload] File validation failed for '{filename}': {e}")
            raise HTTPException(status_code=400, detail=str(e))

        # 4. Compute checksum
        checksum = storage_service.compute_checksum(file_data)

        # 5. Check for duplicate upload (same claim + same checksum)
        existing = supabase.table("claim_documents") \
            .select("id, file_name") \
            .eq("claim_id", str(claim_id)) \
            .eq("checksum", checksum).execute()

        if existing.data:
            logger.warning(
                f"[API:Upload] Duplicate receipt detected for claim {claim_id}: "
                f"matches doc_id={existing.data[0]['id']} ('{existing.data[0]['file_name']}')"
            )
            raise HTTPException(
                status_code=409,
                detail=f"A file with the same content already exists for this claim "
                       f"(document_id: {existing.data[0]['id']}, "
                       f"file: {existing.data[0]['file_name']}).",
            )

        # 6. Create the document record first (to get the UUID)
        doc_record = supabase.table("claim_documents").insert({
            "claim_id": str(claim_id),
            "document_type": "RECEIPT",
            "file_name": filename,
            "file_size_bytes": len(file_data),
            "mime_type": mime_type,
            "checksum": checksum,
        }).execute()

        doc_id = doc_record.data[0]["id"]

        # 7. Upload to Supabase Storage
        try:
            storage_path = storage_service.upload_receipt(
                claim_id=str(claim_id),
                document_id=doc_id,
                file_data=file_data,
                filename=filename,
                mime_type=mime_type,
            )
        except StorageError as e:
            # Rollback the DB record
            supabase.table("claim_documents").delete().eq("id", doc_id).execute()
            logger.error(f"[API:Upload] Supabase Storage upload failed: {e}")
            raise HTTPException(status_code=502, detail=f"Storage upload failed: {e}")

        # 8. Update the document record with storage path
        supabase.table("claim_documents").update({
            "storage_path": storage_path,
            "file_url": storage_service.get_public_url(storage_path),
        }).eq("id", doc_id).execute()

        logger.info(
            f"[API:Upload] Receipt uploaded successfully: doc_id={doc_id}, "
            f"path='{storage_path}', size={len(file_data):,} bytes, mime={mime_type}"
        )

        return DocumentUploadResponse(
            id=doc_id,
            claim_id=claim_id,
            file_name=filename,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size_bytes=len(file_data),
            checksum=checksum,
        )

    except HTTPException:
        raise
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        err_msg = str(e)
        if "already exists" in err_msg.lower():
            raise HTTPException(status_code=409, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)
    except Exception as exc:
        logger.error(f"[API:Upload] Document upload failed: {exc}", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))



# ---------------------------------------------------------------------------
# Process (trigger OCR)
# ---------------------------------------------------------------------------
@router.post(
    "/claims/{claim_id}/documents/{document_id}/process",
    response_model=ProcessingResponse,
    summary="Trigger OCR processing for a document",
    description=(
        "Runs the Gemini extraction pipeline. Idempotent — returns existing result "
        "if already COMPLETED. Pass ?force=true to reprocess."
    ),
)
def trigger_processing(
    claim_id: UUID,
    document_id: UUID,
    force: bool = Query(False, description="Force reprocessing even if already completed"),
):
    try:
        logger.info(
            f"[API:OCR] Trigger OCR requested: claim_id={claim_id}, "
            f"document_id={document_id}, force={force}"
        )
        _get_claim_or_404(str(claim_id))
        _get_document_or_404(str(document_id), str(claim_id))

        result = process_document(str(document_id), force_reprocess=force)

        status = OcrProcessingStatus(result["status"])
        extracted = result.get("extracted_data")

        logger.info(
            f"[API:OCR] Completed request for document_id={document_id}: "
            f"status={status}, message='{result.get('message')}'"
        )

        return ProcessingResponse(
            document_id=document_id,
            status=status,
            message=result["message"],
            extracted_data=extracted,
        )

    except OcrPipelineError as e:
        logger.warning(f"[API:OCR] Pipeline error for doc_id={document_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            f"[API:OCR] Internal server error for doc_id={document_id}: {exc}",
            exc_info=exc,
        )
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Get document detail
# ---------------------------------------------------------------------------
@router.get(
    "/claims/{claim_id}/documents/{document_id}",
    response_model=DocumentDetailOut,
    summary="Get document with OCR status and extracted data",
)
def get_document_detail(claim_id: UUID, document_id: UUID):
    try:
        doc = _get_document_or_404(str(document_id), str(claim_id))

        # Fetch latest OCR processing record
        ocr = supabase.table("ocr_processing") \
            .select("*").eq("document_id", str(document_id)) \
            .order("created_at", desc=True).limit(1).execute()

        # Fetch extracted data
        extracted = supabase.table("claim_extracted_data") \
            .select("*").eq("document_id", str(document_id)) \
            .order("created_at", desc=True).limit(1).execute()

        doc["ocr_processing"] = ocr.data[0] if ocr.data else None
        doc["extracted_data"] = extracted.data[0] if extracted.data else None

        return doc

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to get document detail",
            extra={"document_id": str(document_id)},
            exc_info=exc,
        )
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Get extracted data only
# ---------------------------------------------------------------------------
@router.get(
    "/claims/{claim_id}/documents/{document_id}/extracted",
    response_model=ExtractedDataOut | None,
    summary="Get just the extracted receipt data",
)
def get_extracted_data(claim_id: UUID, document_id: UUID):
    try:
        _get_document_or_404(str(document_id), str(claim_id))

        result = supabase.table("claim_extracted_data") \
            .select("*").eq("document_id", str(document_id)) \
            .order("created_at", desc=True).limit(1).execute()

        if not result.data:
            raise HTTPException(
                status_code=404,
                detail="No extracted data found. Run /process first.",
            )

        return result.data[0]

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to get extracted data",
            extra={"document_id": str(document_id)},
            exc_info=exc,
        )
        raise HTTPException(status_code=500, detail=str(exc))
