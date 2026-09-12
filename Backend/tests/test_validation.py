"""
tests/test_validation.py
Unit tests for the validation service.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
from decimal import Decimal

from app.services.validation import validate_receipt


def _codes(warnings: list[dict]) -> list[str]:
    """Extract just the warning codes for easier assertion."""
    return [w["code"] for w in warnings]


# ---------------------------------------------------------------------------
# Amount validations
# ---------------------------------------------------------------------------
class TestAmountValidation:
    def test_valid_amounts(self):
        data = {"total": Decimal("100.00"), "subtotal": Decimal("90.00"),
                "tax": Decimal("10.00"), "currency": "INR",
                "transaction_date": date.today(), "merchant": "Test"}
        warnings = validate_receipt(data)
        codes = _codes(warnings)
        assert "NEGATIVE_TOTAL" not in codes
        assert "NEGATIVE_SUBTOTAL" not in codes
        assert "NEGATIVE_TAX" not in codes
        assert "TOTAL_CONSISTENT" in codes

    def test_negative_total(self):
        data = {"total": Decimal("-50.00"), "currency": "INR",
                "transaction_date": date.today(), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "NEGATIVE_TOTAL" in _codes(warnings)

    def test_negative_subtotal(self):
        data = {"total": Decimal("100.00"), "subtotal": Decimal("-10.00"),
                "currency": "INR", "transaction_date": date.today(), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "NEGATIVE_SUBTOTAL" in _codes(warnings)

    def test_negative_tax(self):
        data = {"total": Decimal("100.00"), "tax": Decimal("-5.00"),
                "currency": "INR", "transaction_date": date.today(), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "NEGATIVE_TAX" in _codes(warnings)

    def test_missing_total(self):
        data = {"currency": "INR", "transaction_date": date.today(), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "MISSING_TOTAL" in _codes(warnings)


# ---------------------------------------------------------------------------
# Total consistency
# ---------------------------------------------------------------------------
class TestTotalConsistency:
    def test_consistent_totals(self):
        data = {"total": Decimal("110.00"), "subtotal": Decimal("100.00"),
                "tax": Decimal("10.00"), "currency": "INR",
                "transaction_date": date.today(), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "TOTAL_CONSISTENT" in _codes(warnings)
        assert "TOTAL_MISMATCH" not in _codes(warnings)

    def test_inconsistent_totals(self):
        data = {"total": Decimal("200.00"), "subtotal": Decimal("100.00"),
                "tax": Decimal("10.00"), "currency": "INR",
                "transaction_date": date.today(), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "TOTAL_MISMATCH" in _codes(warnings)

    def test_small_rounding_difference_ok(self):
        # Within ₹1.00 tolerance
        data = {"total": Decimal("110.50"), "subtotal": Decimal("100.00"),
                "tax": Decimal("10.00"), "currency": "INR",
                "transaction_date": date.today(), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "TOTAL_MISMATCH" not in _codes(warnings)

    def test_consistent_totals_with_discount(self):
        # Subtotal (100) + Tax (10) - Discount (20) = Total (90)
        data = {"total": Decimal("90.00"), "subtotal": Decimal("100.00"),
                "tax": Decimal("10.00"), "discount": Decimal("-20.00"),
                "currency": "INR", "transaction_date": date.today(), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "TOTAL_CONSISTENT" in _codes(warnings)
        assert "TOTAL_MISMATCH" not in _codes(warnings)

    def test_consistent_totals_with_line_item_discount(self):
        # Subtotal (730) + Tax (35) - Coupon (80) = Total (685)
        data = {"total": Decimal("685.00"), "subtotal": Decimal("730.00"),
                "tax": Decimal("35.00"), "currency": "INR",
                "transaction_date": date.today(), "merchant": "Swiggy",
                "line_items": [
                    {"description": "Food items", "amount": Decimal("730.00")},
                    {"description": "Restaurant Coupon Discount", "amount": Decimal("-80.00")},
                ]}
        warnings = validate_receipt(data)
        assert "TOTAL_CONSISTENT" in _codes(warnings)
        assert "TOTAL_MISMATCH" not in _codes(warnings)


# ---------------------------------------------------------------------------
# Currency validation
# ---------------------------------------------------------------------------
class TestCurrencyValidation:
    def test_valid_currency(self):
        data = {"total": Decimal("100.00"), "currency": "INR",
                "transaction_date": date.today(), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "INVALID_CURRENCY_FORMAT" not in _codes(warnings)
        assert "UNKNOWN_CURRENCY" not in _codes(warnings)

    def test_invalid_format(self):
        data = {"total": Decimal("100.00"), "currency": "₹",
                "transaction_date": date.today(), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "INVALID_CURRENCY_FORMAT" in _codes(warnings)

    def test_missing_currency(self):
        data = {"total": Decimal("100.00"),
                "transaction_date": date.today(), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "MISSING_CURRENCY" in _codes(warnings)


# ---------------------------------------------------------------------------
# Date validation
# ---------------------------------------------------------------------------
class TestDateValidation:
    def test_valid_date(self):
        data = {"total": Decimal("100.00"), "currency": "INR",
                "transaction_date": date.today(), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "INVALID_DATE" not in _codes(warnings)
        assert "FUTURE_DATE" not in _codes(warnings)

    def test_future_date(self):
        data = {"total": Decimal("100.00"), "currency": "INR",
                "transaction_date": date.today() + timedelta(days=30), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "FUTURE_DATE" in _codes(warnings)

    def test_old_date(self):
        data = {"total": Decimal("100.00"), "currency": "INR",
                "transaction_date": date.today() - timedelta(days=400), "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "OLD_DATE" in _codes(warnings)

    def test_missing_date(self):
        data = {"total": Decimal("100.00"), "currency": "INR", "merchant": "Test"}
        warnings = validate_receipt(data)
        assert "MISSING_DATE" in _codes(warnings)


# ---------------------------------------------------------------------------
# Merchant validation
# ---------------------------------------------------------------------------
class TestMerchantValidation:
    def test_missing_merchant(self):
        data = {"total": Decimal("100.00"), "currency": "INR",
                "transaction_date": date.today()}
        warnings = validate_receipt(data)
        assert "MISSING_MERCHANT" in _codes(warnings)

    def test_present_merchant(self):
        data = {"total": Decimal("100.00"), "currency": "INR",
                "transaction_date": date.today(), "merchant": "Uber"}
        warnings = validate_receipt(data)
        assert "MISSING_MERCHANT" not in _codes(warnings)


# ---------------------------------------------------------------------------
# Line item validation
# ---------------------------------------------------------------------------
class TestLineItemValidation:
    def test_discount_line_item_allowed(self):
        """Discount items with negative amounts should NOT trigger NEGATIVE_LINE_ITEM."""
        data = {"total": Decimal("90.00"), "currency": "INR",
                "transaction_date": date.today(), "merchant": "Test",
                "line_items": [
                    {"description": "Item 1", "amount": Decimal("100.00")},
                    {"description": "Promo Discount", "amount": Decimal("-10.00")},
                ]}
        warnings = validate_receipt(data)
        assert "NEGATIVE_LINE_ITEM" not in _codes(warnings)

    def test_non_discount_negative_line_item_flagged(self):
        """Non-discount items with negative amounts SHOULD trigger NEGATIVE_LINE_ITEM."""
        data = {"total": Decimal("100.00"), "currency": "INR",
                "transaction_date": date.today(), "merchant": "Test",
                "line_items": [
                    {"description": "Regular Item", "amount": Decimal("-10.00")},
                ]}
        warnings = validate_receipt(data)
        assert "NEGATIVE_LINE_ITEM" in _codes(warnings)

    def test_valid_line_items(self):
        data = {"total": Decimal("100.00"), "currency": "INR",
                "transaction_date": date.today(), "merchant": "Test",
                "line_items": [
                    {"description": "Item 1", "amount": Decimal("50.00")},
                    {"description": "Item 2", "amount": Decimal("50.00")},
                ]}
        warnings = validate_receipt(data)
        assert "NEGATIVE_LINE_ITEM" not in _codes(warnings)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
