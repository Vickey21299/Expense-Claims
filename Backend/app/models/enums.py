"""
app/models/enums.py
All shared enumerations — kept in one place so every router/model imports from here.
"""
from enum import Enum


class ClaimStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    FLAGGED = "FLAGGED"
    MANAGER_CONFIRMED = "MANAGER_CONFIRMED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    READY_FOR_PAYMENT = "READY_FOR_PAYMENT"
    PAID = "PAID"


class UserRole(str, Enum):
    STAFF = "staff"
    MANAGER = "manager"
    FINANCE = "finance"


class OcrStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    CLEAN = "CLEAN"
    FLAGGED = "FLAGGED"
    ERROR = "ERROR"


class VerificationDecision(str, Enum):
    CLEAN = "CLEAN"
    POTENTIAL_DUPLICATE = "POTENTIAL_DUPLICATE"
    BORDERLINE = "BORDERLINE"
    WAITING_FOR_EXISTING_CLAIM = "WAITING_FOR_EXISTING_CLAIM"
    ESCALATE_TO_MANAGER = "ESCALATE_TO_MANAGER"


class DocumentType(str, Enum):
    RECEIPT = "RECEIPT"
    INVOICE = "INVOICE"
    BOARDING_PASS = "BOARDING_PASS"
    OTHER = "OTHER"


class OcrProcessingStatus(str, Enum):
    """Granular statuses for the OCR pipeline (ocr_processing table)."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    NORMALIZED = "NORMALIZED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FinanceDecision(str, Enum):
    FINANCE_PENDING = "FINANCE_PENDING"
    FINANCE_CLEARED = "FINANCE_CLEARED"
    FINANCE_REJECTED = "FINANCE_REJECTED"
    FINANCE_EXCEPTION = "FINANCE_EXCEPTION"


class ManagerDecision(str, Enum):
    APPROVED = "APPROVED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class VerificationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# Valid status transitions (server-enforced state machine)
ALLOWED_TRANSITIONS: dict[ClaimStatus, list[ClaimStatus]] = {
    ClaimStatus.DRAFT: [ClaimStatus.SUBMITTED],
    ClaimStatus.SUBMITTED: [ClaimStatus.UNDER_REVIEW, ClaimStatus.FLAGGED, ClaimStatus.READY_FOR_PAYMENT, ClaimStatus.APPROVED, ClaimStatus.REJECTED],
    ClaimStatus.UNDER_REVIEW: [ClaimStatus.READY_FOR_PAYMENT, ClaimStatus.APPROVED, ClaimStatus.REJECTED, ClaimStatus.FLAGGED],
    ClaimStatus.FLAGGED: [ClaimStatus.MANAGER_CONFIRMED, ClaimStatus.REJECTED],
    ClaimStatus.MANAGER_CONFIRMED: [ClaimStatus.READY_FOR_PAYMENT, ClaimStatus.APPROVED, ClaimStatus.REJECTED],
    ClaimStatus.APPROVED: [ClaimStatus.READY_FOR_PAYMENT],
    ClaimStatus.REJECTED: [ClaimStatus.SUBMITTED],  # allow resubmit
    ClaimStatus.READY_FOR_PAYMENT: [ClaimStatus.PAID],
    ClaimStatus.PAID: [],  # terminal — no exits
}

