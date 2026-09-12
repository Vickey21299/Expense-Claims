"""
app/models/verification.py
Pydantic schemas for the Verification Engine.
"""
from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.enums import VerificationDecision, ClaimStatus


class FieldSimilarityScores(BaseModel):
    """Explainable similarity metrics across individual fields."""
    merchant_similarity: float = Field(..., ge=0.0, le=1.0)
    amount_similarity: float = Field(..., ge=0.0, le=1.0)
    date_similarity: float = Field(..., ge=0.0, le=1.0)
    invoice_similarity: float | None = Field(None, ge=0.0, le=1.0)
    category_similarity: float = Field(..., ge=0.0, le=1.0)
    receipt_hash_match: bool = False
    same_employee: bool = False


class CandidateMatch(BaseModel):
    """A matched historical claim candidate with similarity breakdown."""
    matched_claim_id: UUID
    claim_ref: str | None = None
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    status: ClaimStatus | str
    created_at: datetime | None = None
    submitted_at: datetime | None = None
    age_days: int = 0
    field_scores: FieldSimilarityScores
    signals: list[str] = []
    target_values: dict[str, Any] = Field(default_factory=dict)
    matched_values: dict[str, Any] = Field(default_factory=dict)



class LlmVerificationAnalysis(BaseModel):
    """Structured forensic assessment and manager guidance produced by Gemini LLM."""
    duplicate_risk_percentage: int = Field(..., ge=0, le=100)
    risk_classification: str = Field(..., description="LOW RISK | MEDIUM RISK | HIGH RISK | CRITICAL RISK")
    matched_claim_ref: str | None = None
    reasoning: str = Field(..., description="Detailed forensic explanation of matching attributes and discrepancies")
    manager_recommendation: str = Field(..., description="Direct plain-English recommendation for the manager")
    suggested_action: str = Field("VERIFY_REIMBURSEMENT", description="APPROVE | REJECT | REQUEST_CLARIFICATION | VERIFY_REIMBURSEMENT")
    analyzed_at: datetime | None = None
    model_used: str | None = None


class VerificationRunOut(BaseModel):
    """Response payload for a completed verification run."""
    id: UUID | None = None
    claim_id: UUID
    decision: VerificationDecision
    similarity_score: float
    strongest_match_claim_id: UUID | None = None
    strongest_match: CandidateMatch | None = None
    matched_claim_status: str | None = None
    matched_claim_age_days: int | None = None
    wait_until: datetime | None = None
    field_scores: FieldSimilarityScores | None = None
    triggered_rules: list[str] = []
    explanation: str
    candidates: list[CandidateMatch] = []
    llm_analysis: LlmVerificationAnalysis | None = None
    engine_version: str = "1.0.0-deterministic"
    verified_at: datetime

