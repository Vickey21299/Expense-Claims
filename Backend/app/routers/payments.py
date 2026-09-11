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
from app.models.payments import PaymentCreate, PaymentOut, PaymentListOut
from app.models.enums import ClaimStatus

router = APIRouter(prefix="/payments", tags=["Payments"])


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
        "Creates a payment and transitions the claim from READY_FOR_PAYMENT → PAID. "
        "PAID is a terminal state — no further transitions are possible. "
        "Returns 409 if claim is not READY_FOR_PAYMENT or already PAID."
    ),
)
def create_payment(body: PaymentCreate):
    try:
        # Validate claim exists and is READY_FOR_PAYMENT
        claim_result = supabase.table("claims").select("*").eq("id", str(body.claim_id)).single().execute()
        if not claim_result.data:
            raise HTTPException(status_code=404, detail=f"Claim {body.claim_id} not found")
        claim = claim_result.data

        if claim["status"] == ClaimStatus.PAID.value:
            raise HTTPException(
                status_code=409,
                detail="This claim has already been paid. PAID is a terminal state.",
            )
        if claim["status"] != ClaimStatus.READY_FOR_PAYMENT.value:
            raise HTTPException(
                status_code=409,
                detail=f"Only READY_FOR_PAYMENT claims can be paid. Current: {claim['status']}",
            )

        now = datetime.now(timezone.utc).isoformat()

        # Insert payment record
        payment_payload = {
            "claim_id": str(body.claim_id),
            "amount": body.amount,
            "currency": body.currency,
            "processed_by": str(body.processed_by),
            "processed_at": now,
            "notes": body.notes,
        }
        if body.payment_reference:
            payment_payload["payment_reference"] = body.payment_reference

        payment_result = supabase.table("payments").insert(payment_payload).execute()
        payment = payment_result.data[0]

        # Transition claim to PAID and store payment reference
        supabase.table("claims").update({
            "status": ClaimStatus.PAID.value,
            "payment_reference": payment.get("payment_reference") or payment["id"],
            "finance_status": "FINANCE_CLEARED",
        }).eq("id", str(body.claim_id)).execute()

        # Status history
        supabase.table("claim_status_history").insert({
            "claim_id": str(body.claim_id),
            "from_status": ClaimStatus.READY_FOR_PAYMENT.value,
            "to_status": ClaimStatus.PAID.value,
            "event_label": "Payment processed",
            "comment": body.notes,
            "actor_id": str(body.processed_by),
            "occurred_at": now,
        }).execute()

        logger.info(
            "Payment created — claim marked PAID",
            extra={
                "claim_id": str(body.claim_id),
                "payment_id": payment["id"],
                "amount": body.amount,
                "currency": body.currency,
            },
        )
        return payment
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to create payment", exc_info=exc)
        raise HTTPException(status_code=500, detail=str(exc))
