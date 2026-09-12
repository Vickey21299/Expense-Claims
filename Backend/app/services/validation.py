"""
app/services/validation.py
Deterministic validation of extracted receipt data.

Runs AFTER normalization. Never silently corrects values — only records warnings.
Designed to produce signals for the future Verification Engine (Session 6).
"""
from datetime import date
from decimal import Decimal

from app.core.logging import get_logger

logger = get_logger(__name__)

# Known 3-letter ISO currency codes (common subset)
_VALID_CURRENCIES = {
    "INR", "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "SGD", "AED",
    "CHF", "CNY", "HKD", "NZD", "SEK", "KRW", "THB", "MYR", "IDR",
}


class ValidationWarning:
    """A single validation warning."""
    def __init__(self, code: str, field: str | None, message: str, severity: str = "WARNING"):
        self.code = code
        self.field = field
        self.message = message
        self.severity = severity

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "field": self.field,
            "message": self.message,
            "severity": self.severity,
        }


def validate_receipt(data: dict) -> list[dict]:
    """
    Run deterministic validations on normalized receipt data.
    Returns a list of warning dicts. Empty list = all checks passed.
    """
    warnings: list[ValidationWarning] = []

    # --- Amount validations ---
    total = data.get("total")
    subtotal = data.get("subtotal")
    tax = data.get("tax")
    discount = data.get("discount")

    if total is not None:
        if isinstance(total, Decimal) and total < 0:
            warnings.append(ValidationWarning(
                "NEGATIVE_TOTAL", "total",
                f"Total amount is negative: {total}",
                "ERROR",
            ))
    else:
        warnings.append(ValidationWarning(
            "MISSING_TOTAL", "total",
            "Total amount could not be extracted.",
            "WARNING",
        ))

    if subtotal is not None and isinstance(subtotal, Decimal) and subtotal < 0:
        warnings.append(ValidationWarning(
            "NEGATIVE_SUBTOTAL", "subtotal",
            f"Subtotal is negative: {subtotal}",
            "ERROR",
        ))

    if tax is not None and isinstance(tax, Decimal) and tax < 0:
        warnings.append(ValidationWarning(
            "NEGATIVE_TAX", "tax",
            f"Tax amount is negative: {tax}",
            "ERROR",
        ))

    # --- Total consistency check ---
    if (
        total is not None
        and subtotal is not None
        and tax is not None
        and isinstance(total, Decimal)
        and isinstance(subtotal, Decimal)
        and isinstance(tax, Decimal)
    ):
        discount_val = Decimal("0.00")
        if isinstance(discount, Decimal):
            # If discount is positive (e.g. 80.00), convert to negative deduction (-80.00)
            discount_val = discount if discount < 0 else -discount
        else:
            # Infer discount from line items if top-level discount was not provided
            _DISC_KW = {"discount", "promo", "coupon", "offer", "cashback", "rebate", "voucher", "saving", "deduction", "less", "off"}
            for item in data.get("line_items", []):
                if isinstance(item, dict):
                    amt = item.get("amount")
                    desc = (item.get("description") or "").lower()
                    is_disc = any(kw in desc for kw in _DISC_KW)
                    if isinstance(amt, Decimal) and (is_disc or amt < 0):
                        discount_val -= abs(amt)

        expected = subtotal + tax + discount_val
        diff = abs(total - expected)
        # Allow up to ₹1.00 rounding tolerance
        if diff > Decimal("1.00"):
            warnings.append(ValidationWarning(
                "TOTAL_MISMATCH", "total",
                f"Total ({total}) ≠ subtotal ({subtotal}) + tax ({tax})"
                f"{f' - discount ({abs(discount_val)})' if discount_val else ''} = {expected}. "
                f"Difference: {diff}",
                "WARNING",
            ))
        else:
            # Consistent — record as INFO for audit trail
            warnings.append(ValidationWarning(
                "TOTAL_CONSISTENT", "total",
                f"Total ({total}) matches subtotal ({subtotal}) + tax ({tax})"
                f"{f' - discount ({abs(discount_val)})' if discount_val else ''}.",
                "INFO",
            ))

    # --- Currency validation ---
    currency = data.get("currency")
    if currency:
        if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha():
            warnings.append(ValidationWarning(
                "INVALID_CURRENCY_FORMAT", "currency",
                f"Currency '{currency}' is not a valid 3-letter code.",
                "ERROR",
            ))
        elif currency.upper() not in _VALID_CURRENCIES:
            warnings.append(ValidationWarning(
                "UNKNOWN_CURRENCY", "currency",
                f"Currency '{currency}' is not in the recognized list.",
                "WARNING",
            ))
    else:
        warnings.append(ValidationWarning(
            "MISSING_CURRENCY", "currency",
            "Currency could not be determined.",
            "WARNING",
        ))

    # --- Date validation ---
    transaction_date = data.get("transaction_date")
    if transaction_date:
        if isinstance(transaction_date, date):
            # Future date check
            if transaction_date > date.today():
                warnings.append(ValidationWarning(
                    "FUTURE_DATE", "transaction_date",
                    f"Transaction date {transaction_date} is in the future.",
                    "WARNING",
                ))
            # Very old date check (> 1 year)
            days_old = (date.today() - transaction_date).days
            if days_old > 365:
                warnings.append(ValidationWarning(
                    "OLD_DATE", "transaction_date",
                    f"Transaction date {transaction_date} is over 1 year old ({days_old} days).",
                    "WARNING",
                ))
        else:
            warnings.append(ValidationWarning(
                "INVALID_DATE", "transaction_date",
                f"Transaction date '{transaction_date}' is not a valid date.",
                "ERROR",
            ))
    else:
        warnings.append(ValidationWarning(
            "MISSING_DATE", "transaction_date",
            "Transaction date could not be extracted.",
            "WARNING",
        ))

    # --- Merchant validation ---
    merchant = data.get("merchant") or data.get("merchant_normalized")
    if not merchant:
        warnings.append(ValidationWarning(
            "MISSING_MERCHANT", "merchant",
            "Merchant name could not be extracted.",
            "WARNING",
        ))

    # --- Line item validation ---
    _DISCOUNT_KEYWORDS = {
        "discount", "promo", "coupon", "offer", "cashback",
        "rebate", "voucher", "saving", "deduction", "less", "off",
    }
    line_items = data.get("line_items", [])
    for i, item in enumerate(line_items):
        if isinstance(item, dict):
            amount = item.get("amount")
            description = (item.get("description") or "").lower()
            is_discount_item = any(kw in description for kw in _DISCOUNT_KEYWORDS)

            if amount is not None and isinstance(amount, Decimal) and amount < 0 and not is_discount_item:
                warnings.append(ValidationWarning(
                    "NEGATIVE_LINE_ITEM", f"line_items[{i}].amount",
                    f"Line item {i} has negative amount ({amount}) without discount context.",
                    "WARNING",
                ))

    return [w.to_dict() for w in warnings]
