"""
app/routers/reviews.py
Manager and Finance review endpoints.

Manager:
  GET  /api/v1/manager/claims                          Claims pending manager review
  POST /api/v1/manager/claims/{claim_id}/approve       Approve (SUBMITTED/UNDER_REVIEW/FLAGGED → APPROVED)
  POST /api/v1/manager/claims/{claim_id}/reject        Reject (→ REJECTED)

Finance:
  GET  /api/v1/finance/claims                          Claims in finance queue
  POST /api/v1/finance/claims/{claim_id}/verify        Clear or reject (APPROVED → READY_FOR_PAYMENT | FINANCE_REJECTED)
  POST /api/v1/finance/claims/{claim_id}/reject        Finance rejection shorthand
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.database import supabase
from app.core.logging import get_logger
from app.models.reviews import (
    ManagerReviewCreate,
    ManagerReviewOut,
    ManagerConfirmContext,
    ManagerClaimDossierOut,
    FinanceReviewCreate,
    FinanceReviewOut,
    FinanceClaimDossierOut,
    FinanceClearAction,
    FinanceRejectAction,
    FinancePayAction,
)
from app.models.payments import PaymentOut
from app.services.payment import default_payment_service
from app.models.claims import ClaimListOut, ClaimOut, StatusHistoryOut
from app.models.enums import ClaimStatus, FinanceDecision, VerificationStatus
from app.models.verification import CandidateMatch, LlmVerificationAnalysis

router = APIRouter(tags=["Reviews"])
logger = get_logger(__name__)

MANAGER_REVIEWABLE = {
    ClaimStatus.SUBMITTED.value,
    ClaimStatus.UNDER_REVIEW.value,
    ClaimStatus.FLAGGED.value,
}



def _verify_manager_authorization(claim: dict, manager_id: UUID) -> None:
    """
    Enforces assigned manager authorization and blocks self-approval.
    """
    if str(manager_id) == claim.get("employee_id"):
        raise HTTPException(
            status_code=403,
            detail="Self-approval is not permitted. A manager cannot act on their own claim.",
        )
    if claim.get("manager_id") and str(manager_id) != str(claim["manager_id"]):
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: You are not the assigned manager for claim {claim.get('claim_ref') or claim.get('id')}.",
        )


# ===========================================================================
# Manager routes
# ===========================================================================
@router.get(
    "/manager/claims",
    response_model=ClaimListOut,
    summary="Claims pending manager review",
    description="Returns all claims currently awaiting a manager decision, optionally filtered by manager_id.",
)
def manager_pending_claims(
    manager_id: UUID | None = Query(None, description="Filter by manager's user ID"),
    status: str | None = Query(None, description="Default: SUBMITTED,UNDER_REVIEW,FLAGGED"),
):
    try:
        q = supabase.table("claims").select("*")
        if manager_id:
            q = q.eq("manager_id", str(manager_id))

        if status:
            status_clean = status.strip().upper()
            if status_clean == "PENDING":
                q = q.in_("status", list(MANAGER_REVIEWABLE))
            elif status_clean == "APPROVED":
                q = q.in_("status", [ClaimStatus.APPROVED.value, ClaimStatus.MANAGER_CONFIRMED.value, ClaimStatus.READY_FOR_PAYMENT.value, ClaimStatus.PAID.value])
            elif status_clean == "REJECTED":
                q = q.eq("status", ClaimStatus.REJECTED.value)
            elif "," in status_clean:
                q = q.in_("status", [s.strip() for s in status_clean.split(",")])
            elif status_clean != "ALL":
                q = q.eq("status", status.strip())
        else:
            # Default when no filter: return all active team claims (excluding unsubmitted drafts)
            q = q.neq("status", ClaimStatus.DRAFT.value)

        result = q.order("created_at", desc=True).execute()
        claims_data = result.data or []

        if claims_data:
            claim_ids = [c["id"] for c in claims_data]

            # 1. Attach verification and AI analysis
            try:
                ver_res = (
                    supabase.table("claim_verifications")
                    .select("*")
                    .in_("claim_id", claim_ids)
                    .order("verified_at", desc=True)
                    .execute()
                )
                ver_map: dict[str, dict] = {}
                for v in (ver_res.data or []):
                    if v["claim_id"] not in ver_map:
                        ver_map[v["claim_id"]] = v

                for c in claims_data:
                    ver = ver_map.get(c["id"])
                    if ver:
                        evidence = ver.get("evidence") or {}
                        llm_data = evidence.get("llm_analysis")
                        if llm_data:
                            c["manager_recommendation"] = llm_data.get("manager_recommendation")
                            c["duplicate_risk_percentage"] = llm_data.get("duplicate_risk_percentage")
                            c["risk_classification"] = llm_data.get("risk_classification")
                            c["llm_analysis"] = llm_data
                        else:
                            c["manager_recommendation"] = ver.get("explanation")
                            c["duplicate_risk_percentage"] = int(min(100, float(ver.get("similarity_score", 0.0)) * 100))
                            c["risk_classification"] = "HIGH RISK" if c["duplicate_risk_percentage"] >= 70 else ("MEDIUM RISK" if c["duplicate_risk_percentage"] >= 40 else "LOW RISK")
            except Exception as e:
                logger.warning(f"[ManagerClaims] Could not attach verification details: {e}")

            # 2. Attach latest manager reviews and comments
            try:
                mgr_res = (
                    supabase.table("manager_reviews")
                    .select("*")
                    .in_("claim_id", claim_ids)
                    .order("reviewed_at", desc=True)
                    .execute()
                )
                mgr_map: dict[str, dict] = {}
                for m in (mgr_res.data or []):
                    if m["claim_id"] not in mgr_map:
                        mgr_map[m["claim_id"]] = m

                for c in claims_data:
                    m = mgr_map.get(c["id"])
                    if m:
                        c["manager_comment"] = m.get("comment")
            except Exception as e:
                logger.warning(f"[ManagerClaims] Could not attach manager reviews: {e}")

            # 3. Attach employee info
            try:
                emp_ids = list({c["employee_id"] for c in claims_data if c.get("employee_id")})
                if emp_ids:
                    emp_res = supabase.table("users").select("id, full_name, email, department, role, job_title").in_("id", emp_ids).execute()
                    emp_map = {u["id"]: u for u in (emp_res.data or [])}
                    for c in claims_data:
                        emp = emp_map.get(c.get("employee_id"))
                        if emp:
                            c["employee"] = emp
                            c["employee_name"] = emp.get("full_name")
            except Exception as e:
                logger.warning(f"[ManagerClaims] Could not attach employee profiles: {e}")

        logger.info("Listed manager pending claims", extra={"count": len(claims_data)})
        return ClaimListOut(total=len(claims_data), claims=claims_data)
    except Exception as exc:
        logger.error("Failed to list manager claims", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/manager/claims/{claim_id}",
    response_model=ManagerClaimDossierOut,
    summary="Get comprehensive manager review dossier",
    description=(
        "Returns full claim details, employee profile, receipt documents, OCR extracted data, "
        "deterministic verification scores, Gemini forensic reasoning & recommendation, "
        "top 1–5 matched historical claims, and complete status history."
    ),
)
def manager_claim_dossier(claim_id: UUID):
    try:
        # 1. Fetch claim
        claim_res = supabase.table("claims").select("*").eq("id", str(claim_id)).single().execute()
        if not claim_res.data:
            raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
        claim = claim_res.data

        # 2. Fetch employee profile
        emp_res = supabase.table("users").select("id, full_name, email, department, role").eq("id", claim["employee_id"]).execute()
        employee = emp_res.data[0] if emp_res.data else None

        # 3. Fetch documents
        docs_res = supabase.table("claim_documents").select("*").eq("claim_id", str(claim_id)).execute()
        documents = docs_res.data or []

        # 4. Fetch extracted OCR data
        ext_res = supabase.table("claim_extracted_data").select("*").eq("claim_id", str(claim_id)).order("created_at", desc=True).limit(1).execute()
        extracted_data = ext_res.data[0] if ext_res.data else None

        # 5. Fetch verification run and evidence
        ver_run = (
            supabase.table("claim_verifications")
            .select("*")
            .eq("claim_id", str(claim_id))
            .order("verified_at", desc=True)
            .limit(1)
            .execute()
        )
        ver_record = ver_run.data[0] if ver_run.data else None
        evidence = ver_record.get("evidence") if ver_record else {}

        # 6. Parse LLM analysis
        llm_analysis = None
        if evidence and evidence.get("llm_analysis"):
            try:
                llm_analysis = LlmVerificationAnalysis(**evidence["llm_analysis"])
            except Exception:
                pass

        # 7. Parse matched candidates
        matched_candidates = []
        if evidence and evidence.get("all_candidates"):
            for c in evidence["all_candidates"][:5]:
                try:
                    matched_candidates.append(CandidateMatch(**c))
                except Exception:
                    pass

        # 8. Fetch status history
        hist_res = supabase.table("claim_status_history").select("*").eq("claim_id", str(claim_id)).order("occurred_at").execute()
        status_history = hist_res.data or []

        # 9. Compute allowed actions
        is_flagged = claim.get("status") == ClaimStatus.FLAGGED.value or claim.get("verification_status") == VerificationStatus.FLAGGED.value
        if is_flagged:
            allowed_actions = ["CONFIRM_CONTEXT", "REJECT"]
        elif claim.get("status") in (ClaimStatus.UNDER_REVIEW.value, ClaimStatus.SUBMITTED.value):
            allowed_actions = ["APPROVE", "REJECT"]
        else:
            allowed_actions = []

        # Attach manager alert and duplicate risk onto claim object
        if llm_analysis:
            claim["manager_recommendation"] = llm_analysis.manager_recommendation
            claim["duplicate_risk_percentage"] = llm_analysis.duplicate_risk_percentage
            claim["risk_classification"] = llm_analysis.risk_classification
            claim["llm_analysis"] = llm_analysis
        elif ver_record:
            claim["manager_recommendation"] = ver_record.get("explanation")
            claim["duplicate_risk_percentage"] = int(min(100, float(ver_record.get("similarity_score", 0.0)) * 100))
            claim["risk_classification"] = "HIGH RISK" if claim["duplicate_risk_percentage"] >= 70 else ("MEDIUM RISK" if claim["duplicate_risk_percentage"] >= 40 else "LOW RISK")

        return ManagerClaimDossierOut(
            claim=ClaimOut(**claim),
            employee=employee,
            documents=documents,
            extracted_data=extracted_data,
            verification=ver_record,
            llm_analysis=llm_analysis,
            matched_candidates=matched_candidates,
            status_history=status_history,
            allowed_actions=allowed_actions,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to build manager claim dossier", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/manager/claims/{claim_id}/approve",
    response_model=ManagerReviewOut,
    summary="Manager approves clean claim",
    description=(
        "Approves a clean claim. Self-approval is blocked and only the assigned manager can approve. "
        "Flagged claims are BLOCKED from direct approval (must use /confirm). "
        "Transitions: UNDER_REVIEW / SUBMITTED → READY_FOR_PAYMENT."
    ),
)
def manager_approve(claim_id: UUID, body: ManagerReviewCreate):
    try:
        result = supabase.table("claims").select("*").eq("id", str(claim_id)).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
        claim = result.data

        # Enforce assigned manager authorization & block self-approval
        _verify_manager_authorization(claim, body.manager_id)

        # IMPORTANT: Block flagged claims from direct approval to READY_FOR_PAYMENT
        if (
            claim.get("status") == ClaimStatus.FLAGGED.value
            or claim.get("verification_status") == VerificationStatus.FLAGGED.value
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Flagged claims cannot be directly approved as READY_FOR_PAYMENT. "
                    "The manager must confirm the business context with a valid justification using "
                    f"POST /api/v1/manager/claims/{claim_id}/confirm so Finance can independently review."
                ),
            )

        if claim["status"] not in (ClaimStatus.SUBMITTED.value, ClaimStatus.UNDER_REVIEW.value, ClaimStatus.APPROVED.value):
            raise HTTPException(
                status_code=409,
                detail=f"Claim cannot be approved from status: {claim['status']}",
            )

        # Update claim to READY_FOR_PAYMENT
        supabase.table("claims").update({
            "status": ClaimStatus.READY_FOR_PAYMENT.value,
            "finance_status": FinanceDecision.FINANCE_PENDING.value,
        }).eq("id", str(claim_id)).execute()

        # Insert manager review record
        review_payload = {
            "claim_id": str(claim_id),
            "manager_id": str(body.manager_id),
            "decision": "APPROVED",
            "comment": body.comment,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        review_result = supabase.table("manager_reviews").insert(review_payload).execute()

        # Status history
        _append_history(
            str(claim_id),
            ClaimStatus(claim["status"]),
            ClaimStatus.READY_FOR_PAYMENT,
            "Manager Approved (Clean Claim)",
            comment=body.comment or "Clean claim approved by manager as READY_FOR_PAYMENT",
            actor_id=str(body.manager_id),
        )

        logger.info(
            "Claim approved by manager -> READY_FOR_PAYMENT",
            extra={"claim_id": str(claim_id), "manager_id": str(body.manager_id)},
        )
        return review_result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to approve claim", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/manager/claims/{claim_id}/confirm",
    response_model=ManagerReviewOut,
    summary="Manager confirms business context for flagged claim",
    description=(
        "Confirms business context for a FLAGGED claim with a required justification comment. "
        "Enforces assigned manager authorization. "
        "Transitions: FLAGGED → MANAGER_CONFIRMED (queued for Finance independent review)."
    ),
)
def manager_confirm_context(claim_id: UUID, body: ManagerConfirmContext):
    try:
        result = supabase.table("claims").select("*").eq("id", str(claim_id)).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
        claim = result.data

        # Enforce assigned manager authorization & block self-approval
        _verify_manager_authorization(claim, body.manager_id)

        # Comment is required
        if not body.comment or not body.comment.strip():
            raise HTTPException(
                status_code=422,
                detail="Manager comment/reason is required to confirm business context for a flagged claim.",
            )

        if claim["status"] not in (ClaimStatus.FLAGGED.value, ClaimStatus.UNDER_REVIEW.value):
            raise HTTPException(
                status_code=409,
                detail=f"Only FLAGGED claims require business context confirmation. Current status: {claim['status']}",
            )

        # Update claim to MANAGER_CONFIRMED (with resilient fallback if postgres enum has not yet been altered)
        try:
            supabase.table("claims").update({
                "status": ClaimStatus.MANAGER_CONFIRMED.value,
                "finance_status": FinanceDecision.FINANCE_PENDING.value,
            }).eq("id", str(claim_id)).execute()
            new_status = ClaimStatus.MANAGER_CONFIRMED
        except Exception as e:
            logger.warning(f"Could not set status to MANAGER_CONFIRMED ({e}). Using fallback APPROVED/FINANCE_PENDING for finance queue.")
            supabase.table("claims").update({
                "status": ClaimStatus.APPROVED.value,
                "finance_status": FinanceDecision.FINANCE_PENDING.value,
            }).eq("id", str(claim_id)).execute()
            new_status = ClaimStatus.APPROVED


        # Insert manager review record
        review_payload = {
            "claim_id": str(claim_id),
            "manager_id": str(body.manager_id),
            "decision": "CONFIRMED",
            "comment": body.comment,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        review_result = supabase.table("manager_reviews").insert(review_payload).execute()

        # Append status history
        _append_history(
            str(claim_id),
            ClaimStatus(claim["status"]),
            new_status,
            "Manager Confirmed Business Context",
            comment=body.comment,
            actor_id=str(body.manager_id),
        )

        logger.info(
            "Flagged claim confirmed by manager -> queued for Finance",
            extra={"claim_id": str(claim_id), "manager_id": str(body.manager_id)},
        )
        return review_result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to confirm business context", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/manager/claims/{claim_id}/reject",
    response_model=ManagerReviewOut,
    summary="Manager rejects claim",
    description="Rejects a claim. Requires a comment explaining the rejection reason. Enforces assigned manager authorization.",
)
def manager_reject(claim_id: UUID, body: ManagerReviewCreate):
    try:
        result = supabase.table("claims").select("*").eq("id", str(claim_id)).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
        claim = result.data

        # Enforce assigned manager authorization & block self-approval
        _verify_manager_authorization(claim, body.manager_id)

        # Comment is required for rejection
        if not body.comment or not body.comment.strip():
            raise HTTPException(
                status_code=422,
                detail="A comment explaining the rejection reason is required when rejecting a claim.",
            )

        if claim["status"] not in MANAGER_REVIEWABLE:
            raise HTTPException(
                status_code=409,
                detail=f"Claim cannot be rejected from status: {claim['status']}",
            )

        supabase.table("claims").update({
            "status": ClaimStatus.REJECTED.value,
        }).eq("id", str(claim_id)).execute()

        review_payload = {
            "claim_id": str(claim_id),
            "manager_id": str(body.manager_id),
            "decision": "REJECTED",
            "comment": body.comment,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        review_result = supabase.table("manager_reviews").insert(review_payload).execute()

        _append_history(
            str(claim_id),
            ClaimStatus(claim["status"]),
            ClaimStatus.REJECTED,
            "Manager rejected",
            comment=body.comment,
            actor_id=str(body.manager_id),
        )

        logger.info(
            "Claim rejected by manager",
            extra={"claim_id": str(claim_id), "manager_id": str(body.manager_id)},
        )
        return review_result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to reject claim", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ===========================================================================
# Finance routes
# ===========================================================================
FINANCE_REVIEWABLE = {
    ClaimStatus.APPROVED.value,
    ClaimStatus.READY_FOR_PAYMENT.value,
    ClaimStatus.MANAGER_CONFIRMED.value,
}



@router.get(
    "/finance/claims",
    response_model=ClaimListOut,
    summary="Claims in finance queue",
    description="Returns claims awaiting finance review/clearing, enriched with manager comments and AI recommendations.",
)
def finance_queue(
    finance_status: str | None = Query(None, description="Filter by finance_status"),
):
    try:
        q = supabase.table("claims").select("*")

        if finance_status:
            status_clean = finance_status.strip().upper()
            if status_clean == "PAID":
                q = q.eq("status", ClaimStatus.PAID.value)
            elif status_clean == "FINANCE_PENDING":
                q = q.or_(f"finance_status.eq.{FinanceDecision.FINANCE_PENDING.value},status.eq.{ClaimStatus.APPROVED.value},status.eq.{ClaimStatus.MANAGER_CONFIRMED.value}")
            elif status_clean in (FinanceDecision.FINANCE_CLEARED.value, FinanceDecision.FINANCE_REJECTED.value, FinanceDecision.FINANCE_EXCEPTION.value):
                q = q.eq("finance_status", status_clean)
            elif status_clean != "ALL":
                q = q.eq("finance_status", status_clean)
            else:
                q = q.neq("status", ClaimStatus.DRAFT.value)
        else:
            # Default: all claims in finance queue or processed
            q = q.in_("status", [
                ClaimStatus.APPROVED.value,
                ClaimStatus.MANAGER_CONFIRMED.value,
                ClaimStatus.READY_FOR_PAYMENT.value,
                ClaimStatus.PAID.value,
                ClaimStatus.REJECTED.value,
                ClaimStatus.FLAGGED.value,
            ])

        result = q.order("created_at", desc=True).execute()
        claims_data = result.data or []

        if claims_data:
            claim_ids = [c["id"] for c in claims_data]

            # 1. Attach latest manager reviews and comments
            try:
                mgr_res = (
                    supabase.table("manager_reviews")
                    .select("*")
                    .in_("claim_id", claim_ids)
                    .order("reviewed_at", desc=True)
                    .execute()
                )
                mgr_map: dict[str, dict] = {}
                for m in (mgr_res.data or []):
                    if m["claim_id"] not in mgr_map:
                        mgr_map[m["claim_id"]] = m

                for c in claims_data:
                    m = mgr_map.get(c["id"])
                    if m:
                        c["manager_comment"] = m.get("comment")
            except Exception as e:
                logger.warning(f"[FinanceQueue] Could not attach manager reviews: {e}")

            # 2. Attach latest verification details
            try:
                ver_res = (
                    supabase.table("claim_verifications")
                    .select("*")
                    .in_("claim_id", claim_ids)
                    .order("verified_at", desc=True)
                    .execute()
                )
                ver_map: dict[str, dict] = {}
                for v in (ver_res.data or []):
                    if v["claim_id"] not in ver_map:
                        ver_map[v["claim_id"]] = v

                for c in claims_data:
                    ver = ver_map.get(c["id"])
                    if ver:
                        evidence = ver.get("evidence") or {}
                        llm_data = evidence.get("llm_analysis")
                        if llm_data:
                            c["manager_recommendation"] = llm_data.get("manager_recommendation")
                            c["duplicate_risk_percentage"] = llm_data.get("duplicate_risk_percentage")
                            c["risk_classification"] = llm_data.get("risk_classification")
                            try:
                                c["llm_analysis"] = LlmVerificationAnalysis(**llm_data)
                            except Exception:
                                c["llm_analysis"] = None
                        else:
                            c["manager_recommendation"] = ver.get("explanation")
                            c["duplicate_risk_percentage"] = int(min(100, float(ver.get("similarity_score", 0.0)) * 100))
                            c["risk_classification"] = "HIGH RISK" if c["duplicate_risk_percentage"] >= 70 else ("MEDIUM RISK" if c["duplicate_risk_percentage"] >= 40 else "LOW RISK")
            except Exception as e:
                logger.warning(f"[FinanceQueue] Could not attach verification details: {e}")

            # 3. Attach employee info
            try:
                emp_ids = list({c["employee_id"] for c in claims_data if c.get("employee_id")})
                if emp_ids:
                    emp_res = supabase.table("users").select("id, full_name, email, department, role, job_title").in_("id", emp_ids).execute()
                    emp_map = {u["id"]: u for u in (emp_res.data or [])}
                    for c in claims_data:
                        emp = emp_map.get(c.get("employee_id"))
                        if emp:
                            c["employee"] = emp
                            c["employee_name"] = emp.get("full_name")
            except Exception as e:
                logger.warning(f"[FinanceQueue] Could not attach employee profiles: {e}")

        logger.info("Listed finance queue", extra={"count": len(claims_data)})
        return ClaimListOut(total=len(claims_data), claims=claims_data)
    except Exception as exc:
        logger.error("Failed to list finance queue", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/finance/claims/{claim_id}",
    response_model=FinanceClaimDossierOut,
    summary="Finance claim details & review dossier",
    description=(
        "Returns full claim details, employee profile, receipt documents, OCR extracted data, "
        "deterministic verification scores, Gemini forensic reasoning & recommendation, "
        "manager decision and comment, matched historical candidates, payment information, and complete status history."
    ),
)
def finance_claim_dossier(claim_id: UUID):
    try:
        # 1. Fetch claim
        claim_res = supabase.table("claims").select("*").eq("id", str(claim_id)).single().execute()
        if not claim_res.data:
            raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
        claim = claim_res.data

        # 2. Fetch employee profile
        emp_res = supabase.table("users").select("id, full_name, email, department, role, job_title").eq("id", claim["employee_id"]).execute()
        employee = emp_res.data[0] if emp_res.data else None

        # 3. Fetch documents
        docs_res = supabase.table("claim_documents").select("*").eq("claim_id", str(claim_id)).execute()
        documents = docs_res.data or []

        # 4. Fetch extracted OCR data
        ext_res = supabase.table("claim_extracted_data").select("*").eq("claim_id", str(claim_id)).order("created_at", desc=True).limit(1).execute()
        extracted_data = ext_res.data[0] if ext_res.data else None

        # 5. Fetch verification run and evidence
        ver_run = (
            supabase.table("claim_verifications")
            .select("*")
            .eq("claim_id", str(claim_id))
            .order("verified_at", desc=True)
            .limit(1)
            .execute()
        )
        ver_record = ver_run.data[0] if ver_run.data else None
        evidence = ver_record.get("evidence") if ver_record else {}

        # 6. Parse LLM analysis
        llm_analysis = None
        if evidence and evidence.get("llm_analysis"):
            try:
                llm_analysis = LlmVerificationAnalysis(**evidence["llm_analysis"])
            except Exception:
                pass

        # 7. Parse matched candidates
        matched_candidates = []
        if evidence and evidence.get("all_candidates"):
            for c in evidence["all_candidates"][:5]:
                try:
                    matched_candidates.append(CandidateMatch(**c))
                except Exception:
                    pass

        # 8. Fetch latest manager review
        mgr_res = (
            supabase.table("manager_reviews")
            .select("*")
            .eq("claim_id", str(claim_id))
            .order("reviewed_at", desc=True)
            .limit(1)
            .execute()
        )
        manager_review = mgr_res.data[0] if mgr_res.data else None

        # 9. Fetch payment info if available
        pay_res = (
            supabase.table("payments")
            .select("*")
            .eq("claim_id", str(claim_id))
            .limit(1)
            .execute()
        )
        payment_info = pay_res.data[0] if pay_res.data else None

        # 10. Fetch status history
        hist_res = supabase.table("claim_status_history").select("*").eq("claim_id", str(claim_id)).order("occurred_at").execute()
        status_history = hist_res.data or []

        # 11. Compute allowed actions for Finance
        status = claim.get("status")
        if status in (ClaimStatus.MANAGER_CONFIRMED.value, ClaimStatus.APPROVED.value):
            allowed_actions = ["CLEAR_ANOMALY", "REJECT"]
        elif status == ClaimStatus.READY_FOR_PAYMENT.value:
            allowed_actions = ["EXECUTE_PAYMENT", "REJECT"]
        else:
            allowed_actions = []

        # Enrich claim object with AI metrics and manager comment
        if llm_analysis:
            claim["manager_recommendation"] = llm_analysis.manager_recommendation
            claim["duplicate_risk_percentage"] = llm_analysis.duplicate_risk_percentage
            claim["risk_classification"] = llm_analysis.risk_classification
            claim["llm_analysis"] = llm_analysis
        elif ver_record:
            claim["manager_recommendation"] = ver_record.get("explanation")
            claim["duplicate_risk_percentage"] = int(min(100, float(ver_record.get("similarity_score", 0.0)) * 100))
            claim["risk_classification"] = "HIGH RISK" if claim["duplicate_risk_percentage"] >= 70 else ("MEDIUM RISK" if claim["duplicate_risk_percentage"] >= 40 else "LOW RISK")

        if manager_review and manager_review.get("comment"):
            claim["manager_comment"] = manager_review["comment"]

        return FinanceClaimDossierOut(
            claim=ClaimOut(**claim),
            employee=employee,
            documents=documents,
            extracted_data=extracted_data,
            verification=ver_record,
            llm_analysis=llm_analysis,
            manager_review=manager_review,
            matched_candidates=matched_candidates,
            payment_info=payment_info,
            status_history=status_history,
            allowed_actions=allowed_actions,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to build finance claim dossier", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/finance/claims/{claim_id}/clear",
    response_model=FinanceReviewOut,
    summary="Finance clears anomaly — ready for payment",
    description=(
        "Finance clears an anomaly for a MANAGER_CONFIRMED or APPROVED claim. "
        "Transitions claim to READY_FOR_PAYMENT and sets finance_status to FINANCE_CLEARED."
    ),
)
def finance_clear(claim_id: UUID, body: FinanceClearAction):
    try:
        result = supabase.table("claims").select("*").eq("id", str(claim_id)).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
        claim = result.data

        # Only MANAGER_CONFIRMED or APPROVED claims can be cleared by finance
        valid_clear_statuses = {
            ClaimStatus.MANAGER_CONFIRMED.value,
            ClaimStatus.APPROVED.value,
        }
        if claim["status"] not in valid_clear_statuses:
            raise HTTPException(
                status_code=409,
                detail=f"Finance can only clear claims in MANAGER_CONFIRMED or APPROVED status. Current status: '{claim['status']}'",
            )

        now_iso = datetime.now(timezone.utc).isoformat()

        supabase.table("claims").update({
            "status": ClaimStatus.READY_FOR_PAYMENT.value,
            "finance_status": FinanceDecision.FINANCE_CLEARED.value,
        }).eq("id", str(claim_id)).execute()

        review_payload = {
            "claim_id": str(claim_id),
            "finance_user_id": str(body.finance_user_id),
            "decision": FinanceDecision.FINANCE_CLEARED.value,
            "cleared": True,
            "comment": body.comment,
            "reviewed_at": now_iso,
        }
        review_result = supabase.table("finance_reviews").insert(review_payload).execute()

        _append_history(
            str(claim_id),
            ClaimStatus(claim["status"]),
            ClaimStatus.READY_FOR_PAYMENT,
            "Finance cleared anomaly — ready for payment",
            comment=body.comment,
            actor_id=str(body.finance_user_id),
        )

        logger.info(
            "Finance cleared claim for payment",
            extra={"claim_id": str(claim_id), "finance_user_id": str(body.finance_user_id)},
        )
        return review_result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to clear claim in finance", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/finance/claims/{claim_id}/reject",
    response_model=FinanceReviewOut,
    summary="Finance rejects claim",
    description=(
        "Finance rejects a claim. Requires a reason explaining the rejection. "
        "Transitions claim to REJECTED and sets finance_status to FINANCE_REJECTED."
    ),
)
def finance_reject(claim_id: UUID, body: FinanceRejectAction):
    try:
        # Enforce reason
        if not body.reason or not body.reason.strip():
            raise HTTPException(
                status_code=422,
                detail="A reason is required when rejecting a claim from finance.",
            )

        result = supabase.table("claims").select("*").eq("id", str(claim_id)).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
        claim = result.data

        valid_reject_statuses = {
            ClaimStatus.MANAGER_CONFIRMED.value,
            ClaimStatus.APPROVED.value,
            ClaimStatus.READY_FOR_PAYMENT.value,
        }
        if claim["status"] not in valid_reject_statuses:
            raise HTTPException(
                status_code=409,
                detail=f"Finance cannot reject claim from status: '{claim['status']}'",
            )

        now_iso = datetime.now(timezone.utc).isoformat()

        supabase.table("claims").update({
            "status": ClaimStatus.REJECTED.value,
            "finance_status": FinanceDecision.FINANCE_REJECTED.value,
        }).eq("id", str(claim_id)).execute()

        review_payload = {
            "claim_id": str(claim_id),
            "finance_user_id": str(body.finance_user_id),
            "decision": FinanceDecision.FINANCE_REJECTED.value,
            "cleared": False,
            "comment": body.reason.strip(),
            "reviewed_at": now_iso,
        }
        review_result = supabase.table("finance_reviews").insert(review_payload).execute()

        _append_history(
            str(claim_id),
            ClaimStatus(claim["status"]),
            ClaimStatus.REJECTED,
            "Finance rejected",
            comment=body.reason.strip(),
            actor_id=str(body.finance_user_id),
        )

        logger.info(
            "Claim rejected by finance",
            extra={"claim_id": str(claim_id), "finance_user_id": str(body.finance_user_id)},
        )
        return review_result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to reject claim in finance", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/finance/claims/{claim_id}/pay",
    response_model=PaymentOut,
    summary="Finance initiates payment",
    description=(
        "Executes payment for a READY_FOR_PAYMENT claim via PaymentService. "
        "Transitions claim to PAID (terminal state). "
        "Returns 409 if claim is not READY_FOR_PAYMENT or already PAID."
    ),
)
async def finance_pay(claim_id: UUID, body: FinancePayAction):
    try:
        payment = await default_payment_service.execute_claim_payment(
            claim_id=claim_id,
            processed_by=body.finance_user_id,
            notes=body.notes,
            payment_reference=body.payment_reference,
        )
        return payment
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to initiate payment from finance", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/finance/claims/{claim_id}/verify",
    response_model=FinanceReviewOut,
    summary="Finance verifies claim",
    description=(
        "Finance decision on an APPROVED claim. "
        "FINANCE_CLEARED → READY_FOR_PAYMENT. "
        "FINANCE_REJECTED stays at APPROVED with finance_status=FINANCE_REJECTED. "
        "FINANCE_EXCEPTION flags for manual investigation."
    ),
)
def finance_verify(claim_id: UUID, body: FinanceReviewCreate):
    try:
        result = supabase.table("claims").select("*").eq("id", str(claim_id)).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
        claim = result.data

        if claim["status"] not in FINANCE_REVIEWABLE:
            raise HTTPException(
                status_code=409,
                detail=f"Finance can only review APPROVED claims. Current: {claim['status']}",
            )

        # Determine resulting claim status
        new_claim_status = claim["status"]
        if body.decision == FinanceDecision.FINANCE_CLEARED:
            new_claim_status = ClaimStatus.READY_FOR_PAYMENT.value
            history_label = "Finance cleared — ready for payment"
        elif body.decision == FinanceDecision.FINANCE_REJECTED:
            history_label = "Finance rejected"
        else:
            history_label = "Finance flagged as exception"

        supabase.table("claims").update({
            "status": new_claim_status,
            "finance_status": body.decision.value,
        }).eq("id", str(claim_id)).execute()

        review_payload = {
            "claim_id": str(claim_id),
            "finance_user_id": str(body.finance_user_id),
            "decision": body.decision.value,
            "cleared": body.cleared,
            "comment": body.comment,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        review_result = supabase.table("finance_reviews").insert(review_payload).execute()

        _append_history(
            str(claim_id),
            ClaimStatus(claim["status"]),
            ClaimStatus(new_claim_status),
            history_label,
            comment=body.comment,
            actor_id=str(body.finance_user_id),
        )

        logger.info(
            "Finance review completed",
            extra={
                "claim_id": str(claim_id),
                "decision": body.decision.value,
                "finance_user_id": str(body.finance_user_id),
            },
        )
        return review_result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to process finance review", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Shared helper (also used by claims router)
# ---------------------------------------------------------------------------
def _append_history(
    claim_id: str,
    from_status: ClaimStatus | None,
    to_status: ClaimStatus,
    event_label: str,
    comment: str | None = None,
    actor_id: str | None = None,
) -> None:
    payload: dict = {
        "claim_id": claim_id,
        "to_status": to_status if isinstance(to_status, str) else to_status.value,
        "event_label": event_label,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    if from_status:
        payload["from_status"] = from_status if isinstance(from_status, str) else from_status.value
    if comment:
        payload["comment"] = comment
    if actor_id:
        payload["actor_id"] = actor_id
    supabase.table("claim_status_history").insert(payload).execute()
