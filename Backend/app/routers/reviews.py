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
    ManagerReviewCreate, ManagerReviewOut,
    FinanceReviewCreate, FinanceReviewOut,
)
from app.models.claims import ClaimListOut, ClaimOut
from app.models.enums import ClaimStatus, FinanceDecision

router = APIRouter(tags=["Reviews"])
logger = get_logger(__name__)

MANAGER_REVIEWABLE = {
    ClaimStatus.SUBMITTED.value,
    ClaimStatus.UNDER_REVIEW.value,
    ClaimStatus.FLAGGED.value,
}


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
            q = q.eq("status", status)
        else:
            # Default: all statuses a manager can act on
            q = q.in_("status", list(MANAGER_REVIEWABLE))

        result = q.order("submitted_at", desc=True).execute()
        logger.info("Listed manager pending claims", extra={"count": len(result.data)})
        return ClaimListOut(total=len(result.data), claims=result.data)
    except Exception as exc:
        logger.error("Failed to list manager claims", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/manager/claims/{claim_id}/approve",
    response_model=ManagerReviewOut,
    summary="Manager approves claim",
    description=(
        "Approves a claim. Self-approval is blocked — manager_id must differ from employee_id. "
        "Transitions: SUBMITTED / UNDER_REVIEW / FLAGGED → APPROVED."
    ),
)
def manager_approve(claim_id: UUID, body: ManagerReviewCreate):
    try:
        result = supabase.table("claims").select("*").eq("id", str(claim_id)).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
        claim = result.data

        # Self-approval block
        if str(body.manager_id) == claim["employee_id"]:
            raise HTTPException(
                status_code=403,
                detail="Self-approval is not permitted. A manager cannot approve their own claim.",
            )

        if claim["status"] not in MANAGER_REVIEWABLE:
            raise HTTPException(
                status_code=409,
                detail=f"Claim cannot be approved from status: {claim['status']}",
            )

        # Update claim
        supabase.table("claims").update({
            "status": ClaimStatus.APPROVED.value,
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
            ClaimStatus.APPROVED,
            f"Manager approved",
            comment=body.comment,
            actor_id=str(body.manager_id),
        )

        logger.info(
            "Claim approved by manager",
            extra={"claim_id": str(claim_id), "manager_id": str(body.manager_id)},
        )
        return review_result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to approve claim", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/manager/claims/{claim_id}/reject",
    response_model=ManagerReviewOut,
    summary="Manager rejects claim",
    description="Rejects a claim. Requires a comment explaining the rejection reason.",
)
def manager_reject(claim_id: UUID, body: ManagerReviewCreate):
    try:
        result = supabase.table("claims").select("*").eq("id", str(claim_id)).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
        claim = result.data

        if str(body.manager_id) == claim["employee_id"]:
            raise HTTPException(status_code=403, detail="Self-rejection is not permitted.")

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
FINANCE_REVIEWABLE = {ClaimStatus.APPROVED.value}


@router.get(
    "/finance/claims",
    response_model=ClaimListOut,
    summary="Claims in finance queue",
    description="Returns APPROVED claims with FINANCE_PENDING or FINANCE_EXCEPTION status.",
)
def finance_queue(
    finance_status: str | None = Query(None, description="Filter by finance_status"),
):
    try:
        q = supabase.table("claims").select("*").eq("status", ClaimStatus.APPROVED.value)
        if finance_status:
            q = q.eq("finance_status", finance_status)
        result = q.order("submitted_at", desc=True).execute()
        logger.info("Listed finance queue", extra={"count": len(result.data)})
        return ClaimListOut(total=len(result.data), claims=result.data)
    except Exception as exc:
        logger.error("Failed to list finance queue", exc_info=exc)
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
