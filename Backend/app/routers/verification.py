"""
app/routers/verification.py
Verification Engine endpoints.

POST /api/v1/verification/claims/{claim_id}/run   Run deterministic verification
GET  /api/v1/verification/claims/{claim_id}       Get latest verification result
"""
from uuid import UUID
from fastapi import APIRouter, HTTPException

from app.core.logging import get_logger
from app.models.verification import VerificationRunOut
from app.services.verification import run_verification, get_latest_verification

router = APIRouter(prefix="/verification", tags=["Verification"])
logger = get_logger(__name__)


@router.post(
    "/claims/{claim_id}/run",
    response_model=VerificationRunOut,
    summary="Run verification on a claim",
    description=(
        "Executes deterministic verification comparing the claim against historical claims. "
        "Evaluates duplicate risk, borderline similarity, active processing status, "
        "and lifecycle rules. Enforces server-side claim state transitions."
    ),
)
def execute_verification(claim_id: UUID):
    try:
        logger.info(f"[API:Verification] Triggered verification for claim_id={claim_id}")
        result = run_verification(str(claim_id))
        return result
    except ValueError as e:
        logger.warning(f"[API:Verification] Bad request for claim_id={claim_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[API:Verification] Failed verifying claim_id={claim_id}: {exc}", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/claims/{claim_id}",
    response_model=VerificationRunOut,
    summary="Get latest verification result",
    description="Retrieves the most recent verification run and explainability audit for a claim.",
)
def fetch_verification(claim_id: UUID):
    try:
        result = get_latest_verification(str(claim_id))
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No verification record found for claim {claim_id}. Run verification first.",
            )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"[API:Verification] Failed fetching verification: {exc}", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))
