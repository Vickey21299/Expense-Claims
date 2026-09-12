"""
app/services/verification/llm_analysis.py
Session 6B — Gemini Verification & Manager Recommendation Layer.

Performs forensic duplicate analysis using Google Gemini (gemini-2.5-flash)
with pruned context (target claim + top 1–5 candidate matches + deterministic signals).
Produces structured JSON including duplicate risk %, classification, reasoning,
and an actionable manager recommendation.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.models.enums import VerificationDecision
from app.models.verification import CandidateMatch, LlmVerificationAnalysis
from app.services.verification.config import verification_config

logger = get_logger(__name__)

# Structured schema for Gemini's response_schema (JSON mode)
_LLM_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "duplicate_risk_percentage": {
            "type": "integer",
            "description": "Estimated duplicate risk percentage from 0 to 100",
        },
        "risk_classification": {
            "type": "string",
            "enum": ["LOW RISK", "MEDIUM RISK", "HIGH RISK", "CRITICAL RISK"],
            "description": "Categorical risk assessment level",
        },
        "matched_claim_ref": {
            "type": "string",
            "description": "The claim_ref of the primary matched historical claim, or null if no strong match",
            "nullable": True,
        },
        "reasoning": {
            "type": "string",
            "description": "Clear, bulleted forensic explanation of matching and differing attributes, invoice/merchant variations, tip/tax differences, and timing.",
        },
        "manager_recommendation": {
            "type": "string",
            "description": "Concise, professional recommendation written for the approving manager starting with 'Automation Alert:' (e.g. 'Automation Alert: This claim closely matches CLM-8103 in merchant, amount, date, and invoice details. The automation engine estimates a 94% duplicate risk. Please verify whether this is a legitimate reimbursement or a duplicate claim.')",
        },
        "suggested_action": {
            "type": "string",
            "enum": ["APPROVE", "REJECT", "REQUEST_CLARIFICATION", "VERIFY_REIMBURSEMENT"],
            "description": "Suggested next action for the manager",
        },
    },
    "required": [
        "duplicate_risk_percentage",
        "risk_classification",
        "reasoning",
        "manager_recommendation",
        "suggested_action",
    ],
}

_SYSTEM_PROMPT = """You are an enterprise expense claim auditing and fraud prevention specialist.
Analyze the target expense claim against the provided top historical candidate matches and deterministic evidence.

Your objective:
1. Determine whether the current claim is a duplicate submission, an accidental double-claim, a split transaction, or a legitimate independent reimbursement (e.g., recurring monthly service or frequent commute).
2. Assess semantic nuances:
   - Identical invoice/receipt numbers with identical amounts represent near-certain duplicates.
   - Same merchant and exact same amount on consecutive days could be legitimate daily travel or duplicate submissions.
   - Minor amount differences may represent tip, currency exchange variance, or added service fees.
3. Compute an accurate Duplicate Risk Percentage (0% to 100%) and categorical Risk Classification:
   - 0-39%: LOW RISK
   - 40-69%: MEDIUM RISK
   - 70-89%: HIGH RISK
   - 90-100%: CRITICAL RISK
4. Provide forensic reasoning with clear bullet points outlining what matched and what differed.
5. Provide a crisp, professional 'manager_recommendation' starting specifically with:
   'Automation Alert: ...'
   Clearly state the matched claim reference, matching dimensions, estimated duplicate risk, and what the manager should check (e.g., whether this is a legitimate reimbursement or duplicate).
"""


def is_llm_analysis_required(
    decision: VerificationDecision,
    candidates: list[CandidateMatch],
    overall_score: float,
) -> bool:
    """
    Determine if LLM forensic analysis should be triggered.
    Returns False for clean claims with low similarity to save API latency and quota.
    """
    if not verification_config.LLM_ANALYSIS_ENABLED:
        return False

    # 1. Trigger if deterministic engine flagged an issue
    if decision in (
        VerificationDecision.POTENTIAL_DUPLICATE,
        VerificationDecision.BORDERLINE,
        VerificationDecision.ESCALATE_TO_MANAGER,
        VerificationDecision.WAITING_FOR_EXISTING_CLAIM,
    ):
        return True

    # 2. Trigger if overall score exceeds threshold
    if overall_score >= verification_config.LLM_TRIGGER_SCORE_THRESHOLD:
        return True

    # 3. Trigger if any top candidate exceeds threshold
    if candidates and candidates[0].similarity_score >= verification_config.LLM_TRIGGER_SCORE_THRESHOLD:
        return True

    return False


def build_pruned_context(
    claim: dict[str, Any],
    extracted: dict[str, Any] | None,
    top_candidates: list[CandidateMatch],
    decision: VerificationDecision,
    overall_score: float,
    triggered_rules: list[str],
) -> dict[str, Any]:
    """
    Prune and format the payload strictly to:
    Current Claim + Top 1-5 Historical Matches + Deterministic Evidence.
    Does NOT include the entire claims table history.
    """
    # 1. Current target claim
    t_merchant = (extracted.get("merchant_normalized") if extracted else None) or claim.get("merchant")
    t_amount = (extracted.get("total") if extracted else None) or claim.get("amount")
    t_date = (extracted.get("transaction_date") if extracted else None) or claim.get("claim_date")
    t_inv = (extracted.get("invoice_number") if extracted else None)

    target_data = {
        "claim_ref": claim.get("claim_ref"),
        "merchant": t_merchant,
        "amount": float(t_amount) if t_amount is not None else 0.0,
        "currency": claim.get("currency", "INR"),
        "date": str(t_date) if t_date else None,
        "invoice_number": t_inv,
        "claim_type": claim.get("claim_type"),
        "description": claim.get("description"),
        "employee_id": str(claim.get("employee_id")),
    }

    # 2. Top candidates (pruned to limit)
    limit = verification_config.LLM_TOP_CANDIDATES_LIMIT
    candidates_data = []
    for cand in top_candidates[:limit]:
        cand_dict = {
            "matched_claim_ref": cand.claim_ref or str(cand.matched_claim_id)[:8],
            "similarity_score": round(float(cand.similarity_score), 4),
            "status": str(cand.status),
            "age_days": cand.age_days,
            "same_employee": cand.field_scores.same_employee,
            "target_values": cand.target_values,
            "matched_values": cand.matched_values,
            "field_scores": {
                "merchant_similarity": round(cand.field_scores.merchant_similarity, 3),
                "amount_similarity": round(cand.field_scores.amount_similarity, 3),
                "date_similarity": round(cand.field_scores.date_similarity, 3),
                "invoice_similarity": (
                    round(cand.field_scores.invoice_similarity, 3)
                    if cand.field_scores.invoice_similarity is not None
                    else None
                ),
                "receipt_hash_match": cand.field_scores.receipt_hash_match,
            },
            "signals": cand.signals,
        }
        candidates_data.append(cand_dict)

    # 3. Deterministic evidence
    deterministic_evidence = {
        "engine_decision": decision.value,
        "overall_similarity_score": round(float(overall_score), 4),
        "triggered_rules": triggered_rules,
    }

    return {
        "current_claim": target_data,
        "top_historical_matches": candidates_data,
        "deterministic_evidence": deterministic_evidence,
    }


def _build_fallback_analysis(
    claim: dict[str, Any],
    top_candidates: list[CandidateMatch],
    decision: VerificationDecision,
    overall_score: float,
) -> LlmVerificationAnalysis:
    """Deterministic fallback if Gemini API call fails or times out."""
    strongest = top_candidates[0] if top_candidates else None
    matched_ref = (strongest.claim_ref or str(strongest.matched_claim_id)[:8]) if strongest else None
    pct = int(min(100, max(0, round(overall_score * 100))))

    if pct >= 90:
        classification = "CRITICAL RISK"
        action = "REJECT" if decision == VerificationDecision.POTENTIAL_DUPLICATE else "VERIFY_REIMBURSEMENT"
    elif pct >= 70:
        classification = "HIGH RISK"
        action = "VERIFY_REIMBURSEMENT"
    elif pct >= 40:
        classification = "MEDIUM RISK"
        action = "REQUEST_CLARIFICATION"
    else:
        classification = "LOW RISK"
        action = "APPROVE"

    signals_text = ", ".join(strongest.signals) if strongest and strongest.signals else "field similarity"
    recommendation = (
        f"Automation Alert: This claim closely matches {matched_ref or 'a historical claim'} "
        f"in {signals_text}. The automation engine estimates a {pct}% duplicate risk. "
        f"Please verify whether this is a legitimate reimbursement or a duplicate claim."
    )

    reasoning = (
        f"• Deterministic engine detected a {classification} condition with {pct}% duplicate risk.\n"
        f"• Matched against candidate {matched_ref or 'N/A'}.\n"
        f"• Key signals: {signals_text}."
    )

    return LlmVerificationAnalysis(
        duplicate_risk_percentage=pct,
        risk_classification=classification,
        matched_claim_ref=matched_ref,
        reasoning=reasoning,
        manager_recommendation=recommendation,
        suggested_action=action,
        analyzed_at=datetime.now(timezone.utc),
        model_used="deterministic-fallback",
    )


def analyze_claim_with_llm(
    claim: dict[str, Any],
    extracted: dict[str, Any] | None,
    top_candidates: list[CandidateMatch],
    decision: VerificationDecision,
    overall_score: float,
    triggered_rules: list[str],
) -> LlmVerificationAnalysis:
    """
    Execute Gemini forensic analysis on the pruned claim and candidate context.
    Returns a validated LlmVerificationAnalysis instance.
    """
    t_start = time.time()
    pruned_context = build_pruned_context(
        claim=claim,
        extracted=extracted,
        top_candidates=top_candidates,
        decision=decision,
        overall_score=overall_score,
        triggered_rules=triggered_rules,
    )

    context_json_str = json.dumps(pruned_context, indent=2, default=str)
    user_prompt = (
        f"Here is the expense claim comparison data:\n\n"
        f"{context_json_str}\n\n"
        f"Analyze the risk of duplication and provide your structured assessment and manager recommendation."
    )

    curr_label = claim.get("claim_ref") or str(claim.get("id"))[:8]
    logger.info(
        f"[LLM Verification] Sending forensic analysis request to Gemini "
        f"for claim '{curr_label}' against {len(pruned_context['top_historical_matches'])} candidate(s)..."
    )

    if not settings.GEMINI_API_KEY:
        logger.warning("[LLM Verification] GEMINI_API_KEY not configured. Using deterministic fallback.")
        return _build_fallback_analysis(claim, top_candidates, decision, overall_score)

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                types.Part.from_text(text=_SYSTEM_PROMPT),
                types.Part.from_text(text=user_prompt),
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                response_mime_type="application/json",
                response_schema=_LLM_ANALYSIS_SCHEMA,
            ),
        )

        elapsed = time.time() - t_start
        logger.info(f"[LLM Verification] Response received from Gemini in {elapsed:.2f}s")

        parsed = json.loads(response.text)
        analysis = LlmVerificationAnalysis(
            duplicate_risk_percentage=int(parsed["duplicate_risk_percentage"]),
            risk_classification=parsed["risk_classification"],
            matched_claim_ref=parsed.get("matched_claim_ref"),
            reasoning=parsed["reasoning"],
            manager_recommendation=parsed["manager_recommendation"],
            suggested_action=parsed.get("suggested_action", "VERIFY_REIMBURSEMENT"),
            analyzed_at=datetime.now(timezone.utc),
            model_used=settings.GEMINI_MODEL,
        )

        logger.info(
            f"[LLM Verification] Gemini verdict for '{curr_label}': "
            f"Risk={analysis.duplicate_risk_percentage}% ({analysis.risk_classification}), "
            f"Action={analysis.suggested_action}, Matched={analysis.matched_claim_ref}"
        )
        return analysis

    except Exception as exc:
        logger.error(f"[LLM Verification] Gemini call failed or timed out: {exc}. Falling back to deterministic analysis.", exc_info=exc)
        return _build_fallback_analysis(claim, top_candidates, decision, overall_score)
