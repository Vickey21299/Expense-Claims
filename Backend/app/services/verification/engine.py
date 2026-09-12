"""
app/services/verification/engine.py
Core orchestrator for the deterministic verification engine.
Runs candidate retrieval, scoring, rule checks, persistence, and state transitions.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.database import supabase
from app.core.logging import get_logger
from app.models.enums import ClaimStatus, VerificationStatus, VerificationDecision
from app.models.verification import (
    FieldSimilarityScores,
    CandidateMatch,
    VerificationRunOut,
    LlmVerificationAnalysis,
)
from app.services.verification.retrieval import retrieve_candidates
from app.services.verification.rules import evaluate_candidate, determine_verification_decision
from app.services.verification.llm_analysis import is_llm_analysis_required, analyze_claim_with_llm


logger = get_logger(__name__)


def _to_json_safe(data: Any) -> Any:
    """Helper to convert Decimals and datetimes for Supabase JSONB storage."""
    def _converter(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return str(obj)
    return json.loads(json.dumps(data, default=_converter))


def _append_claim_history(
    claim_id: str,
    from_status: str | None,
    to_status: str,
    event_label: str,
    comment: str | None = None,
) -> None:
    """Record status history event."""
    try:
        supabase.table("claim_status_history").insert({
            "claim_id": claim_id,
            "from_status": from_status,
            "to_status": to_status,
            "event_label": event_label,
            "comment": comment,
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"[Verification] Could not append history: {e}")


def run_verification(
    claim_id: str,
    in_memory_claim: dict | None = None,
    in_memory_extracted: dict | None = None,
    in_memory_doc: dict | None = None,
) -> VerificationRunOut:
    """
    Execute full deterministic verification for a claim.
    Validates claim eligibility, retrieves candidates, calculates similarities,
    applies lifecycle rules, persists evidence, and transitions claim state.

    Supports optional in-memory objects (claim, extracted, doc) to skip DB read queries
    during unified pipeline execution.
    """
    import time
    start_time = time.time()
    logger.info(f"========== [Verification Engine] Starting verification for claim_id={claim_id} ==========")

    # 1. Fetch target claim (or use in-memory)
    if in_memory_claim is not None:
        logger.info(f"[Verification] [1/5] Using in-memory claim details — skipped DB query!")
        claim = in_memory_claim
    else:
        logger.info(f"[Verification] [1/5] Fetching claim details from database...")
        claim_res = supabase.table("claims").select("*").eq("id", claim_id).single().execute()
        if not claim_res.data:
            raise ValueError(f"Claim {claim_id} not found.")
        claim = claim_res.data

    # 2. Check OCR / extracted data availability (or use in-memory)
    if in_memory_extracted is not None:
        logger.info(f"[Verification] [1/5] Using in-memory extracted data — skipped DB query!")
        extracted = in_memory_extracted
    else:
        extracted_res = (
            supabase.table("claim_extracted_data")
            .select("*")
            .eq("claim_id", claim_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        extracted = extracted_res.data[0] if extracted_res.data else None

    # Fetch document for checksum (or use in-memory)
    if in_memory_doc is not None:
        logger.info(f"[Verification] [1/5] Using in-memory document data — skipped DB query!")
        doc = in_memory_doc
    else:
        doc_res = (
            supabase.table("claim_documents")
            .select("*")
            .eq("claim_id", claim_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        doc = doc_res.data[0] if doc_res.data else None

    if not extracted and claim.get("ocr_status") in ("PENDING", "PROCESSING"):
        raise ValueError(
            "OCR processing must be completed before verification can run. "
            f"Current OCR status: {claim.get('ocr_status')}."
        )

    t_merchant = (extracted.get("merchant_normalized") if extracted else None) or claim.get("merchant")
    t_amount = (extracted.get("total") if extracted else None) or claim.get("amount")
    t_date = (extracted.get("transaction_date") if extracted else None) or claim.get("claim_date")
    t_inv = (extracted.get("invoice_number") if extracted else None)
    logger.info(
        f"[Verification] [1/5] Claim verified for OCR completion: "
        f"merchant='{t_merchant}', amount={t_amount} {claim.get('currency')}, "
        f"date={t_date}, invoice='{t_inv}'"
    )

    # 3. Retrieve historical candidates
    t_ret = time.time()
    logger.info(f"[Verification] [2/5] Querying historical database for candidate matches...")
    candidates_raw = retrieve_candidates(claim_id, claim, extracted, doc)
    logger.info(
        f"[Verification] [2/5] Candidate retrieval complete in {time.time() - t_ret:.2f}s: "
        f"found {len(candidates_raw)} historical candidate(s)"
    )

    # 4. Score each candidate
    t_score = time.time()
    logger.info(f"[Verification] [3/5] Scoring field-level similarities against {len(candidates_raw)} candidate(s)...")
    candidate_matches: list[CandidateMatch] = []
    curr_label = claim.get("claim_ref") or str(claim.get("id"))[:8]
    for cand in candidates_raw:
        match = evaluate_candidate(claim, extracted, doc, cand)
        candidate_matches.append(match)
        tv = match.target_values
        mv = match.matched_values
        cand_label = match.claim_ref or str(match.matched_claim_id)[:8]
        logger.info(
            f"    [MATCH DETAILS] Current ({curr_label}) vs Matched ({cand_label}) [Score: {match.similarity_score:.1%} | Status: {match.status}]:\n"
            f"      • Merchant: Current='{tv.get('merchant')}' vs Matched='{mv.get('merchant')}' -> Similarity={match.field_scores.merchant_similarity:.2f}\n"
            f"      • Amount:   Current={tv.get('amount')} vs Matched={mv.get('amount')} -> Similarity={match.field_scores.amount_similarity:.2f}\n"
            f"      • Date:     Current='{tv.get('date')}' vs Matched='{mv.get('date')}' -> Similarity={match.field_scores.date_similarity:.2f}\n"
            f"      • Invoice:  Current='{tv.get('invoice') or 'N/A'}' vs Matched='{mv.get('invoice') or 'N/A'}' -> Match={match.field_scores.invoice_similarity if match.field_scores.invoice_similarity is not None else 'N/A'}\n"
            f"      • Signals:  {match.signals if match.signals else 'None'}"
        )

    # 5. Determine decision
    logger.info(f"[Verification] [4/5] Evaluating deterministic lifecycle and fraud rules...")
    (
        decision,
        overall_score,
        strongest_match,
        wait_until,
        triggered_rules,
        explanation,
    ) = determine_verification_decision(claim, candidate_matches)

    if strongest_match:
        cand_label = strongest_match.claim_ref or str(strongest_match.matched_claim_id)[:8]
        logger.info(
            f"[Verification] [4/5] Strongest Match: Current '{curr_label}' matched with Historical '{cand_label}' "
            f"(Similarity: {strongest_match.similarity_score:.1%}, Status: {strongest_match.status}, Age: {strongest_match.age_days}d)"
        )
    else:
        logger.info(f"[Verification] [4/5] No historical candidates exceeded threshold for Current '{curr_label}'.")

    logger.info(
        f"[Verification] [4/5] Rule evaluation finished -> Decision: {decision.value} "
        f"(overall_score={overall_score:.4f}, triggered_rules={triggered_rules})"
    )

    # 5B. Session 6B — Gemini Verification & Manager Recommendation Layer
    llm_analysis: LlmVerificationAnalysis | None = None
    if is_llm_analysis_required(decision, candidate_matches, overall_score):
        logger.info(
            f"[Verification] [Session 6B] LLM Analysis required (decision={decision.value}, "
            f"score={overall_score:.2f}) -> Calling Gemini forensic analyzer..."
        )
        llm_analysis = analyze_claim_with_llm(
            claim=claim,
            extracted=extracted,
            top_candidates=candidate_matches,
            decision=decision,
            overall_score=overall_score,
            triggered_rules=triggered_rules,
        )
        if llm_analysis:
            logger.info(
                f"[Verification] [Session 6B] Gemini Recommendation:\n"
                f"    {llm_analysis.manager_recommendation}"
            )
            # Prepend manager recommendation to explanation
            explanation = f"{llm_analysis.manager_recommendation}\n\nDeterministic Rules:\n{explanation}"
    else:
        logger.info(
            f"[Verification] [Session 6B] LLM Analysis skipped (clean claim, score={overall_score:.2f} < threshold)"
        )

    logger.info(f"    Explanation: \"{explanation}\"")

    now_iso = datetime.now(timezone.utc).isoformat()
    now_dt = datetime.now(timezone.utc)

    # 6. Idempotency — Clean up existing records for this claim first
    logger.info(f"[Verification] [5/5] Persisting verification evidence & updating state machine...")
    try:
        supabase.table("duplicate_matches").delete().eq("claim_id", claim_id).execute()
        supabase.table("verification_results").delete().eq("claim_id", claim_id).execute()
        supabase.table("claim_verifications").delete().eq("claim_id", claim_id).execute()
    except Exception as e:
        logger.warning(f"[Verification] Cleanup prior to insert: {e}")

    # 7. Persist candidate matches into duplicate_matches table
    for match in candidate_matches:
        if match.similarity_score >= 0.50 or match.field_scores.receipt_hash_match:
            try:
                supabase.table("duplicate_matches").insert({
                    "claim_id": claim_id,
                    "matched_claim_id": str(match.matched_claim_id),
                    "similarity_score": float(match.similarity_score),
                    "assessment": f"Candidate match with status {match.status}",
                    "signals": _to_json_safe(match.signals),
                    "detected_by": "RULE",
                    "detected_at": now_iso,
                }).execute()
            except Exception as e:
                logger.warning(f"[Verification] Error saving duplicate match: {e}")

    # 8. Persist granular check row in verification_results table
    try:
        supabase.table("verification_results").insert({
            "claim_id": claim_id,
            "check_name": "DUPLICATE_AND_LIFECYCLE_VERIFICATION",
            "passed": decision == VerificationDecision.CLEAN,
            "message": llm_analysis.manager_recommendation if llm_analysis else explanation,
            "severity": "INFO" if decision == VerificationDecision.CLEAN else (
                "WARNING" if decision in (VerificationDecision.BORDERLINE, VerificationDecision.WAITING_FOR_EXISTING_CLAIM) else "ERROR"
            ),
            "checked_at": now_iso,
        }).execute()
    except Exception as e:
        logger.warning(f"[Verification] Error saving verification_results: {e}")

    # 9. Persist complete verification run into claim_verifications table
    evidence_data = {
        "candidate_count": len(candidate_matches),
        "strongest_match": strongest_match.model_dump(mode="json") if strongest_match else None,
        "all_candidates": [c.model_dump(mode="json") for c in candidate_matches[:10]],
        "llm_analysis": llm_analysis.model_dump(mode="json") if llm_analysis else None,
    }

    verification_record = {
        "claim_id": claim_id,
        "decision": decision.value,
        "similarity_score": float(overall_score),
        "strongest_match_claim_id": str(strongest_match.matched_claim_id) if strongest_match else None,
        "matched_claim_status": str(strongest_match.status) if strongest_match else None,
        "matched_claim_age_days": strongest_match.age_days if strongest_match else None,
        "wait_until": wait_until.isoformat() if wait_until else None,
        "field_scores": _to_json_safe(strongest_match.field_scores.model_dump()) if strongest_match else {},
        "triggered_rules": _to_json_safe(triggered_rules),
        "evidence": _to_json_safe(evidence_data),
        "explanation": explanation,
        "engine_version": "2.0.0-llm-verified" if llm_analysis else "1.0.0-deterministic",
        "verified_at": now_iso,
    }

    run_id = None
    try:
        run_res = supabase.table("claim_verifications").insert(verification_record).execute()
        if run_res.data:
            run_id = run_res.data[0].get("id")
    except Exception as e:
        logger.warning(f"[Verification] Could not insert into claim_verifications: {e}")

    # 10. Update Claim status and verification_status in state machine
    curr_status = claim.get("status")
    new_status = curr_status
    new_verif_status = "PENDING"
    history_comment = (
        llm_analysis.manager_recommendation
        if llm_analysis
        else explanation
    )

    if decision == VerificationDecision.CLEAN:
        new_verif_status = VerificationStatus.CLEAN.value
        # If in DRAFT or SUBMITTED, advance to UNDER_REVIEW (manager queue for clean claims)
        if curr_status in (ClaimStatus.DRAFT.value, ClaimStatus.SUBMITTED.value):
            new_status = ClaimStatus.UNDER_REVIEW.value
            _append_claim_history(
                claim_id,
                curr_status,
                new_status,
                "Verification Passed: CLEAN",
                "Claim passed deterministic verification with no duplicate risks. Ready for manager review.",
            )

    elif decision in (
        VerificationDecision.POTENTIAL_DUPLICATE,
        VerificationDecision.BORDERLINE,
        VerificationDecision.ESCALATE_TO_MANAGER,
    ):
        new_verif_status = VerificationStatus.FLAGGED.value
        # Transition to FLAGGED review queue
        if curr_status in (ClaimStatus.DRAFT.value, ClaimStatus.SUBMITTED.value, ClaimStatus.UNDER_REVIEW.value):
            new_status = ClaimStatus.FLAGGED.value
            _append_claim_history(
                claim_id,
                curr_status,
                new_status,
                f"Verification Flagged: {decision.value}",
                history_comment,
            )

    elif decision == VerificationDecision.WAITING_FOR_EXISTING_CLAIM:
        # Remains in SUBMITTED state with PENDING verification status
        new_verif_status = VerificationStatus.PENDING.value
        _append_claim_history(
            claim_id,
            curr_status,
            curr_status,
            "Verification Pending: Active Claim In Processing",
            history_comment,
        )

    try:
        supabase.table("claims").update({
            "status": new_status,
            "verification_status": new_verif_status,
        }).eq("id", claim_id).execute()
    except Exception as e:
        logger.error(f"[Verification] Error updating claim status: {e}")

    logger.info(f"[Verification] <<< Completed verification for claim_id={claim_id} -> decision={decision.value}")

    return VerificationRunOut(
        id=UUID(run_id) if run_id else None,
        claim_id=UUID(claim_id),
        decision=decision,
        similarity_score=overall_score,
        strongest_match_claim_id=strongest_match.matched_claim_id if strongest_match else None,
        strongest_match=strongest_match,
        matched_claim_status=str(strongest_match.status) if strongest_match else None,
        matched_claim_age_days=strongest_match.age_days if strongest_match else None,
        wait_until=wait_until,
        field_scores=strongest_match.field_scores if strongest_match else None,
        triggered_rules=triggered_rules,
        explanation=explanation,
        candidates=candidate_matches,
        llm_analysis=llm_analysis,
        engine_version="2.0.0-llm-verified" if llm_analysis else "1.0.0-deterministic",
        verified_at=now_dt,
    )


def get_latest_verification(claim_id: str) -> VerificationRunOut | None:
    """Retrieve the latest verification run for a claim."""
    try:
        res = (
            supabase.table("claim_verifications")
            .select("*")
            .eq("claim_id", claim_id)
            .order("verified_at", desc=True)
            .limit(1)
            .execute()
        )
        if not res.data:
            return None

        record = res.data[0]
        field_scores = (
            FieldSimilarityScores(**record["field_scores"])
            if record.get("field_scores")
            else None
        )

        evidence = record.get("evidence") or {}
        llm_data = evidence.get("llm_analysis")
        llm_analysis = LlmVerificationAnalysis(**llm_data) if llm_data else None

        candidates = []
        for c in evidence.get("all_candidates", []):
            try:
                candidates.append(CandidateMatch(**c))
            except Exception:
                pass

        return VerificationRunOut(
            id=UUID(record["id"]),
            claim_id=UUID(record["claim_id"]),
            decision=VerificationDecision(record["decision"]),
            similarity_score=float(record["similarity_score"]),
            strongest_match_claim_id=UUID(record["strongest_match_claim_id"]) if record.get("strongest_match_claim_id") else None,
            matched_claim_status=record.get("matched_claim_status"),
            matched_claim_age_days=record.get("matched_claim_age_days"),
            wait_until=datetime.fromisoformat(record["wait_until"]) if record.get("wait_until") else None,
            field_scores=field_scores,
            triggered_rules=record.get("triggered_rules", []),
            explanation=record.get("explanation", ""),
            candidates=candidates,
            llm_analysis=llm_analysis,
            engine_version=record.get("engine_version", "1.0.0-deterministic"),
            verified_at=datetime.fromisoformat(record["verified_at"]),
        )
    except Exception as e:
        logger.error(f"[Verification] Error fetching latest verification: {e}")
        return None

