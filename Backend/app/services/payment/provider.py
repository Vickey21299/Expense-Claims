"""
app/services/payment/provider.py
Abstract Payment Provider interface and concrete MockPaymentProvider.
Allows seamless plug-and-play replacement of real banking/payment gateways in the future.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import secrets
from typing import Any

from app.core.logging import get_logger
from app.models.payments import PayoutRequest, PayoutResult

logger = get_logger(__name__)


class PaymentProvider(ABC):
    """Abstract interface for payment payout providers."""

    @abstractmethod
    async def execute_payout(self, request: PayoutRequest) -> PayoutResult:
        """Execute a payout request to the recipient and return the payout result."""
        pass


class MockPaymentProvider(PaymentProvider):
    """
    Mock implementation simulating instant banking/UPI transaction settlement.
    Generates deterministic or random unique transaction references.
    """

    def __init__(self, provider_name: str = "MockPaymentGateway", channel: str = "UPI_DIRECT"):
        self.provider_name = provider_name
        self.channel = channel

    async def execute_payout(self, request: PayoutRequest) -> PayoutResult:
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y%m%d")

        # Use caller-provided reference or generate realistic transaction ID
        if request.reference_id and request.reference_id.strip():
            tx_ref = request.reference_id.strip()
        else:
            suffix = secrets.token_hex(4).upper()
            tx_ref = f"TXN-PAY-{date_str}-{suffix}"

        logger.info(
            "Mock payout executed successfully",
            extra={
                "claim_id": str(request.claim_id),
                "amount": request.amount,
                "currency": request.currency,
                "tx_ref": tx_ref,
                "provider": self.provider_name,
            },
        )

        return PayoutResult(
            success=True,
            transaction_reference=tx_ref,
            processed_at=now,
            provider_name=self.provider_name,
            channel=self.channel,
            details={
                "settlement_type": "INSTANT",
                "mode": "IMPS/UPI",
                "status": "SETTLED",
                "bank_ack": f"ACK-{secrets.token_hex(6).upper()}",
            },
        )
