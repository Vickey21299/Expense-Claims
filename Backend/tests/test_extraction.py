"""
tests/test_extraction.py
Unit tests for the extraction service with mocked Gemini responses.
No real API calls are made.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from unittest.mock import MagicMock, patch

from app.services.extraction import GeminiReceiptExtractor, ExtractionResult


def _make_mock_response(data: dict) -> MagicMock:
    """Create a mock Gemini response object."""
    resp = MagicMock()
    resp.text = json.dumps(data)
    resp.usage_metadata = None
    return resp


class TestGeminiExtractor:
    """Tests with mocked Gemini client."""

    def _extract_with_mock(self, response_data: dict) -> ExtractionResult:
        """Helper to run extraction with a mocked Gemini response."""
        mock_response = _make_mock_response(response_data)

        with patch("app.services.extraction.GeminiReceiptExtractor._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_get_client.return_value = mock_client

            extractor = GeminiReceiptExtractor(api_key="test-key")
            result = extractor.extract(b"fake-pdf-data", "application/pdf")

        return result

    def test_valid_receipt(self):
        """Full valid receipt extraction."""
        data = {
            "merchant": "Uber",
            "invoice_number": "INV-92831",
            "transaction_date": "2026-09-08",
            "currency": "INR",
            "subtotal": 1059.32,
            "tax": 190.68,
            "total": 1250.00,
            "line_items": [
                {"description": "Base Fare", "quantity": 1, "unit_price": 120.00, "amount": 120.00},
                {"description": "Distance", "quantity": 1, "unit_price": 850.00, "amount": 850.00},
            ],
            "merchant_confidence": 0.95,
            "amount_confidence": 0.98,
            "date_confidence": 0.90,
            "invoice_confidence": 0.85,
        }

        result = self._extract_with_mock(data)

        assert result.provider == "gemini"
        assert result.extracted_data["merchant"] == "Uber"
        assert result.extracted_data["total"] == 1250.00
        assert result.extracted_data["currency"] == "INR"
        assert len(result.extracted_data["line_items"]) == 2
        assert result.confidence_scores["merchant"] == 0.95
        assert result.confidence_scores["amount"] == 0.98
        assert result.confidence_scores["overall"] is not None
        assert result.raw_response is not None

    def test_missing_optional_fields(self):
        """Receipt with minimal fields — only merchant and total."""
        data = {
            "merchant": "Local Shop",
            "invoice_number": None,
            "transaction_date": None,
            "currency": None,
            "subtotal": None,
            "tax": None,
            "total": 50.00,
            "line_items": [],
        }

        result = self._extract_with_mock(data)

        assert result.extracted_data["merchant"] == "Local Shop"
        assert result.extracted_data["total"] == 50.00
        assert result.extracted_data["invoice_number"] is None
        assert result.extracted_data["currency"] is None
        assert result.extracted_data["line_items"] == []

    def test_null_total(self):
        """Receipt where total could not be determined."""
        data = {
            "merchant": "Unknown Store",
            "total": None,
            "line_items": [],
        }

        result = self._extract_with_mock(data)
        assert result.extracted_data["total"] is None

    def test_multiple_line_items(self):
        """Receipt with many line items."""
        items = [
            {"description": f"Item {i}", "quantity": i, "unit_price": 10.0 * i, "amount": 10.0 * i * i}
            for i in range(1, 6)
        ]
        data = {
            "merchant": "Restaurant",
            "total": sum(item["amount"] for item in items),
            "line_items": items,
        }

        result = self._extract_with_mock(data)
        assert len(result.extracted_data["line_items"]) == 5

    def test_confidence_scores_extracted(self):
        """Confidence scores are properly separated from data."""
        data = {
            "merchant": "Test",
            "total": 100.00,
            "line_items": [],
            "merchant_confidence": 0.7,
            "amount_confidence": 0.9,
            "date_confidence": 0.5,
            "invoice_confidence": None,
        }

        result = self._extract_with_mock(data)

        # Confidence should be extracted and NOT in the data dict
        assert "merchant_confidence" not in result.extracted_data
        assert "amount_confidence" not in result.extracted_data
        assert result.confidence_scores["merchant"] == 0.7
        assert result.confidence_scores["amount"] == 0.9
        assert result.confidence_scores["invoice"] is None

    def test_invalid_json_raises(self):
        """Gemini returning non-JSON should raise ValueError."""
        mock_response = MagicMock()
        mock_response.text = "This is not JSON at all"
        mock_response.usage_metadata = None

        with patch("app.services.extraction.GeminiReceiptExtractor._get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_get_client.return_value = mock_client

            extractor = GeminiReceiptExtractor(api_key="test-key")
            try:
                extractor.extract(b"fake-data", "application/pdf")
                assert False, "Should have raised ValueError"
            except ValueError as e:
                assert "invalid JSON" in str(e)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
