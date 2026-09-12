"""
tests/test_llm_analysis.py
Unit tests for Session 6B: Gemini Verification & Manager Recommendation Layer.
"""
import json
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.models.enums import VerificationDecision, ClaimStatus
from app.models.verification import (
    CandidateMatch,
    FieldSimilarityScores,
    LlmVerificationAnalysis,
)
from app.services.verification.config import verification_config
from app.services.verification.llm_analysis import (
    is_llm_analysis_required,
    build_pruned_context,
    analyze_claim_with_llm,
    _build_fallback_analysis,
)


def _make_candidate_match(
    claim_ref: str = "CLM-8103",
    score: float = 0.94,
    status: str = "APPROVED",
    signals: list[str] | None = None,
) -> CandidateMatch:
    return CandidateMatch(
        matched_claim_id=uuid4(),
        claim_ref=claim_ref,
        similarity_score=score,
        status=ClaimStatus.APPROVED,
        age_days=15,
        field_scores=FieldSimilarityScores(
            merchant_similarity=1.0,
            amount_similarity=0.98,
            date_similarity=0.90,
            invoice_similarity=1.0,
            category_similarity=1.0,
            receipt_hash_match=False,
            same_employee=True,
        ),
        signals=signals or ["Exact invoice match", "Same employee"],
        target_values={"merchant": "Uber India", "amount": 1200.0, "invoice": "INV-4412"},
        matched_values={"merchant": "Uber India", "amount": 1200.0, "invoice": "INV-4412"},
    )


class TestLlmAnalysisGating:
    """Test whether Gemini forensic analysis is selectively triggered."""

    def test_analysis_required_for_potential_duplicate(self):
        cand = _make_candidate_match(score=0.94)
        assert is_llm_analysis_required(
            decision=VerificationDecision.POTENTIAL_DUPLICATE,
            candidates=[cand],
            overall_score=0.94,
        ) is True

    def test_analysis_required_for_borderline(self):
        cand = _make_candidate_match(score=0.72)
        assert is_llm_analysis_required(
            decision=VerificationDecision.BORDERLINE,
            candidates=[cand],
            overall_score=0.72,
        ) is True

    def test_analysis_skipped_for_clean_with_low_score(self):
        cand = _make_candidate_match(score=0.25)
        assert is_llm_analysis_required(
            decision=VerificationDecision.CLEAN,
            candidates=[cand],
            overall_score=0.25,
        ) is False

    def test_analysis_skipped_for_clean_with_no_candidates(self):
        assert is_llm_analysis_required(
            decision=VerificationDecision.CLEAN,
            candidates=[],
            overall_score=0.0,
        ) is False

    def test_analysis_disabled_via_config(self):
        cand = _make_candidate_match(score=0.94)
        with patch.object(verification_config, "LLM_ANALYSIS_ENABLED", False):
            assert is_llm_analysis_required(
                decision=VerificationDecision.POTENTIAL_DUPLICATE,
                candidates=[cand],
                overall_score=0.94,
            ) is False


class TestPrunedContextBuilder:
    """Verify that Gemini receives only the current claim + top candidates + deterministic evidence."""

    def test_build_pruned_context_structure(self):
        claim = {
            "id": str(uuid4()),
            "claim_ref": "CLM-CURRENT",
            "merchant": "Uber",
            "amount": 1200.00,
            "currency": "INR",
            "claim_date": "2026-09-10",
            "claim_type": "Travel",
            "description": "Client visit travel",
            "employee_id": str(uuid4()),
        }
        extracted = {
            "merchant_normalized": "Uber India",
            "total": 1200.00,
            "transaction_date": "2026-09-10",
            "invoice_number": "UBR-9988",
        }
        candidates = [_make_candidate_match(f"CLM-{i}", score=0.90 - i * 0.1) for i in range(10)]

        context = build_pruned_context(
            claim=claim,
            extracted=extracted,
            top_candidates=candidates,
            decision=VerificationDecision.POTENTIAL_DUPLICATE,
            overall_score=0.90,
            triggered_rules=["RULE_EXACT_INVOICE_DUPLICATE"],
        )

        assert "current_claim" in context
        assert "top_historical_matches" in context
        assert "deterministic_evidence" in context

        # Ensure pruning: max 5 candidates included
        assert len(context["top_historical_matches"]) == 5
        assert context["top_historical_matches"][0]["matched_claim_ref"] == "CLM-0"

        # Verify target fields
        assert context["current_claim"]["merchant"] == "Uber India"
        assert context["current_claim"]["amount"] == 1200.00
        assert context["current_claim"]["invoice_number"] == "UBR-9988"

        # Verify deterministic evidence
        assert context["deterministic_evidence"]["engine_decision"] == "POTENTIAL_DUPLICATE"
        assert context["deterministic_evidence"]["overall_similarity_score"] == 0.90


class TestGeminiLlmAnalysis:
    """Verify Gemini API calls, schema responses, and graceful fallbacks."""

    def test_analyze_claim_with_mocked_gemini(self):
        claim = {
            "id": str(uuid4()),
            "claim_ref": "CLM-NEW",
            "merchant": "Uber",
            "amount": 1200.00,
            "currency": "INR",
            "claim_date": "2026-09-10",
            "employee_id": str(uuid4()),
        }
        candidates = [_make_candidate_match(claim_ref="CLM-8103", score=0.94)]

        mock_gemini_json = {
            "duplicate_risk_percentage": 94,
            "risk_classification": "HIGH RISK",
            "matched_claim_ref": "CLM-8103",
            "reasoning": "• Merchant name 'Uber India' matches target exactly.\n• Amount ₹1,200.00 is identical.\n• Invoice UBR-9988 is an exact match.",
            "manager_recommendation": (
                "Automation Alert: This claim closely matches CLM-8103 in merchant, amount, date, and invoice details. "
                "The automation engine estimates a 94% duplicate risk. Please verify whether this is a legitimate reimbursement or a duplicate claim."
            ),
            "suggested_action": "VERIFY_REIMBURSEMENT",
        }

        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_gemini_json)

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_cls.return_value = mock_client

            with patch("app.core.config.settings.GEMINI_API_KEY", "test-api-key"):
                result = analyze_claim_with_llm(
                    claim=claim,
                    extracted=None,
                    top_candidates=candidates,
                    decision=VerificationDecision.POTENTIAL_DUPLICATE,
                    overall_score=0.94,
                    triggered_rules=["RULE_EXACT_INVOICE_DUPLICATE"],
                )

        assert isinstance(result, LlmVerificationAnalysis)
        assert result.duplicate_risk_percentage == 94
        assert result.risk_classification == "HIGH RISK"
        assert result.matched_claim_ref == "CLM-8103"
        assert result.suggested_action == "VERIFY_REIMBURSEMENT"
        assert result.manager_recommendation.startswith("Automation Alert:")
        assert "CLM-8103" in result.manager_recommendation

    def test_analyze_claim_fallback_on_gemini_exception(self):
        claim = {
            "id": str(uuid4()),
            "claim_ref": "CLM-NEW",
            "merchant": "Uber",
            "amount": 1200.00,
            "currency": "INR",
            "employee_id": str(uuid4()),
        }
        candidates = [_make_candidate_match(claim_ref="CLM-8103", score=0.94)]

        with patch("google.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = RuntimeError("Gemini 503 Quota exceeded")
            mock_client_cls.return_value = mock_client

            with patch("app.core.config.settings.GEMINI_API_KEY", "test-api-key"):
                result = analyze_claim_with_llm(
                    claim=claim,
                    extracted=None,
                    top_candidates=candidates,
                    decision=VerificationDecision.POTENTIAL_DUPLICATE,
                    overall_score=0.94,
                    triggered_rules=["RULE_EXACT_INVOICE_DUPLICATE"],
                )

        # Fallback should gracefully produce a valid LlmVerificationAnalysis
        assert isinstance(result, LlmVerificationAnalysis)
        assert result.duplicate_risk_percentage == 94
        assert result.risk_classification == "CRITICAL RISK"
        assert result.model_used == "deterministic-fallback"
        assert result.manager_recommendation.startswith("Automation Alert:")
        assert "CLM-8103" in result.manager_recommendation
