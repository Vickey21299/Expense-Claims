"""
app/services/verification/config.py
Configurable weights, thresholds, and policies for the Verification Engine.
"""
from decimal import Decimal
import os


class VerificationConfig:
    # Thresholds
    BORDERLINE_THRESHOLD: float = float(os.environ.get("VERIFICATION_BORDERLINE_THRESHOLD", "0.70"))
    STRONG_MATCH_THRESHOLD: float = float(os.environ.get("VERIFICATION_STRONG_MATCH_THRESHOLD", "0.90"))

    # Active processing wait window
    WAIT_PERIOD_DAYS: int = int(os.environ.get("VERIFICATION_WAIT_PERIOD_DAYS", "3"))

    # Field-level similarity weights (sum to 1.0)
    WEIGHT_MERCHANT: float = float(os.environ.get("VERIFICATION_WEIGHT_MERCHANT", "0.25"))
    WEIGHT_AMOUNT: float = float(os.environ.get("VERIFICATION_WEIGHT_AMOUNT", "0.30"))
    WEIGHT_DATE: float = float(os.environ.get("VERIFICATION_WEIGHT_DATE", "0.20"))
    WEIGHT_INVOICE: float = float(os.environ.get("VERIFICATION_WEIGHT_INVOICE", "0.15"))
    WEIGHT_CATEGORY: float = float(os.environ.get("VERIFICATION_WEIGHT_CATEGORY", "0.10"))

    # Date similarity window (days)
    DATE_WINDOW_MAX_DAYS: int = int(os.environ.get("VERIFICATION_DATE_WINDOW_MAX_DAYS", "30"))

    # Amount similarity tolerance (percentage)
    AMOUNT_TOLERANCE_PCT: float = float(os.environ.get("VERIFICATION_AMOUNT_TOLERANCE_PCT", "0.25"))

    # Candidate retrieval window
    RETRIEVAL_AMOUNT_PCT: float = float(os.environ.get("VERIFICATION_RETRIEVAL_AMOUNT_PCT", "0.20"))
    RETRIEVAL_DATE_WINDOW_DAYS: int = int(os.environ.get("VERIFICATION_RETRIEVAL_DATE_WINDOW_DAYS", "60"))
    MAX_CANDIDATES: int = int(os.environ.get("VERIFICATION_MAX_CANDIDATES", "50"))

    # Session 6B: LLM Verification & Manager Recommendation Layer
    LLM_ANALYSIS_ENABLED: bool = os.environ.get("VERIFICATION_LLM_ANALYSIS_ENABLED", "true").lower() in ("1", "true", "yes")
    LLM_TRIGGER_SCORE_THRESHOLD: float = float(os.environ.get("VERIFICATION_LLM_TRIGGER_SCORE_THRESHOLD", "0.60"))
    LLM_TOP_CANDIDATES_LIMIT: int = int(os.environ.get("VERIFICATION_LLM_TOP_CANDIDATES_LIMIT", "5"))


verification_config = VerificationConfig()

