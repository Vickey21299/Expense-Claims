"""
app/services/payment/service.py
Core PaymentService orchestrating payment execution, state-machine validation,
and database persistence using pluggable PaymentProvider.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException

from app.core.database import supabase
from app.core.logging import get_logger
from app.models.enums import ClaimStatus, FinanceDecision
from app.models.payments import PayoutRequest, PayoutResult
from app.services.payment.provider import PaymentProvider, MockPaymentProvider

logger = get_logger(__name__)


class PaymentService:
    """
    Payment orchestration service.
    Enforces terminal state guardrails, state-machine rules, and manages payout execution.
    """

    def __init__(self, provider: PaymentProvider | None = None):
        self.provider = provider or MockPaymentProvider()

    async def execute_claim_payment(
        self,
        claim_id: UUID,
        processed_by: UUID,
        notes: str | None = None,
        payment_reference: str | None = None,
    ) -> dict:
        """
        Execute payment for a claim.
        Strictly enforces that the claim is in READY_FOR_PAYMENT status and not already PAID.
        Transitions claim to PAID upon successful execution.
        """
        # 1. Fetch claim
        result = supabase.table("claims").select("*").eq("id", str(claim_id)).single().execute()
        if not result.data:
            raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
        claim = result.data

        # 2. Guardrails: State validation
        if claim["status"] == ClaimStatus.PAID.value:
            raise HTTPException(
                status_code=409,
                detail="This claim has already been paid. PAID is a terminal state.",
            )
        if claim["status"] != ClaimStatus.READY_FOR_PAYMENT.value:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Only claims in READY_FOR_PAYMENT status can be paid. "
                    f"Current status: '{claim['status']}'. Claim must be cleared by Finance first."
                ),
            )

        # 3. Construct PayoutRequest
        amount = float(claim.get("amount") or 0.0)
        currency = claim.get("currency") or "INR"
        recipient_id = UUID(claim["employee_id"])

        payout_req = PayoutRequest(
            claim_id=claim_id,
            amount=amount,
            currency=currency,
            recipient_id=recipient_id,
            reference_id=payment_reference,
            notes=notes,
        )

        # 4. Execute payout via provider
        payout_result: PayoutResult = await self.provider.execute_payout(payout_req)
        if not payout_result.success:
            logger.error(
                "Payout execution failed",
                extra={"claim_id": str(claim_id), "provider": payout_result.provider_name},
            )
            raise HTTPException(
                status_code=502,
                detail=f"Payment execution failed with provider {payout_result.provider_name}",
            )

        now_iso = payout_result.processed_at.isoformat()

        # 5. Insert payment record into database
        payment_payload = {
            "claim_id": str(claim_id),
            "amount": amount,
            "currency": currency,
            "processed_by": str(processed_by),
            "processed_at": now_iso,
            "notes": notes,
            "payment_reference": payout_result.transaction_reference,
        }

        payment_insert = supabase.table("payments").insert(payment_payload).execute()
        payment_record = payment_insert.data[0]

        # 6. Update claim status to PAID
        supabase.table("claims").update({
            "status": ClaimStatus.PAID.value,
            "payment_reference": payout_result.transaction_reference,
            "finance_status": FinanceDecision.FINANCE_CLEARED.value,
        }).eq("id", str(claim_id)).execute()

        # 7. Append status history audit
        history_comment = notes if notes else f"Payment ref: {payout_result.transaction_reference}"
        supabase.table("claim_status_history").insert({
            "claim_id": str(claim_id),
            "from_status": ClaimStatus.READY_FOR_PAYMENT.value,
            "to_status": ClaimStatus.PAID.value,
            "event_label": f"Payment executed via {payout_result.provider_name}",
            "comment": history_comment,
            "actor_id": str(processed_by),
            "occurred_at": now_iso,
        }).execute()

        logger.info(
            "Claim successfully paid",
            extra={
                "claim_id": str(claim_id),
                "payment_id": payment_record["id"],
                "payment_reference": payout_result.transaction_reference,
                "amount": amount,
            },
        )

        return payment_record


# Singleton instance
default_payment_service = PaymentService()
