"""
app/models/claims.py
Pydantic schemas for claims and related sub-resources.
"""
from __future__ import annotations
from datetime import date, datetime
from uuid import UUID
from typing import Any

from pydantic import BaseModel, field_validator

from app.models.enums import (
    ClaimStatus,
    OcrStatus,
    VerificationStatus,
    FinanceDecision,
    DocumentType,
    VerificationSeverity,
)


# ---------------------------------------------------------------------------
# Claim
# ---------------------------------------------------------------------------
class ClaimBase(BaseModel):
    merchant: str | None = None
    claim_type: str
    amount: float = 0.0
    currency: str = "INR"
    claim_date: date | None = None
    description: str | None = None


class ClaimCreate(ClaimBase):
    employee_id: UUID
    manager_id: UUID | None = None


class ClaimUpdate(BaseModel):
    merchant: str | None = None
    claim_type: str | None = None
    amount: float | None = None
    currency: str | None = None
    claim_date: date | None = None
    description: str | None = None
    manager_id: UUID | None = None


class ClaimOut(ClaimBase):
    id: UUID
    claim_ref: str | None = None
    employee_id: UUID
    manager_id: UUID | None = None
    status: ClaimStatus
    ocr_status: OcrStatus
    verification_status: VerificationStatus
    finance_status: FinanceDecision | None = None
    payment_reference: str | None = None
    submitted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClaimListOut(BaseModel):
    total: int
    claims: list[ClaimOut]


# ---------------------------------------------------------------------------
# Claim detail — includes related data
# ---------------------------------------------------------------------------
class VerificationResultOut(BaseModel):
    id: UUID
    check_name: str
    passed: bool
    message: str | None = None
    severity: VerificationSeverity
    checked_at: datetime


class DuplicateMatchOut(BaseModel):
    id: UUID
    matched_claim_id: UUID | None = None
    similarity_score: float | None = None
    assessment: str | None = None
    signals: list[str]
    detected_by: str
    resolved: bool
    resolved_at: datetime | None = None
    resolution_note: str | None = None
    detected_at: datetime


class StatusHistoryOut(BaseModel):
    id: UUID
    from_status: ClaimStatus | None = None
    to_status: ClaimStatus
    event_label: str
    comment: str | None = None
    actor_name: str | None = None
    occurred_at: datetime


class ClaimDetailOut(ClaimOut):
    """Full claim detail including nested related records."""
    verification_results: list[VerificationResultOut] = []
    duplicate_matches: list[DuplicateMatchOut] = []
    status_history: list[StatusHistoryOut] = []


# ---------------------------------------------------------------------------
# Claim document
# ---------------------------------------------------------------------------
class ClaimDocumentOut(BaseModel):
    id: UUID
    claim_id: UUID
    document_type: DocumentType
    file_name: str | None = None
    file_url: str | None = None
    file_size_bytes: int | None = None
    mime_type: str | None = None
    ocr_raw_text: str | None = None
    ocr_confidence: float | None = None
    ocr_processed_at: datetime | None = None
    created_at: datetime


# ---------------------------------------------------------------------------
# Claim items
# ---------------------------------------------------------------------------
class ClaimItemOut(BaseModel):
    id: UUID
    claim_id: UUID
    document_id: UUID | None = None
    description: str
    quantity: float
    unit_price: float
    total_amount: float
    currency: str
    extracted_by: str
    confidence: float | None = None
    created_at: datetime


class ClaimItemCreate(BaseModel):
    description: str
    quantity: float = 1.0
    unit_price: float
    currency: str = "INR"
    extracted_by: str = "MANUAL"
    confidence: float | None = None
    document_id: UUID | None = None


# ---------------------------------------------------------------------------
# Submit action
# ---------------------------------------------------------------------------
class ClaimSubmitResponse(BaseModel):
    claim_id: UUID
    claim_ref: str | None
    status: ClaimStatus
    message: str
