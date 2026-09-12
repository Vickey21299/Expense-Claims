"""
app/routers/claims.py
Full claim lifecycle endpoints.

POST   /api/v1/claims                              Create draft claim
GET    /api/v1/claims                              List claims (filterable)
GET    /api/v1/claims/{claim_id}                   Get full claim detail
PUT    /api/v1/claims/{claim_id}                   Update draft claim
DELETE /api/v1/claims/{claim_id}                   Delete draft claim
POST   /api/v1/claims/{claim_id}/submit            DRAFT -> SUBMITTED
GET    /api/v1/claims/{claim_id}/verification      Verification results
GET    /api/v1/claims/{claim_id}/duplicates        Duplicate matches
GET    /api/v1/claims/{claim_id}/history           Status history
GET    /api/v1/claims/{claim_id}/documents         Documents
GET    /api/v1/claims/{claim_id}/items             Line items
POST   /api/v1/claims/{claim_id}/items             Add line item
"""
import random
import string
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.database import supabase
from app.core.logging import get_logger
from app.models.claims import (
    ClaimCreate, ClaimUpdate, ClaimOut, ClaimListOut,
    ClaimDetailOut, ClaimSubmitResponse,
    VerificationResultOut, DuplicateMatchOut, StatusHistoryOut,
    ClaimDocumentOut, ClaimItemOut, ClaimItemCreate,
)
from app.models.enums import ClaimStatus, ALLOWED_TRANSITIONS

router = APIRouter(prefix="/claims", tags=["Claims"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _generate_claim_ref() -> str:
    """Generate a unique human-readable claim ref like CLM-48291."""
    import time
    for _ in range(10):
        suffix = "".join(random.choices(string.digits, k=5))
        ref = f"CLM-{suffix}"
        res = supabase.table("claims").select("id").eq("claim_ref", ref).execute()
        if not res.data:
            return ref
    return f"CLM-{int(time.time() * 1000) % 1000000:06d}"


def _append_history(
    claim_id: str,
    from_status: ClaimStatus | None,
    to_status: ClaimStatus,
    event_label: str,
    comment: str | None = None,
    actor_name: str | None = None,
    actor_id: str | None = None,
) -> None:
    """Insert a single status history record."""
    payload: dict = {
        "claim_id": claim_id,
        "to_status": to_status.value,
        "event_label": event_label,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    if from_status:
        payload["from_status"] = from_status.value
    if comment:
        payload["comment"] = comment
    if actor_name:
        payload["actor_name"] = actor_name
    if actor_id:
        payload["actor_id"] = actor_id
    supabase.table("claim_status_history").insert(payload).execute()


def _get_claim_or_404(claim_id: str) -> dict:
    """Fetch a claim row by UUID or claim_ref, or raise 404."""
    ident = str(claim_id).strip()
    is_uuid = False
    try:
        UUID(ident)
        is_uuid = True
    except ValueError:
        is_uuid = False

    if is_uuid:
        result = supabase.table("claims").select("*").eq("id", ident).execute()
    else:
        result = supabase.table("claims").select("*").ilike("claim_ref", ident).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return result.data[0]


# ---------------------------------------------------------------------------
# List & create
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=ClaimListOut,
    summary="List claims",
    description="List all claims. Filter by status, employee_id, manager_id, or finance_status.",
)
def list_claims(
    status: str | None = Query(None, description="ClaimStatus value"),
    employee_id: UUID | None = Query(None),
    manager_id: UUID | None = Query(None),
    finance_status: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    try:
        q = supabase.table("claims").select("*")
        if status:
            q = q.eq("status", status)
        if employee_id:
            q = q.eq("employee_id", str(employee_id))
        if manager_id:
            q = q.eq("manager_id", str(manager_id))
        if finance_status:
            q = q.eq("finance_status", finance_status)
        result = q.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        logger.info("Listed claims", extra={"count": len(result.data), "filters": {
            "status": status, "employee_id": str(employee_id) if employee_id else None,
        }})
        return ClaimListOut(total=len(result.data), claims=result.data)
    except Exception as exc:
        logger.error("Failed to list claims", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "",
    response_model=ClaimOut,
    status_code=201,
    summary="Create draft claim",
)
def create_claim(body: ClaimCreate):
    try:
        payload = body.model_dump(exclude_none=True)
        payload["employee_id"] = str(payload["employee_id"])
        if "manager_id" in payload:
            payload["manager_id"] = str(payload["manager_id"])
        if "claim_date" in payload and payload["claim_date"] is not None:
            payload["claim_date"] = str(payload["claim_date"])

        # Generate ref
        payload["claim_ref"] = _generate_claim_ref()
        payload["status"] = ClaimStatus.DRAFT.value

        result = supabase.table("claims").insert(payload).execute()
        claim = result.data[0]

        # Seed history
        _append_history(
            claim["id"], None, ClaimStatus.DRAFT,
            "Claim created as draft",
        )

        logger.info("Claim created", extra={"claim_id": claim["id"], "claim_ref": claim["claim_ref"]})
        return claim
    except Exception as exc:
        logger.error("Failed to create claim", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Get single claim (summary)
# ---------------------------------------------------------------------------
@router.get(
    "/{claim_id}",
    response_model=ClaimDetailOut,
    summary="Get full claim detail",
    description="Returns claim with nested verification results, duplicate matches, and status history.",
)
def get_claim(claim_id: str):
    try:
        claim = _get_claim_or_404(claim_id)
        actual_id = claim["id"]

        # Fetch related data
        ver = supabase.table("verification_results").select("*").eq("claim_id", actual_id).execute()
        dup = supabase.table("duplicate_matches").select("*").eq("claim_id", actual_id).execute()
        hist = supabase.table("claim_status_history").select("*").eq("claim_id", actual_id).order("occurred_at").execute()
        docs = supabase.table("claim_documents").select("*").eq("claim_id", actual_id).order("created_at").execute()

        claim["verification_results"] = ver.data or []
        claim["duplicate_matches"] = dup.data or []
        claim["status_history"] = hist.data or []
        claim["documents"] = docs.data or []

        # Fetch latest verification and LLM analysis
        try:
            ver_run = (
                supabase.table("claim_verifications")
                .select("*")
                .eq("claim_id", actual_id)
                .order("verified_at", desc=True)
                .limit(1)
                .execute()
            )
            if ver_run.data:
                latest_v = ver_run.data[0]
                claim["latest_verification"] = latest_v
                evidence = latest_v.get("evidence") or {}
                llm_data = evidence.get("llm_analysis")
                if llm_data:
                    claim["manager_recommendation"] = llm_data.get("manager_recommendation")
                    claim["duplicate_risk_percentage"] = llm_data.get("duplicate_risk_percentage")
                    claim["risk_classification"] = llm_data.get("risk_classification")
                    claim["llm_analysis"] = llm_data
                else:
                    claim["manager_recommendation"] = latest_v.get("explanation")
                    claim["duplicate_risk_percentage"] = int(min(100, float(latest_v.get("similarity_score", 0.0)) * 100))
                    claim["risk_classification"] = "HIGH RISK" if claim["duplicate_risk_percentage"] >= 70 else ("MEDIUM RISK" if claim["duplicate_risk_percentage"] >= 40 else "LOW RISK")
        except Exception as e:
            logger.warning(f"[ClaimDetail] Could not attach latest verification: {e}")

        # Fetch latest manager review / comment
        try:
            mgr_rev = (
                supabase.table("manager_reviews")
                .select("comment")
                .eq("claim_id", actual_id)
                .order("reviewed_at", desc=True)
                .limit(1)
                .execute()
            )
            if mgr_rev.data and mgr_rev.data[0].get("comment"):
                claim["manager_comment"] = mgr_rev.data[0]["comment"]
        except Exception as e:
            logger.warning(f"[ClaimDetail] Could not attach manager comment: {e}")

        # Fetch latest finance review / comment
        try:
            fin_rev = (
                supabase.table("finance_reviews")
                .select("comment")
                .eq("claim_id", actual_id)
                .order("reviewed_at", desc=True)
                .limit(1)
                .execute()
            )
            if fin_rev.data and fin_rev.data[0].get("comment"):
                claim["finance_comment"] = fin_rev.data[0]["comment"]
        except Exception as e:
            logger.warning(f"[ClaimDetail] Could not attach finance comment: {e}")

        logger.info("Fetched claim detail", extra={"claim_id": str(claim_id), "actual_id": actual_id})
        return claim
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get claim", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))



# ---------------------------------------------------------------------------
# Update draft claim
# ---------------------------------------------------------------------------
@router.put(
    "/{claim_id}",
    response_model=ClaimOut,
    summary="Update claim (draft only)",
    description="Only DRAFT claims can be edited. Returns 409 if claim is not in DRAFT status.",
)
def update_claim(claim_id: UUID, body: ClaimUpdate):
    try:
        claim = _get_claim_or_404(str(claim_id))
        if claim["status"] != ClaimStatus.DRAFT.value:
            raise HTTPException(
                status_code=409,
                detail=f"Only DRAFT claims can be edited. Current status: {claim['status']}",
            )

        payload = body.model_dump(exclude_none=True)
        if "manager_id" in payload:
            payload["manager_id"] = str(payload["manager_id"])
        if "claim_date" in payload and payload["claim_date"] is not None:
            payload["claim_date"] = str(payload["claim_date"])

        result = supabase.table("claims").update(payload).eq("id", str(claim_id)).execute()
        logger.info("Claim updated", extra={"claim_id": str(claim_id)})
        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to update claim", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Delete draft claim
# ---------------------------------------------------------------------------
@router.delete(
    "/{claim_id}",
    status_code=204,
    summary="Delete draft claim",
    description="Only DRAFT claims can be deleted.",
)
def delete_claim(claim_id: UUID):
    try:
        claim = _get_claim_or_404(str(claim_id))
        if claim["status"] != ClaimStatus.DRAFT.value:
            raise HTTPException(
                status_code=409,
                detail=f"Only DRAFT claims can be deleted. Current status: {claim['status']}",
            )
        supabase.table("claims").delete().eq("id", str(claim_id)).execute()
        logger.info("Claim deleted", extra={"claim_id": str(claim_id)})
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to delete claim", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------
@router.post(
    "/{claim_id}/submit",
    response_model=ClaimSubmitResponse,
    summary="Submit claim (DRAFT → SUBMITTED)",
    description=(
        "Transitions a DRAFT claim to SUBMITTED. "
        "In Phase 2, this will trigger the verification engine."
    ),
)
def submit_claim(claim_id: UUID):
    try:
        claim = _get_claim_or_404(str(claim_id))

        if claim["status"] != ClaimStatus.DRAFT.value:
            raise HTTPException(
                status_code=409,
                detail=f"Only DRAFT claims can be submitted. Current status: {claim['status']}",
            )

        now = datetime.now(timezone.utc).isoformat()
        result = supabase.table("claims").update({
            "status": ClaimStatus.SUBMITTED.value,
            "submitted_at": now,
            "ocr_status": "PENDING",
            "verification_status": "PENDING",
        }).eq("id", str(claim_id)).execute()

        _append_history(
            str(claim_id),
            ClaimStatus.DRAFT,
            ClaimStatus.SUBMITTED,
            "Claim submitted",
        )

        logger.info(
            "Claim submitted",
            extra={"claim_id": str(claim_id), "claim_ref": claim.get("claim_ref")},
        )
        updated = result.data[0]
        return ClaimSubmitResponse(
            claim_id=updated["id"],
            claim_ref=updated.get("claim_ref"),
            status=ClaimStatus.SUBMITTED,
            message="Claim submitted successfully. Verification pending.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to submit claim", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# Sub-resources
# ---------------------------------------------------------------------------
@router.get(
    "/{claim_id}/verification",
    response_model=list[VerificationResultOut],
    summary="Get verification results",
)
def get_verification_results(claim_id: UUID):
    try:
        _get_claim_or_404(str(claim_id))
        result = supabase.table("verification_results").select("*").eq("claim_id", str(claim_id)).execute()
        return result.data
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get verification", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/{claim_id}/duplicates",
    response_model=list[DuplicateMatchOut],
    summary="Get duplicate match results",
)
def get_duplicates(claim_id: UUID):
    try:
        _get_claim_or_404(str(claim_id))
        result = supabase.table("duplicate_matches").select("*").eq("claim_id", str(claim_id)).execute()
        return result.data
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get duplicates", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/{claim_id}/history",
    response_model=list[StatusHistoryOut],
    summary="Get status history",
)
def get_status_history(claim_id: UUID):
    try:
        _get_claim_or_404(str(claim_id))
        result = supabase.table("claim_status_history").select("*") \
            .eq("claim_id", str(claim_id)).order("occurred_at").execute()
        return result.data
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get history", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/{claim_id}/documents",
    response_model=list[ClaimDocumentOut],
    summary="Get claim documents",
)
def get_documents(claim_id: UUID):
    try:
        _get_claim_or_404(str(claim_id))
        result = supabase.table("claim_documents").select("*").eq("claim_id", str(claim_id)).execute()
        return result.data
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get documents", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/{claim_id}/items",
    response_model=list[ClaimItemOut],
    summary="Get claim line items",
)
def get_items(claim_id: UUID):
    try:
        _get_claim_or_404(str(claim_id))
        result = supabase.table("claim_items").select("*").eq("claim_id", str(claim_id)).execute()
        return result.data
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get items", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "/{claim_id}/items",
    response_model=ClaimItemOut,
    status_code=201,
    summary="Add line item to claim",
)
def add_item(claim_id: UUID, body: ClaimItemCreate):
    try:
        _get_claim_or_404(str(claim_id))
        payload = body.model_dump(exclude_none=True)
        payload["claim_id"] = str(claim_id)
        if "document_id" in payload and payload["document_id"]:
            payload["document_id"] = str(payload["document_id"])
        result = supabase.table("claim_items").insert(payload).execute()
        logger.info("Line item added", extra={"claim_id": str(claim_id)})
        return result.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to add item", extra={"claim_id": str(claim_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))
