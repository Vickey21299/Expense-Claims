"""
tests/test_unified_pipeline.py
Unit tests for the streamlined in-memory receipt upload, OCR, and verification pipeline.
Validates that redundant database queries and storage downloads are completely skipped.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from main import app
from app.models.enums import ClaimStatus, VerificationDecision
from app.services.ocr_pipeline import process_document, process_and_verify_receipt
from app.services.verification.engine import run_verification


def _sample_claim(claim_id: str | None = None) -> dict:
    cid = claim_id or str(uuid4())
    return {
        "id": cid,
        "claim_ref": "CLM-OPT-001",
        "employee_id": "usr-emp-1",
        "merchant": "Swiggy",
        "amount": Decimal("685.00"),
        "currency": "INR",
        "claim_date": "2026-09-08",
        "claim_type": "Meals",
        "status": "SUBMITTED",
        "ocr_status": "COMPLETED",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _sample_extracted(claim_id: str, doc_id: str) -> dict:
    return {
        "id": str(uuid4()),
        "claim_id": claim_id,
        "document_id": doc_id,
        "merchant": "Swiggy",
        "merchant_normalized": "Swiggy",
        "invoice_number": "SWIGGY-100",
        "transaction_date": "2026-09-08",
        "currency": "INR",
        "subtotal": 730.00,
        "tax": 35.00,
        "total": 685.00,
        "line_items": [],
        "normalized_data": {"discount": 80.0},
        "confidence_scores": {"overall": 0.95},
        "validation_warnings": [],
    }


def _sample_doc(claim_id: str, doc_id: str) -> dict:
    return {
        "id": doc_id,
        "claim_id": claim_id,
        "document_type": "RECEIPT",
        "file_name": "receipt.png",
        "file_size_bytes": 1024,
        "mime_type": "image/png",
        "checksum": "test-checksum-123",
        "storage_path": f"claims/{claim_id}/{doc_id}/receipt.png",
        "file_url": f"https://example.com/receipt.png",
    }


class TestUnifiedPipeline:
    """Tests for in-memory hand-off and skipping redundant DB / storage calls."""

    @patch("app.services.verification.engine.retrieve_candidates")
    @patch("app.services.verification.engine.supabase")
    def test_run_verification_in_memory_bypasses_db_reads(self, mock_sb, mock_retrieve):
        """Passing in-memory objects skips reading claims, claim_extracted_data, and claim_documents."""
        claim_id = str(uuid4())
        doc_id = str(uuid4())
        claim = _sample_claim(claim_id)
        extracted = _sample_extracted(claim_id, doc_id)
        doc = _sample_doc(claim_id, doc_id)

        mock_retrieve.return_value = []
        # Setup mocks for writing evidence
        mock_sb.table().delete().eq().execute.return_value = MagicMock(data=[])
        mock_sb.table().insert().execute.return_value = MagicMock(data=[{"id": str(uuid4())}])
        mock_sb.table().update().eq().execute.return_value = MagicMock(data=[claim])

        # Run verification with in-memory data
        run_out = run_verification(
            claim_id=claim_id,
            in_memory_claim=claim,
            in_memory_extracted=extracted,
            in_memory_doc=doc,
        )

        assert run_out.decision == VerificationDecision.CLEAN
        assert run_out.similarity_score == 0.0

        # Ensure table.select was NOT called for reading claim/extracted/doc
        mock_sb.table().select.assert_not_called()
        # Verify state transition update was dispatched
        mock_sb.table().update().eq().execute.assert_called()

    @patch("app.services.ocr_pipeline.get_extractor")
    @patch("app.services.ocr_pipeline.storage_service.download_receipt")
    @patch("app.services.ocr_pipeline.supabase")
    def test_process_document_with_file_data_skips_download(
        self, mock_sb, mock_download, mock_get_ext
    ):
        """When file_data is passed in-memory, storage_service.download_receipt must NOT be called."""
        doc_id = str(uuid4())
        claim_id = str(uuid4())
        doc = _sample_doc(claim_id, doc_id)

        # Mock DB calls in ocr_pipeline
        mock_sb.table().select().eq().single().execute.return_value = MagicMock(data=doc)
        mock_sb.table().select().eq().eq().execute.return_value = MagicMock(data=[])
        mock_sb.table().select().eq().in_().order().limit().execute.return_value = MagicMock(data=[])
        mock_sb.table().insert().execute.return_value = MagicMock(data=[{"id": str(uuid4())}])
        mock_sb.table().update().eq().execute.return_value = MagicMock(data=[])
        mock_sb.table().delete().eq().execute.return_value = MagicMock(data=[])

        # Mock Gemini extractor
        mock_extractor = MagicMock()
        mock_extractor.extract.return_value = MagicMock(
            extracted_data={
                "merchant": "Swiggy",
                "total": "685.00",
                "currency": "INR",
                "transaction_date": "2026-09-08",
                "invoice_number": "SWIGGY-100",
                "discount": "80.00",
                "line_items": [],
            },
            confidence_scores={"overall": 0.95},
            raw_response={"test": True},
        )
        mock_get_ext.return_value = mock_extractor

        # Process with in-memory bytes
        result = process_document(
            document_id=doc_id,
            force_reprocess=True,
            file_data=b"fake-image-bytes",
            mime_type="image/png",
        )

        assert result["status"] == "COMPLETED"
        # Download from storage must have been skipped!
        mock_download.assert_not_called()

    @patch("app.services.ocr_pipeline.run_verification")
    @patch("app.services.ocr_pipeline.process_document")
    @patch("app.services.ocr_pipeline.storage_service")
    @patch("app.services.ocr_pipeline.supabase")
    def test_process_and_verify_receipt_unified(
        self, mock_sb, mock_storage, mock_process_doc, mock_run_verif
    ):
        """Unified pipeline connects upload, OCR, and verification in-memory."""
        claim_id = str(uuid4())
        doc_id = str(uuid4())
        claim = _sample_claim(claim_id)
        doc = _sample_doc(claim_id, doc_id)
        extracted = _sample_extracted(claim_id, doc_id)

        # Mock DB claim lookup and duplicate check
        mock_sb.table().select().eq().single().execute.return_value = MagicMock(data=claim)
        mock_sb.table().select().eq().eq().execute.return_value = MagicMock(data=[])
        mock_sb.table().insert().execute.return_value = MagicMock(data=[{"id": doc_id}])
        mock_sb.table().update().eq().execute.return_value = MagicMock(data=[doc])

        # Mock storage
        mock_storage.validate_file.return_value = "image/png"
        mock_storage.compute_checksum.return_value = "checksum-xyz"
        mock_storage.upload_receipt.return_value = "claims/123/receipt.png"
        mock_storage.get_public_url.return_value = "https://example.com/receipt.png"

        # Mock OCR output
        mock_process_doc.return_value = {
            "status": "COMPLETED",
            "extracted_data": extracted,
        }

        # Mock Verification output
        mock_run_verif.return_value = MagicMock(
            decision=VerificationDecision.CLEAN,
            similarity_score=0.0,
            model_dump=lambda mode="json": {
                "decision": "CLEAN",
                "similarity_score": 0.0,
                "explanation": "No duplicate claims detected.",
            },
        )

        res = process_and_verify_receipt(
            claim_id=claim_id,
            file_data=b"fake-bytes",
            filename="receipt.png",
            content_type="image/png",
        )

        assert res["claim_id"] == claim_id
        assert res["ocr_status"] == "COMPLETED"
        assert res["verification"]["decision"] == "CLEAN"
        assert res["document"]["id"] == doc_id

        # Verify run_verification was called with in-memory claim and extracted data
        mock_run_verif.assert_called_once()
        _, kwargs = mock_run_verif.call_args
        assert kwargs["in_memory_claim"] == claim
        assert kwargs["in_memory_extracted"] == extracted
        assert kwargs["in_memory_doc"]["id"] == doc_id

    @patch("app.routers.documents.process_and_verify_receipt")
    @patch("app.routers.documents.supabase")
    def test_upload_and_verify_api_endpoint(self, mock_sb, mock_pipeline):
        """POST /api/v1/claims/{claim_id}/documents/upload-and-verify triggers streamlined pipeline."""
        client = TestClient(app)
        claim_id = str(uuid4())
        doc_id = str(uuid4())
        claim = _sample_claim(claim_id)

        mock_sb.table().select().eq().single().execute.return_value = MagicMock(data=claim)
        mock_pipeline.return_value = {
            "claim_id": claim_id,
            "document": {
                "id": doc_id,
                "claim_id": claim_id,
                "file_name": "bill.png",
                "storage_path": f"claims/{claim_id}/{doc_id}/bill.png",
                "mime_type": "image/png",
                "file_size_bytes": 500,
                "checksum": "chk-123",
            },
            "ocr_status": "COMPLETED",
            "extracted_data": {
                "id": str(uuid4()),
                "claim_id": claim_id,
                "document_id": doc_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            "verification": {
                "decision": "CLEAN",
                "similarity_score": 0.0,
                "explanation": "Verified clean",
            },
            "message": "Receipt uploaded, extracted, and verified -> CLEAN",
        }

        response = client.post(
            f"/api/v1/claims/{claim_id}/documents/upload-and-verify",
            files={"file": ("bill.png", b"fake-png-content", "image/png")},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["claim_id"] == claim_id
        assert data["document"]["id"] == doc_id
        assert data["ocr_status"] == "COMPLETED"
        assert data["verification"]["decision"] == "CLEAN"

    @patch("app.routers.documents.process_and_verify_receipt")
    @patch("app.routers.documents.supabase")
    def test_upload_document_with_auto_verify_flag(self, mock_sb, mock_pipeline):
        """POST /api/v1/claims/{claim_id}/documents?auto_verify=true routes to pipeline."""
        client = TestClient(app)
        claim_id = str(uuid4())
        doc_id = str(uuid4())
        claim = _sample_claim(claim_id)

        mock_sb.table().select().eq().single().execute.return_value = MagicMock(data=claim)
        mock_pipeline.return_value = {
            "claim_id": claim_id,
            "document": {
                "id": doc_id,
                "claim_id": claim_id,
                "file_name": "bill.png",
                "storage_path": f"claims/{claim_id}/{doc_id}/bill.png",
                "mime_type": "image/png",
                "file_size_bytes": 500,
                "checksum": "chk-123",
            },
            "ocr_status": "COMPLETED",
            "extracted_data": None,
            "verification": None,
            "message": "Processed",
        }

        response = client.post(
            f"/api/v1/claims/{claim_id}/documents?auto_verify=true",
            files={"file": ("bill.png", b"fake-png-content", "image/png")},
        )

        assert response.status_code == 201
        mock_pipeline.assert_called_once()

