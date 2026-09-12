"""
app/services/normalization.py
Deterministic normalization of extracted receipt fields.

Each function takes the raw extracted value and returns a cleaned version.
Original values are preserved separately in the extraction record.
"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Merchant normalization
# ---------------------------------------------------------------------------
# Common prefixes/suffixes to strip from merchant names
_MERCHANT_STRIP_PATTERNS = [
    r"\*+",            # "UBER *TRIP" → "UBER TRIP"
    r"\s+TRIP$",       # "UBER TRIP" → "UBER"
    r"\s+INDIA$",      # "UBER INDIA" → "UBER"
    r"\s+PVT\.?\s*LTD\.?$",
    r"\s+PRIVATE\s+LIMITED$",
    r"\s+LIMITED$",
    r"\s+LTD\.?$",
    r"\s+INC\.?$",
    r"\s+LLC\.?$",
    r"\s+CORP\.?$",
    r"\s+TECHNOLOGIES?$",
    r"\s+INFOCOMM$",
]

# Known merchant aliases → canonical name
_MERCHANT_ALIASES: dict[str, str] = {
    "uber": "Uber",
    "uber eats": "Uber Eats",
    "ola": "Ola",
    "swiggy": "Swiggy",
    "zomato": "Zomato",
    "starbucks": "Starbucks",
    "starbucks coffee": "Starbucks",
    "amazon web services": "AWS",
    "aws": "AWS",
    "google cloud": "Google Cloud",
    "microsoft azure": "Microsoft Azure",
    "reliance jio": "Jio",
    "jio": "Jio",
    "airtel": "Airtel",
    "vodafone": "Vodafone",
    "flipkart": "Flipkart",
    "amazon": "Amazon",
    "meghana foods": "Meghana Foods",
    "google": "Google",
}


def normalize_merchant(raw: str | None) -> str | None:
    """Normalize a merchant name to a consistent representation."""
    if not raw or not raw.strip():
        return None

    cleaned = raw.strip()

    # Remove common noise patterns
    for pattern in _MERCHANT_STRIP_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    # Collapse multiple spaces
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Check alias map (case-insensitive)
    lookup = cleaned.lower()
    if lookup in _MERCHANT_ALIASES:
        return _MERCHANT_ALIASES[lookup]

    # Default: title case
    return cleaned.title() if cleaned else None


# ---------------------------------------------------------------------------
# Currency normalization
# ---------------------------------------------------------------------------
_CURRENCY_MAP: dict[str, str] = {
    "₹": "INR",
    "rs": "INR",
    "rs.": "INR",
    "inr": "INR",
    "rupees": "INR",
    "rupee": "INR",
    "$": "USD",
    "usd": "USD",
    "us$": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
}


def normalize_currency(raw: str | None) -> str | None:
    """Normalize currency representation to 3-letter ISO code."""
    if not raw or not raw.strip():
        return None

    cleaned = raw.strip().lower().rstrip(".")
    if cleaned in _CURRENCY_MAP:
        return _CURRENCY_MAP[cleaned]

    # Already a 3-letter code?
    if len(cleaned) == 3 and cleaned.isalpha():
        return cleaned.upper()

    return raw.strip().upper() if raw.strip() else None


# ---------------------------------------------------------------------------
# Amount normalization
# ---------------------------------------------------------------------------
def normalize_amount(raw: str | Decimal | float | int | None) -> Decimal | None:
    """
    Normalize an amount string to Decimal.

    Handles: ₹1,250  |  INR 1,250.00  |  1,250.00 INR  |  -₹50.00
    """
    if raw is None:
        return None

    if isinstance(raw, (int, float)):
        return Decimal(str(raw))

    if isinstance(raw, Decimal):
        return raw

    text = str(raw).strip()
    if not text:
        return None

    # Remove currency symbols and words
    text = re.sub(r"[₹$€£]", "", text)
    text = re.sub(r"(?i)\b(INR|USD|EUR|GBP|Rupees?)\b|Rs\.?", "", text)

    # Handle negative in parentheses: (100.00) → -100.00
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]

    # Remove commas and whitespace
    text = text.replace(",", "").strip()

    # Remove trailing/leading non-numeric except minus and dot
    text = re.sub(r"[^\d.\-]", "", text)

    if not text or text in (".", "-", "-."):
        return None

    try:
        return Decimal(text)
    except InvalidOperation:
        logger.warning(f"Could not parse amount: {raw!r}")
        return None


# ---------------------------------------------------------------------------
# Date normalization
# ---------------------------------------------------------------------------
_DATE_FORMATS = [
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%m.%d.%Y",
    "%d %b, %Y",
]


def normalize_date(raw: str | date | None) -> date | None:
    """Normalize a date string to a date object."""
    if raw is None:
        return None

    if isinstance(raw, date):
        return raw

    text = str(raw).strip()
    if not text:
        return None

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    # Try ISO format as last resort
    try:
        return date.fromisoformat(text[:10])
    except (ValueError, IndexError):
        pass

    logger.warning(f"Could not parse date: {raw!r}")
    return None


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------
def normalize_text(raw: str | None) -> str | None:
    """Trim whitespace and collapse formatting noise."""
    if not raw:
        return None
    cleaned = re.sub(r"\s+", " ", raw).strip()
    return cleaned if cleaned else None


# ---------------------------------------------------------------------------
# Full receipt normalization
# ---------------------------------------------------------------------------
def normalize_receipt_data(data: dict) -> dict:
    """
    Apply all normalizations to a raw extraction dict.
    Returns a new dict with both original and normalized values.
    """
    normalized = dict(data)

    normalized["merchant_normalized"] = normalize_merchant(data.get("merchant"))
    normalized["currency"] = normalize_currency(data.get("currency")) or "INR"
    normalized["transaction_date"] = normalize_date(data.get("transaction_date"))
    normalized["subtotal"] = normalize_amount(data.get("subtotal"))
    normalized["tax"] = normalize_amount(data.get("tax"))
    normalized["discount"] = normalize_amount(data.get("discount"))
    normalized["total"] = normalize_amount(data.get("total"))
    normalized["invoice_number"] = normalize_text(data.get("invoice_number"))

    # Normalize line items
    line_items = data.get("line_items", [])
    normalized_items = []
    for item in line_items:
        if isinstance(item, dict):
            normalized_items.append({
                "description": normalize_text(item.get("description")),
                "quantity": normalize_amount(item.get("quantity")),
                "unit_price": normalize_amount(item.get("unit_price")),
                "amount": normalize_amount(item.get("amount")),
            })
    normalized["line_items"] = normalized_items

    return normalized
