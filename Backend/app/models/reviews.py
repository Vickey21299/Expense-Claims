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
    decision: ManagerDecision
    comment: str | None = None


class ManagerReviewOut(BaseModel):
    id: UUID
    claim_id: UUID
    manager_id: UUID
    decision: str
    comment: str | None = None
    reviewed_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


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
