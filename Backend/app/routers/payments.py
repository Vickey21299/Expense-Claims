"""
app/routers/payments.py
Payment recording endpoints.

GET  /api/v1/payments              List all payments
POST /api/v1/payments              Create payment record (READY_FOR_PAYMENT -> PAID)
GET  /api/v1/payments/{payment_id} Get payment detail
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.core.database import supabase
from app.core.logging import get_logger
from app.models.payments import PaymentCreate, PaymentOut, PaymentListOut
from app.models.enums import ClaimStatus
from app.services.payment import default_payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])
logger = get_logger(__name__)


@router.get(
    "",
    response_model=PaymentListOut,
    summary="List all payments",
)
def list_payments(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    try:
        result = supabase.table("payments").select("*") \
            .order("processed_at", desc=True).range(offset, offset + limit - 1).execute()
        logger.info("Listed payments", extra={"count": len(result.data)})
        return PaymentListOut(total=len(result.data), payments=result.data)
    except Exception as exc:
        logger.error("Failed to list payments", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get(
    "/{payment_id}",
    response_model=PaymentOut,
    summary="Get payment by ID",
)
def get_payment(payment_id: UUID):
    try:
        result = supabase.table("payments").select("*").eq("id", str(payment_id)).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Payment {payment_id} not found")
        return result.data
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get payment", extra={"payment_id": str(payment_id)}, exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post(
    "",
    response_model=PaymentOut,
    status_code=201,
    summary="Create payment record",
    description=(
        "Creates a payment via PaymentService and transitions the claim from READY_FOR_PAYMENT → PAID. "
        "PAID is a terminal state — no further transitions are possible. "
        "Returns 409 if claim is not READY_FOR_PAYMENT or already PAID."
    ),
)
async def create_payment(body: PaymentCreate):
    try:
        payment = await default_payment_service.execute_claim_payment(
            claim_id=body.claim_id,
            processed_by=body.processed_by,
            notes=body.notes,
            payment_reference=body.payment_reference,
        )
        return payment
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to create payment", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))
