"""
app/services/verification/similarity.py
Field-level deterministic similarity scoring for expense claims.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import difflib
import re
from typing import Any

from app.services.normalization import normalize_merchant, normalize_text
from app.services.verification.config import verification_config


def _to_date(val: Any) -> date | None:
    """Convert various date representations to datetime.date."""
    if val is None:
        return None
    if isinstance(val, date):
        if isinstance(val, datetime):
            return val.date()
        return val
    if isinstance(val, str):
        try:
            return date.fromisoformat(val[:10])
        except (ValueError, TypeError):
            pass
    return None


def _to_decimal(val: Any) -> Decimal | None:
    """Convert amount representation to Decimal."""
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


def calculate_merchant_similarity(m1: str | None, m2: str | None) -> float:
    """
    Calculate similarity between two merchant names (0.0 to 1.0).
    Applies normalization first, then exact and sequence matching.
    """
    if not m1 or not m2:
        return 0.0

    # 1. Normalize canonical merchant names (e.g. "UBER INDIA" -> "Uber", "Swiggy Ltd" -> "Swiggy")
    norm1 = (normalize_merchant(m1) or m1).strip().lower()
    norm2 = (normalize_merchant(m2) or m2).strip().lower()

    if norm1 == norm2:
        return 1.0

    # 2. Check if one contains the other (e.g. "starbucks coffee" and "starbucks")
    if norm1 in norm2 or norm2 in norm1:
        shorter = min(len(norm1), len(norm2))
        longer = max(len(norm1), len(norm2))
        return round(max(0.85, shorter / longer), 4)

    # 3. Fuzzy character sequence match
    ratio = difflib.SequenceMatcher(None, norm1, norm2).ratio()
    return round(ratio, 4)


def calculate_amount_similarity(a1: Any, a2: Any) -> float:
    """
    Calculate similarity between two amounts (0.0 to 1.0).
    Exact match = 1.0. Linear decay up to AMOUNT_TOLERANCE_PCT (default 25%).
    """
    dec1 = _to_decimal(a1)
    dec2 = _to_decimal(a2)

    if dec1 is None or dec2 is None:
        return 0.0

    if dec1 == dec2:
        return 1.0

    max_amt = max(abs(dec1), abs(dec2))
    if max_amt == Decimal("0.00"):
        return 1.0 if dec1 == dec2 else 0.0

    diff = abs(dec1 - dec2)
    rel_diff = float(diff / max_amt)

    tol = verification_config.AMOUNT_TOLERANCE_PCT
    if rel_diff >= tol:
        return 0.0

    score = 1.0 - (rel_diff / tol)
    return round(max(0.0, min(1.0, score)), 4)


def calculate_date_similarity(d1: Any, d2: Any) -> float:
    """
    Calculate date proximity similarity (0.0 to 1.0).
    Same day = 1.0.
    1 day diff = 0.95.
    Linear decay to 0.0 at DATE_WINDOW_MAX_DAYS (default 30 days).
    """
    date1 = _to_date(d1)
    date2 = _to_date(d2)

    if date1 is None or date2 is None:
        return 0.0

    diff_days = abs((date1 - date2).days)
    if diff_days == 0:
        return 1.0
    if diff_days == 1:
        return 0.95

    max_days = float(verification_config.DATE_WINDOW_MAX_DAYS)
    if diff_days >= max_days:
        return 0.0

    score = 1.0 - (diff_days / max_days)
    return round(max(0.0, score), 4)


def _clean_invoice(inv: str | None) -> str | None:
    """Clean invoice number for matching (strip non-alphanumeric)."""
    if not inv:
        return None
    cleaned = re.sub(r"[^A-Za-z0-9]", "", str(inv)).upper()
    return cleaned if cleaned else None


def calculate_invoice_similarity(inv1: str | None, inv2: str | None) -> float | None:
    """
    Calculate similarity between invoice numbers (0.0 to 1.0).
    Returns None if either invoice is missing or blank.
    """
    c1 = _clean_invoice(inv1)
    c2 = _clean_invoice(inv2)

    if not c1 or not c2:
        return None

    if c1 == c2:
        return 1.0

    ratio = difflib.SequenceMatcher(None, c1, c2).ratio()
    return round(ratio, 4)


def calculate_category_similarity(cat1: str | None, cat2: str | None) -> float:
    """Category / claim_type match (1.0 if match, 0.0 otherwise)."""
    if not cat1 or not cat2:
        return 0.0

    clean1 = cat1.strip().lower()
    clean2 = cat2.strip().lower()

    if clean1 == clean2:
        return 1.0
    if clean1 in clean2 or clean2 in clean1:
        return 0.7
    return 0.0


def calculate_weighted_overall_score(
    merchant_sim: float,
    amount_sim: float,
    date_sim: float,
    invoice_sim: float | None,
    category_sim: float,
) -> float:
    """
    Calculate configurable weighted overall similarity score.
    If invoice_sim is None, dynamically reallocates invoice weight proportionally.
    """
    w_m = verification_config.WEIGHT_MERCHANT
    w_a = verification_config.WEIGHT_AMOUNT
    w_d = verification_config.WEIGHT_DATE
    w_i = verification_config.WEIGHT_INVOICE
    w_c = verification_config.WEIGHT_CATEGORY

    if invoice_sim is None:
        # Reallocate invoice weight proportionally across remaining components
        active_sum = w_m + w_a + w_d + w_c
        if active_sum > 0:
            w_m = w_m / active_sum
            w_a = w_a / active_sum
            w_d = w_d / active_sum
            w_c = w_c / active_sum
            score = (w_m * merchant_sim) + (w_a * amount_sim) + (w_d * date_sim) + (w_c * category_sim)
            return round(min(1.0, max(0.0, score)), 4)

    score = (
        (w_m * merchant_sim)
        + (w_a * amount_sim)
        + (w_d * date_sim)
        + (w_i * invoice_sim)
        + (w_c * category_sim)
    )
    return round(min(1.0, max(0.0, score)), 4)
