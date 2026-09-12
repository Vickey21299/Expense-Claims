"""
tests/test_verification_engine.py
Unit tests for the deterministic Verification Engine.
No external API calls or Gemini dependencies.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4
import pytest

from app.models.enums import ClaimStatus, VerificationDecision
from app.services.verification.similarity import (
    calculate_merchant_similarity,
    calculate_amount_similarity,
    calculate_date_similarity,
    calculate_invoice_similarity,
    calculate_category_similarity,
    calculate_weighted_overall_score,
)
from app.services.verification.rules import (
    evaluate_candidate,
    determine_verification_decision,
)
from app.services.verification.engine import run_verification


# ---------------------------------------------------------------------------
# Helpers for test fixtures
# ---------------------------------------------------------------------------
def _make_claim(
    claim_id: str | None = None,
    claim_ref: str = "CLM-001",
    merchant: str = "Uber",
    amount: float = 1250.00,
    claim_date: str = "2026-09-08",
    claim_type: str = "Travel",
    status: str = "SUBMITTED",
    ocr_status: str = "COMPLETED",
    submitted_at: datetime | None = None,
    employee_id: str = "usr-emp-1",
) -> dict:
    return {
        "id": claim_id or str(uuid4()),
        "claim_ref": claim_ref,
        "merchant": merchant,
        "amount": Decimal(str(amount)),
        "claim_date": claim_date,
        "claim_type": claim_type,
        "status": status,
        "ocr_status": ocr_status,
        "submitted_at": (submitted_at or datetime.now(timezone.utc)).isoformat(),
        "created_at": (submitted_at or datetime.now(timezone.utc)).isoformat(),
        "employee_id": employee_id,
    }


def _make_extracted(
    claim_id: str,
    merchant_normalized: str = "Uber",
    total: float = 1250.00,
    transaction_date: str = "2026-09-08",
    invoice_number: str | None = "INV-92831",
) -> dict:
    return {
        "claim_id": claim_id,
        "merchant_normalized": merchant_normalized,
        "total": Decimal(str(total)),
        "transaction_date": transaction_date,
        "invoice_number": invoice_number,
    }


def _make_doc(claim_id: str, checksum: str = "hash-abc-123") -> dict:
    return {
        "claim_id": claim_id,
        "checksum": checksum,
        "file_name": "receipt.png",
    }


# ===========================================================================
# Test Cases (1 through 12)
# ===========================================================================

class TestVerificationEngine:

    # 1. No historical match -> CLEAN
    def test_no_historical_candidates_is_clean(self):
        target_claim = _make_claim()
        decision, score, strongest, wait_until, rules, explanation = determine_verification_decision(
            target_claim, []
        )
        assert decision == VerificationDecision.CLEAN
        assert score == 0.0
        assert strongest is None
        assert wait_until is None
        assert "passed verification checks" in explanation

    # 2. Weak merchant match -> CLEAN
    def test_weak_merchant_match_is_clean(self):
        target_claim = _make_claim(merchant="Starbucks", amount=350.00, claim_date="2026-09-08")
        target_extracted = _make_extracted(target_claim["id"], merchant_normalized="Starbucks", total=350.00, transaction_date="2026-09-08")
        target_doc = _make_doc(target_claim["id"], checksum="hash-1")

        candidate_claim = _make_claim(claim_ref="CLM-OLD", merchant="Reliance Jio", amount=899.00, claim_date="2026-07-01", status="PAID")
        candidate = {
            "claim": candidate_claim,
            "extracted": _make_extracted(candidate_claim["id"], merchant_normalized="Jio", total=899.00, transaction_date="2026-07-01", invoice_number="JIO-999"),
            "document": _make_doc(candidate_claim["id"], checksum="hash-2"),
        }

        match = evaluate_candidate(target_claim, target_extracted, target_doc, candidate)
        decision, score, strongest, wait_until, rules, explanation = determine_verification_decision(
            target_claim, [match]
        )
        assert decision == VerificationDecision.CLEAN
        assert score < 0.70

    # 3. Strong merchant + amount + date match -> POTENTIAL_DUPLICATE
    def test_strong_merchant_amount_date_match(self):
        target_claim = _make_claim(merchant="Uber", amount=1250.00, claim_date="2026-09-08")
        target_extracted = _make_extracted(target_claim["id"], merchant_normalized="Uber", total=1250.00, transaction_date="2026-09-08", invoice_number=None)
        target_doc = _make_doc(target_claim["id"], checksum="hash-new")

        candidate_claim = _make_claim(claim_ref="CLM-100", merchant="UBER INDIA", amount=1250.00, claim_date="2026-09-08", status="PAID")
        candidate = {
            "claim": candidate_claim,
            "extracted": _make_extracted(candidate_claim["id"], merchant_normalized="Uber", total=1250.00, transaction_date="2026-09-08", invoice_number=None),
            "document": _make_doc(candidate_claim["id"], checksum="hash-old"),
        }

        match = evaluate_candidate(target_claim, target_extracted, target_doc, candidate)
        assert match.similarity_score >= 0.90
        decision, score, strongest, wait_until, rules, explanation = determine_verification_decision(
            target_claim, [match]
        )
        assert decision == VerificationDecision.POTENTIAL_DUPLICATE
        assert "DUPLICATE_PAID_CLAIM" in rules

    # 4. Exact invoice match -> strong duplicate override
    def test_exact_invoice_match_is_strong_duplicate(self):
        target_claim = _make_claim(merchant="Swiggy", amount=650.00)
        target_extracted = _make_extracted(target_claim["id"], invoice_number="SWIGGY-88412")
        target_doc = _make_doc(target_claim["id"], checksum="hash-1")

        candidate_claim = _make_claim(claim_ref="CLM-200", merchant="Swiggy", amount=650.00, status="PAID")
        candidate = {
            "claim": candidate_claim,
            "extracted": _make_extracted(candidate_claim["id"], invoice_number="SWIGGY-88412"),
            "document": _make_doc(candidate_claim["id"], checksum="hash-2"),
        }

        match = evaluate_candidate(target_claim, target_extracted, target_doc, candidate)
        assert match.field_scores.invoice_similarity == 1.0
        decision, score, strongest, wait_until, rules, explanation = determine_verification_decision(
            target_claim, [match]
        )
        assert decision == VerificationDecision.POTENTIAL_DUPLICATE
        assert "EXACT_INVOICE_NUMBER" in rules

    # 5. Exact receipt hash -> strong duplicate override
    def test_exact_receipt_hash_match(self):
        target_claim = _make_claim(merchant="AWS", amount=4500.00)
        target_extracted = _make_extracted(target_claim["id"])
        identical_checksum = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        target_doc = _make_doc(target_claim["id"], checksum=identical_checksum)

        candidate_claim = _make_claim(claim_ref="CLM-300", merchant="Amazon Web Services", amount=4500.00, status="PAID")
        candidate = {
            "claim": candidate_claim,
            "extracted": _make_extracted(candidate_claim["id"]),
            "document": _make_doc(candidate_claim["id"], checksum=identical_checksum),
        }

        match = evaluate_candidate(target_claim, target_extracted, target_doc, candidate)
        assert match.field_scores.receipt_hash_match is True
        assert match.similarity_score == 1.0
        decision, score, strongest, wait_until, rules, explanation = determine_verification_decision(
            target_claim, [match]
        )
        assert decision == VerificationDecision.POTENTIAL_DUPLICATE
        assert "EXACT_RECEIPT_HASH" in rules

    # 6. Existing matching claim is PAID -> flag duplicate
    def test_existing_matching_claim_paid_flagged(self):
        target_claim = _make_claim(merchant="Uber", amount=1200.00)
        candidate_claim = _make_claim(claim_ref="CLM-PAID", merchant="Uber", amount=1200.00, status="PAID")
        candidate = {
            "claim": candidate_claim,
            "extracted": _make_extracted(candidate_claim["id"]),
            "document": _make_doc(candidate_claim["id"]),
        }

        match = evaluate_candidate(target_claim, _make_extracted(target_claim["id"]), _make_doc(target_claim["id"]), candidate)
        decision, score, strongest, wait_until, rules, explanation = determine_verification_decision(
            target_claim, [match]
        )
        assert decision == VerificationDecision.POTENTIAL_DUPLICATE
        assert "PAID" in explanation

    # 7. Existing matching claim is processing for 1 day -> WAITING
    def test_existing_matching_claim_processing_within_wait_period(self):
        target_claim = _make_claim(merchant="Uber", amount=1200.00)
        one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
        candidate_claim = _make_claim(
            claim_ref="CLM-ACTIVE",
            merchant="Uber",
            amount=1200.00,
            status="UNDER_REVIEW",
            submitted_at=one_day_ago,
        )
        candidate = {
            "claim": candidate_claim,
            "extracted": _make_extracted(candidate_claim["id"]),
            "document": _make_doc(candidate_claim["id"]),
        }

        match = evaluate_candidate(target_claim, _make_extracted(target_claim["id"]), _make_doc(target_claim["id"]), candidate)
        assert match.age_days == 1

        decision, score, strongest, wait_until, rules, explanation = determine_verification_decision(
            target_claim, [match]
        )
        assert decision == VerificationDecision.WAITING_FOR_EXISTING_CLAIM
        assert wait_until is not None
        assert "ACTIVE_CLAIM_WAITING" in rules
        assert "Employee must wait" in explanation

    # 8. Existing matching claim is processing for 3+ days -> ESCALATE_TO_MANAGER
    def test_existing_matching_claim_processing_exceeded_wait_period(self):
        target_claim = _make_claim(merchant="Uber", amount=1200.00)
        four_days_ago = datetime.now(timezone.utc) - timedelta(days=4)
        candidate_claim = _make_claim(
            claim_ref="CLM-STUCK",
            merchant="Uber",
            amount=1200.00,
            status="UNDER_REVIEW",
            submitted_at=four_days_ago,
        )
        candidate = {
            "claim": candidate_claim,
            "extracted": _make_extracted(candidate_claim["id"]),
            "document": _make_doc(candidate_claim["id"]),
        }

        match = evaluate_candidate(target_claim, _make_extracted(target_claim["id"]), _make_doc(target_claim["id"]), candidate)
        assert match.age_days >= 3

        decision, score, strongest, wait_until, rules, explanation = determine_verification_decision(
            target_claim, [match]
        )
        assert decision == VerificationDecision.ESCALATE_TO_MANAGER
        assert "ACTIVE_CLAIM_EXCEEDED_WAIT_PERIOD" in rules
        assert "Escalated to manager" in explanation

    # 9. Existing matching claim is REJECTED -> normal verification
    def test_existing_matching_claim_rejected_allows_verification(self):
        target_claim = _make_claim(merchant="Uber", amount=1200.00)
        candidate_claim = _make_claim(
            claim_ref="CLM-REJ",
            merchant="Uber",
            amount=1200.00,
            status="REJECTED",
        )
        candidate = {
            "claim": candidate_claim,
            "extracted": _make_extracted(candidate_claim["id"]),
            "document": _make_doc(candidate_claim["id"]),
        }

        match = evaluate_candidate(target_claim, _make_extracted(target_claim["id"]), _make_doc(target_claim["id"]), candidate)
        decision, score, strongest, wait_until, rules, explanation = determine_verification_decision(
            target_claim, [match]
        )
        # Rejected claim does not block verification!
        assert decision == VerificationDecision.CLEAN
        assert "REJECTED" in explanation

    # 10. Multiple candidates -> strongest selected correctly
    def test_multiple_candidates_strongest_selected(self):
        target_claim = _make_claim(merchant="Swiggy", amount=500.00, claim_date="2026-09-08")
        target_extracted = _make_extracted(target_claim["id"], merchant_normalized="Swiggy", total=500.00, transaction_date="2026-09-08", invoice_number="SWIGGY-1")
        target_doc = _make_doc(target_claim["id"], checksum="hash-target")

        # Candidate A: Moderate match (amount differs by 10%, different invoice & checksum)
        cand_a_claim = _make_claim(claim_ref="CLM-A", merchant="Swiggy", amount=550.00, claim_date="2026-09-05", status="PAID")
        cand_a = {
            "claim": cand_a_claim,
            "extracted": _make_extracted(cand_a_claim["id"], merchant_normalized="Swiggy", total=550.00, transaction_date="2026-09-05", invoice_number="SWIGGY-A"),
            "document": _make_doc(cand_a_claim["id"], checksum="hash-a"),
        }

        # Candidate B: Perfect match
        cand_b_claim = _make_claim(claim_ref="CLM-B", merchant="Swiggy", amount=500.00, claim_date="2026-09-08", status="PAID")
        cand_b = {
            "claim": cand_b_claim,
            "extracted": _make_extracted(cand_b_claim["id"], merchant_normalized="Swiggy", total=500.00, transaction_date="2026-09-08", invoice_number="SWIGGY-1"),
            "document": _make_doc(cand_b_claim["id"], checksum="hash-target"),
        }

        match_a = evaluate_candidate(target_claim, target_extracted, target_doc, cand_a)
        match_b = evaluate_candidate(target_claim, target_extracted, target_doc, cand_b)

        assert match_b.similarity_score > match_a.similarity_score

        decision, score, strongest, wait_until, rules, explanation = determine_verification_decision(
            target_claim, [match_a, match_b]
        )
        assert strongest.claim_ref == "CLM-B"
        assert strongest.similarity_score >= 0.95

    # 11. Verification can safely be retried without duplicate records (Idempotency)
    @patch("app.services.verification.engine.retrieve_candidates")
    @patch("app.services.verification.engine.supabase")
    def test_verification_is_idempotent(self, mock_sb, mock_retrieve):
        claim_id = str(uuid4())
        mock_claim = _make_claim(claim_id=claim_id, status="SUBMITTED", ocr_status="COMPLETED")
        mock_extracted = _make_extracted(claim_id=claim_id)
        mock_doc = _make_doc(claim_id=claim_id)

        mock_retrieve.return_value = []

        # Mock database queries
        mock_sb.table().select().eq().single().execute.return_value = MagicMock(data=mock_claim)
        mock_sb.table().select().eq().order().limit().execute.return_value = MagicMock(data=[mock_extracted])

        # Cleanup deletes
        mock_sb.table().delete().eq().execute.return_value = MagicMock(data=[])
        # Inserts & updates
        mock_sb.table().insert().execute.return_value = MagicMock(data=[{"id": str(uuid4())}])
        mock_sb.table().update().eq().execute.return_value = MagicMock(data=[mock_claim])

        # Run twice
        run1 = run_verification(claim_id)
        run2 = run_verification(claim_id)

        assert run1.decision == VerificationDecision.CLEAN
        assert run2.decision == VerificationDecision.CLEAN
        # Verify cleanup was called before insertions
        assert mock_sb.table().delete().eq().execute.call_count >= 2

    # 12. Missing / incomplete OCR data is handled safely
    @patch("app.services.verification.engine.supabase")
    def test_missing_ocr_data_raises_error(self, mock_sb):
        claim_id = str(uuid4())
        mock_claim = _make_claim(claim_id=claim_id, status="SUBMITTED", ocr_status="PENDING")

        # Mock claim found, but extracted data empty
        mock_sb.table().select().eq().single().execute.return_value = MagicMock(data=mock_claim)
        mock_sb.table().select().eq().order().limit().execute.return_value = MagicMock(data=[])

        with pytest.raises(ValueError) as excinfo:
            run_verification(claim_id)

        assert "OCR processing must be completed" in str(excinfo.value)
