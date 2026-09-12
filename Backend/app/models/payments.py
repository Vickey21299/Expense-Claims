"""
app/models/payments.py
Pydantic schemas for payments.
"""
from __future__ import annotations
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PaymentCreate(BaseModel):
    claim_id: UUID
    payment_reference: str | None = None
    amount: float
    currency: str = "INR"
    processed_by: UUID
    notes: str | None = None


class PaymentOut(BaseModel):
    id: UUID
    claim_id: UUID
    payment_reference: str | None = None
    amount: float
    currency: str
    processed_by: UUID | None = None
    processed_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentListOut(BaseModel):
    total: int
    payments: list[PaymentOut]


from typing import Any


class PayoutRequest(BaseModel):
    claim_id: UUID
    amount: float
    currency: str = "INR"
    recipient_id: UUID
    reference_id: str | None = None
    notes: str | None = None


class PayoutResult(BaseModel):
    success: bool
    transaction_reference: str
    processed_at: datetime
    provider_name: str
    channel: str = "UPI_DIRECT"
    details: dict[str, Any] = {}

