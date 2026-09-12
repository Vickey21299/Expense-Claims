"""
app/services/verification/rules.py
Deterministic rule evaluation, claim lifecycle inspection, and explainability generation.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from app.models.enums import ClaimStatus, VerificationDecision
from app.models.verification import FieldSimilarityScores, CandidateMatch
from app.services.verification.config import verification_config
from app.services.verification.similarity import (
    calculate_merchant_similarity,
    calculate_amount_similarity,
    calculate_date_similarity,
    calculate_invoice_similarity,
    calculate_category_similarity,
    calculate_weighted_overall_score,
)


ACTIVE_PROCESSING_STATUSES = {
    ClaimStatus.SUBMITTED.value,
    ClaimStatus.UNDER_REVIEW.value,
    ClaimStatus.FLAGGED.value,
    ClaimStatus.APPROVED.value,
    ClaimStatus.READY_FOR_PAYMENT.value,
}

TERMINAL_PAID_STATUSES = {
    ClaimStatus.PAID.value,
}

CLOSED_REJECTED_STATUSES = {
    ClaimStatus.REJECTED.value,
}


def evaluate_candidate(
    target_claim: dict[str, Any],
    target_extracted: dict[str, Any] | None,
    target_doc: dict[str, Any] | None,
    candidate: dict[str, Any],
) -> CandidateMatch:
    """
    Score a single historical candidate against the target claim.
    """
    c_claim = candidate["claim"]
    c_extracted = candidate.get("extracted") or {}
    c_doc = candidate.get("document") or {}

    # 1. Target values (prefer extracted normalized values where available)
    t_merchant = (target_extracted.get("merchant_normalized") if target_extracted else None) or target_claim.get("merchant")
    t_amount = (target_extracted.get("total") if target_extracted else None) or target_claim.get("amount")
    t_date = (target_extracted.get("transaction_date") if target_extracted else None) or target_claim.get("claim_date")
    t_invoice = target_extracted.get("invoice_number") if target_extracted else None
    t_category = target_claim.get("claim_type")
    t_checksum = target_doc.get("checksum") if target_doc else None
    t_employee = target_claim.get("employee_id")

    # 2. Candidate values
    c_merchant = c_extracted.get("merchant_normalized") or c_claim.get("merchant")
    c_amount = c_extracted.get("total") or c_claim.get("amount")
    c_date = c_extracted.get("transaction_date") or c_claim.get("claim_date")
    c_invoice = c_extracted.get("invoice_number")
    c_category = c_claim.get("claim_type")
    c_checksum = c_doc.get("checksum")
    c_employee = c_claim.get("employee_id")

    # 3. Field similarities
    m_sim = calculate_merchant_similarity(t_merchant, c_merchant)
    a_sim = calculate_amount_similarity(t_amount, c_amount)
    d_sim = calculate_date_similarity(t_date, c_date)
    i_sim = calculate_invoice_similarity(t_invoice, c_invoice)
    cat_sim = calculate_category_similarity(t_category, c_category)
    receipt_match = bool(t_checksum and c_checksum and t_checksum == c_checksum)
    same_emp = bool(t_employee and c_employee and str(t_employee) == str(c_employee))

    overall = calculate_weighted_overall_score(m_sim, a_sim, d_sim, i_sim, cat_sim)

    # 4. Signals and rule triggers
    signals: list[str] = []
    if receipt_match:
        signals.append("Exact receipt file / SHA-256 hash match")
        overall = 1.0
    if i_sim == 1.0 and t_invoice:
        signals.append(f"Exact invoice number match ('{t_invoice}')")
        overall = max(0.95, overall)
    if m_sim >= 0.95 and a_sim >= 0.98 and d_sim >= 0.95:
        signals.append("Exact merchant, amount, and date match")
        overall = max(0.95, overall)
    elif m_sim >= 0.85 and a_sim >= 0.90 and d_sim >= 0.80:
        signals.append(f"Strong match with historical claim (similarity {overall:.0%})")
    elif overall >= verification_config.BORDERLINE_THRESHOLD:
        signals.append(f"Borderline similarity with historical claim ({overall:.0%})")

    if same_emp:
        signals.append("Submitted by the same employee")

    # Calculate age in days
    submitted_time = c_claim.get("submitted_at") or c_claim.get("created_at")
    age_days = 0
    sub_dt = None
    if submitted_time:
        try:
            sub_dt = datetime.fromisoformat(str(submitted_time).replace("Z", "+00:00"))
            age_days = max(0, (datetime.now(timezone.utc) - sub_dt).days)
        except Exception:
            pass

    field_scores = FieldSimilarityScores(
        merchant_similarity=m_sim,
        amount_similarity=a_sim,
        date_similarity=d_sim,
        invoice_similarity=i_sim,
        category_similarity=cat_sim,
        receipt_hash_match=receipt_match,
        same_employee=same_emp,
    )

    target_values = {
        "merchant": t_merchant,
        "amount": float(t_amount) if t_amount is not None else None,
        "date": str(t_date) if t_date is not None else None,
        "invoice": t_invoice,
        "category": t_category,
        "employee_id": str(t_employee) if t_employee else None,
        "checksum": t_checksum,
    }
    matched_values = {
        "merchant": c_merchant,
        "amount": float(c_amount) if c_amount is not None else None,
        "date": str(c_date) if c_date is not None else None,
        "invoice": c_invoice,
        "category": c_category,
        "employee_id": str(c_employee) if c_employee else None,
        "checksum": c_checksum,
    }

    return CandidateMatch(
        matched_claim_id=c_claim["id"],
        claim_ref=c_claim.get("claim_ref"),
        similarity_score=overall,
        status=c_claim.get("status", "UNKNOWN"),
        created_at=c_claim.get("created_at"),
        submitted_at=sub_dt,
        age_days=age_days,
        field_scores=field_scores,
        signals=signals,
        target_values=target_values,
        matched_values=matched_values,
    )


def determine_verification_decision(
    target_claim: dict[str, Any],
    candidate_matches: list[CandidateMatch],
) -> tuple[VerificationDecision, float, CandidateMatch | None, datetime | None, list[str], str]:
    """
    Evaluate candidate matches against deterministic thresholds & lifecycle rules.

    Returns:
      (decision, overall_similarity_score, strongest_match, wait_until, triggered_rules, explanation)
    """
    if not candidate_matches:
        return (
            VerificationDecision.CLEAN,
            0.0,
            None,
            None,
            [],
            "No historical candidates found matching this claim. Claim passed verification checks.",
        )

    # Sort candidates by similarity score descending
    sorted_candidates = sorted(candidate_matches, key=lambda c: c.similarity_score, reverse=True)

    # Filter out candidates that were REJECTED (Case 3: closed without payment)
    # A rejected claim does not block legitimate resubmission or new verification.
    non_rejected = [c for c in sorted_candidates if c.status not in CLOSED_REJECTED_STATUSES]

    if not non_rejected:
        # All candidates were REJECTED claims!
        top_rejected = sorted_candidates[0]
        ref = top_rejected.claim_ref or str(top_rejected.matched_claim_id)[:8]
        return (
            VerificationDecision.CLEAN,
            0.0,
            None,
            None,
            ["PREVIOUS_CLAIM_REJECTED"],
            f"Matching historical claim {ref} was previously REJECTED without payment. "
            "Normal verification passed for this claim.",
        )

    strongest = non_rejected[0]
    score = strongest.similarity_score
    ref = strongest.claim_ref or str(strongest.matched_claim_id)[:8]
    status = strongest.status
    age_days = strongest.age_days
    triggered_rules: list[str] = []

    # Check if strong match
    is_strong = (
        score >= verification_config.STRONG_MATCH_THRESHOLD
        or strongest.field_scores.receipt_hash_match
        or (strongest.field_scores.invoice_similarity == 1.0 and strongest.field_scores.invoice_similarity is not None)
    )

    if not is_strong:
        # Check if borderline
        if score >= verification_config.BORDERLINE_THRESHOLD:
            triggered_rules.append("BORDERLINE_SIMILARITY")
            explanation = (
                f"Borderline similarity ({score:.0%}) detected with historical claim {ref} "
                f"(status: {status}). Flagged for manual review."
            )
            return (
                VerificationDecision.BORDERLINE,
                score,
                strongest,
                None,
                triggered_rules,
                explanation,
            )

        # Weak match below threshold -> CLEAN
        return (
            VerificationDecision.CLEAN,
            score,
            strongest,
            None,
            [],
            f"Highest historical similarity with claim {ref} is low ({score:.0%}). "
            "Claim passed verification checks.",
        )

    # --- Strong / Exact Match Lifecycle Checks ---
    if strongest.field_scores.receipt_hash_match:
        triggered_rules.append("EXACT_RECEIPT_HASH")
    if strongest.field_scores.invoice_similarity == 1.0:
        triggered_rules.append("EXACT_INVOICE_NUMBER")
    if score >= verification_config.STRONG_MATCH_THRESHOLD:
        triggered_rules.append("STRONG_SIMILARITY_MATCH")

    # Case 1: Existing claim is PAID/COMPLETED
    if status in TERMINAL_PAID_STATUSES:
        triggered_rules.append("DUPLICATE_PAID_CLAIM")
        explanation = (
            f"Strong duplicate match ({score:.0%}) found with claim {ref}. "
            f"Existing claim has already been PAID. High reclaim/duplicate risk."
        )
        return (
            VerificationDecision.POTENTIAL_DUPLICATE,
            score,
            strongest,
            None,
            triggered_rules,
            explanation,
        )

    # Case 2: Existing claim is still actively processing
    if status in ACTIVE_PROCESSING_STATUSES:
        wait_days = verification_config.WAIT_PERIOD_DAYS
        if age_days < wait_days:
            # Active processing within wait window
            triggered_rules.append("ACTIVE_CLAIM_WAITING")
            sub_time = strongest.submitted_at or datetime.now(timezone.utc)
            wait_until = sub_time + timedelta(days=wait_days)
            wait_date_str = wait_until.strftime("%Y-%m-%d")

            explanation = (
                f"Matching claim {ref} is currently under active processing ({status}) "
                f"and has been active for {age_days} day(s). "
                f"Employee must wait until {wait_date_str} before attempting to reclaim."
            )
            return (
                VerificationDecision.WAITING_FOR_EXISTING_CLAIM,
                score,
                strongest,
                wait_until,
                triggered_rules,
                explanation,
            )
        else:
            # Active processing exceeded wait period -> ESCALATE TO MANAGER
            triggered_rules.append("ACTIVE_CLAIM_EXCEEDED_WAIT_PERIOD")
            explanation = (
                f"Matching claim {ref} is currently {status} and has exceeded the processing "
                f"period of {wait_days} days (active for {age_days} days). "
                "Escalated to manager to verify if employee is legitimately reclaiming due to processing delay."
            )
            return (
                VerificationDecision.ESCALATE_TO_MANAGER,
                score,
                strongest,
                None,
                triggered_rules,
                explanation,
            )

    # Fallback: Potential duplicate for any other strong match status
    triggered_rules.append("POTENTIAL_DUPLICATE")
    explanation = (
        f"Strong duplicate match ({score:.0%}) found with claim {ref} (status: {status}). "
        "Flagged for manager review."
    )
    return (
        VerificationDecision.POTENTIAL_DUPLICATE,
        score,
        strongest,
        None,
        triggered_rules,
        explanation,
    )
