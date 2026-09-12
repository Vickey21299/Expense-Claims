"""
tests/test_normalization.py
Unit tests for the normalization service.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
from decimal import Decimal

from app.services.normalization import (
    normalize_merchant,
    normalize_currency,
    normalize_amount,
    normalize_date,
    normalize_text,
    normalize_receipt_data,
)


# ---------------------------------------------------------------------------
# Merchant normalization
# ---------------------------------------------------------------------------
class TestNormalizeMerchant:
    def test_uber_variants(self):
        assert normalize_merchant("UBER *TRIP") == "Uber"
        assert normalize_merchant("Uber") == "Uber"
        assert normalize_merchant("UBER INDIA") == "Uber"

    def test_swiggy(self):
        assert normalize_merchant("Swiggy") == "Swiggy"
        assert normalize_merchant("SWIGGY") == "Swiggy"

    def test_starbucks(self):
        assert normalize_merchant("STARBUCKS COFFEE") == "Starbucks"
        assert normalize_merchant("Starbucks") == "Starbucks"

    def test_aws(self):
        assert normalize_merchant("Amazon Web Services") == "AWS"
        assert normalize_merchant("AWS") == "AWS"

    def test_jio(self):
        assert normalize_merchant("Reliance Jio") == "Jio"
        assert normalize_merchant("Jio") == "Jio"

    def test_strip_ltd(self):
        result = normalize_merchant("ACME Corp Ltd")
        assert result is not None
        assert "Ltd" not in result

    def test_none_empty(self):
        assert normalize_merchant(None) is None
        assert normalize_merchant("") is None
        assert normalize_merchant("   ") is None

    def test_unknown_merchant_title_case(self):
        result = normalize_merchant("my local diner")
        assert result == "My Local Diner"


# ---------------------------------------------------------------------------
# Currency normalization
# ---------------------------------------------------------------------------
class TestNormalizeCurrency:
    def test_inr_variants(self):
        assert normalize_currency("₹") == "INR"
        assert normalize_currency("Rs.") == "INR"
        assert normalize_currency("INR") == "INR"
        assert normalize_currency("inr") == "INR"
        assert normalize_currency("Rupees") == "INR"

    def test_usd(self):
        assert normalize_currency("$") == "USD"
        assert normalize_currency("USD") == "USD"
        assert normalize_currency("usd") == "USD"

    def test_eur(self):
        assert normalize_currency("€") == "EUR"
        assert normalize_currency("EUR") == "EUR"

    def test_gbp(self):
        assert normalize_currency("£") == "GBP"

    def test_already_code(self):
        assert normalize_currency("JPY") == "JPY"
        assert normalize_currency("AED") == "AED"

    def test_none_empty(self):
        assert normalize_currency(None) is None
        assert normalize_currency("") is None


# ---------------------------------------------------------------------------
# Amount normalization
# ---------------------------------------------------------------------------
class TestNormalizeAmount:
    def test_simple_number(self):
        assert normalize_amount("1250.00") == Decimal("1250.00")

    def test_with_commas(self):
        assert normalize_amount("1,250.00") == Decimal("1250.00")

    def test_with_currency_symbol(self):
        assert normalize_amount("₹1,250") == Decimal("1250")

    def test_with_currency_text(self):
        assert normalize_amount("INR 1,250.00") == Decimal("1250.00")
        assert normalize_amount("1,250.00 INR") == Decimal("1250.00")

    def test_with_rs(self):
        assert normalize_amount("Rs. 450.00") == Decimal("450.00")

    def test_integer(self):
        assert normalize_amount(450) == Decimal("450")

    def test_float(self):
        assert normalize_amount(450.50) == Decimal("450.5")

    def test_decimal_passthrough(self):
        d = Decimal("999.99")
        assert normalize_amount(d) == d

    def test_negative(self):
        assert normalize_amount("-80.00") == Decimal("-80.00")

    def test_none_empty(self):
        assert normalize_amount(None) is None
        assert normalize_amount("") is None


# ---------------------------------------------------------------------------
# Date normalization
# ---------------------------------------------------------------------------
class TestNormalizeDate:
    def test_iso_format(self):
        assert normalize_date("2026-09-08") == date(2026, 9, 8)

    def test_month_name_format(self):
        assert normalize_date("Sep 08, 2026") == date(2026, 9, 8)
        assert normalize_date("September 8, 2026") == date(2026, 9, 8)

    def test_dd_mm_yyyy(self):
        assert normalize_date("08/09/2026") == date(2026, 9, 8)

    def test_date_passthrough(self):
        d = date(2026, 1, 15)
        assert normalize_date(d) == d

    def test_none_empty(self):
        assert normalize_date(None) is None
        assert normalize_date("") is None


# ---------------------------------------------------------------------------
# Text normalization
# ---------------------------------------------------------------------------
class TestNormalizeText:
    def test_strip_whitespace(self):
        assert normalize_text("  hello   world  ") == "hello world"

    def test_collapse_spaces(self):
        assert normalize_text("INV-\n  001") == "INV- 001"

    def test_none_empty(self):
        assert normalize_text(None) is None
        assert normalize_text("") is None


# ---------------------------------------------------------------------------
# Full receipt normalization
# ---------------------------------------------------------------------------
class TestNormalizeReceiptData:
    def test_full_receipt(self):
        raw = {
            "merchant": "UBER *TRIP",
            "currency": "₹",
            "total": "1,250.00",
            "subtotal": "1,059.32",
            "tax": "190.68",
            "transaction_date": "Sep 08, 2026",
            "invoice_number": "  INV-001  ",
            "line_items": [
                {"description": "Base Fare", "quantity": 1, "unit_price": "120.00", "amount": "120.00"},
            ],
        }

        result = normalize_receipt_data(raw)

        assert result["merchant_normalized"] == "Uber"
        assert result["currency"] == "INR"
        assert result["total"] == Decimal("1250.00")
        assert result["subtotal"] == Decimal("1059.32")
        assert result["tax"] == Decimal("190.68")
        assert result["transaction_date"] == date(2026, 9, 8)
        assert result["invoice_number"] == "INV-001"
        assert len(result["line_items"]) == 1
        assert result["line_items"][0]["amount"] == Decimal("120.00")


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
