"""
app/models/documents.py
Pydantic schemas for the OCR pipeline: document upload, processing status,
extracted receipt data, confidence scores, and validation warnings.
"""
from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import DocumentType, OcrProcessingStatus


# ---------------------------------------------------------------------------
# Receipt extraction — structured output from Gemini
# ---------------------------------------------------------------------------
class ReceiptLineItem(BaseModel):
    """A single line item on a receipt."""
    description: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    amount: Decimal | None = None


class ReceiptData(BaseModel):
    """Structured receipt data — output of extraction + normalization."""
    merchant: str | None = None
    merchant_normalized: str | None = None
    invoice_number: str | None = None
    transaction_date: date | None = None
    currency: str | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    total: Decimal | None = None
    line_items: list[ReceiptLineItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Confidence & validation
# ---------------------------------------------------------------------------
class ConfidenceScores(BaseModel):
    """Per-field confidence from the extraction model (0.0 – 1.0)."""
    merchant: float | None = None
    amount: float | None = None
    date: float | None = None
    invoice: float | None = None
    overall: float | None = None


class ValidationWarning(BaseModel):
    """A single deterministic validation warning."""
    code: str
    field: str | None = None
    message: str
    severity: str = "WARNING"  # INFO | WARNING | ERROR


# ---------------------------------------------------------------------------
# OCR processing record
# ---------------------------------------------------------------------------
class OcrProcessingOut(BaseModel):
    id: UUID
    document_id: UUID
    status: OcrProcessingStatus
    provider: str
    provider_request_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Extracted data record
# ---------------------------------------------------------------------------
class ExtractedDataOut(BaseModel):
    id: UUID
    claim_id: UUID
    document_id: UUID
    ocr_processing_id: UUID | None = None

    merchant: str | None = None
    merchant_normalized: str | None = None
    invoice_number: str | None = None
    transaction_date: date | None = None
    currency: str | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    total: Decimal | None = None

    line_items: list[ReceiptLineItem] = Field(default_factory=list)
    normalized_data: dict[str, Any] = Field(default_factory=dict)
    confidence_scores: ConfidenceScores | dict = Field(default_factory=dict)
    validation_warnings: list[ValidationWarning] | list[dict] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Document upload & detail responses
# ---------------------------------------------------------------------------
class DocumentUploadResponse(BaseModel):
    """Returned immediately after uploading a receipt."""
    id: UUID
    claim_id: UUID
    file_name: str
    storage_path: str
    mime_type: str
    file_size_bytes: int
    checksum: str
    message: str = "Document uploaded successfully. Call /process to start OCR."


class DocumentDetailOut(BaseModel):
    """Full document detail including OCR processing status and extracted data."""
    id: UUID
    claim_id: UUID
    document_type: DocumentType
    file_name: str | None = None
    file_url: str | None = None
    storage_path: str | None = None
    file_size_bytes: int | None = None
    mime_type: str | None = None
    checksum: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    # Nested OCR data (populated when available)
    ocr_processing: OcrProcessingOut | None = None
    extracted_data: ExtractedDataOut | None = None

    model_config = {"from_attributes": True}


class ProcessingResponse(BaseModel):
    """Returned after triggering or querying the OCR pipeline."""
    document_id: UUID
    status: OcrProcessingStatus
    message: str
    extracted_data: ExtractedDataOut | None = None


class UnifiedPipelineResponse(BaseModel):
    """Returned by the streamlined upload + OCR + verification pipeline."""
    claim_id: UUID
    document: DocumentUploadResponse
    ocr_status: OcrProcessingStatus
    extracted_data: ExtractedDataOut | dict | None = None
    verification: dict | None = None
    message: str

