"""
app/models/reviews.py
Pydantic schemas for manager and finance reviews.
"""
from __future__ import annotations
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import ManagerDecision, FinanceDecision


# ---------------------------------------------------------------------------
# Manager review
# ---------------------------------------------------------------------------
class ManagerReviewCreate(BaseModel):
    manager_id: UUID
    decision: ManagerDecision | None = None
    comment: str | None = None


class ManagerConfirmContext(BaseModel):
    """Payload for manager confirming business context for a FLAGGED claim."""
    manager_id: UUID
    comment: str


class ManagerReviewOut(BaseModel):
    id: UUID
    claim_id: UUID
    manager_id: UUID
    decision: str
    comment: str | None = None
    reviewed_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


from typing import Any
from app.models.claims import ClaimOut, StatusHistoryOut
from app.models.verification import CandidateMatch, LlmVerificationAnalysis


class ManagerClaimDossierOut(BaseModel):
    """Comprehensive dossier for manager reviewing a claim."""
    claim: ClaimOut
    employee: dict[str, Any] | None = None
    documents: list[dict[str, Any]] = []
    extracted_data: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    llm_analysis: LlmVerificationAnalysis | None = None
    matched_candidates: list[CandidateMatch] = []
    status_history: list[StatusHistoryOut] = []
    allowed_actions: list[str] = []



# ---------------------------------------------------------------------------
# Finance review
# ---------------------------------------------------------------------------
class FinanceReviewCreate(BaseModel):
    finance_user_id: UUID
    decision: FinanceDecision
    cleared: bool
    comment: str | None = None


class FinanceReviewOut(BaseModel):
    id: UUID
    claim_id: UUID
    finance_user_id: UUID
    decision: FinanceDecision
    cleared: bool
    comment: str | None = None
    reviewed_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class FinanceClaimDossierOut(BaseModel):
    """Full comprehensive dossier for Finance team reviewing or settling a claim."""
    claim: ClaimOut
    employee: dict[str, Any] | None = None
    documents: list[dict[str, Any]] = []
    extracted_data: dict[str, Any] | None = None
    verification: dict[str, Any] | None = None
    llm_analysis: LlmVerificationAnalysis | None = None
    manager_review: dict[str, Any] | None = None
    matched_candidates: list[CandidateMatch] = []
    payment_info: dict[str, Any] | None = None
    status_history: list[StatusHistoryOut] = []
    allowed_actions: list[str] = []


class FinanceClearAction(BaseModel):
    """Payload for Finance clearing an anomaly or approving claim for payment."""
    finance_user_id: UUID
    comment: str | None = None


class FinanceRejectAction(BaseModel):
    """Payload for Finance rejecting a claim."""
    finance_user_id: UUID
    reason: str


class FinancePayAction(BaseModel):
    """Payload for Finance initiating payment on a READY_FOR_PAYMENT claim."""
    finance_user_id: UUID
    notes: str | None = None
    payment_reference: str | None = None

