"""
app/services/extraction.py
Receipt extraction via Gemini document/image understanding.

Provider abstraction:
    ReceiptExtractor (ABC)  ← interface
    GeminiReceiptExtractor  ← production implementation

Gemini-specific code is entirely encapsulated here.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Extraction result
# ---------------------------------------------------------------------------
class ExtractionResult:
    """Wraps the raw response + parsed structured data from any provider."""
    def __init__(
        self,
        raw_response: dict[str, Any],
        extracted_data: dict[str, Any],
        confidence_scores: dict[str, float | None],
        provider: str = "gemini",
    ):
        self.raw_response = raw_response
        self.extracted_data = extracted_data
        self.confidence_scores = confidence_scores
        self.provider = provider


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------
class ReceiptExtractor(ABC):
    """Provider-agnostic interface for receipt extraction."""

    @abstractmethod
    def extract(self, file_data: bytes, mime_type: str) -> ExtractionResult:
        """
        Extract structured receipt data from a file.
        Returns an ExtractionResult with raw response and parsed data.
        """
        ...


# ---------------------------------------------------------------------------
# Gemini implementation
# ---------------------------------------------------------------------------
# Structured schema for Gemini's response_schema (JSON mode)
_RECEIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "merchant": {"type": "string", "description": "Business/merchant name", "nullable": True},
        "invoice_number": {"type": "string", "description": "Invoice or receipt number exactly as printed", "nullable": True},
        "transaction_date": {"type": "string", "description": "Transaction date in YYYY-MM-DD format", "nullable": True},
        "currency": {"type": "string", "description": "3-letter currency code (INR, USD, EUR, etc.)", "nullable": True},
        "subtotal": {"type": "number", "description": "Subtotal before tax", "nullable": True},
        "tax": {"type": "number", "description": "Total tax amount", "nullable": True},
        "discount": {"type": "number", "description": "Total discount, coupon, or offer savings amount", "nullable": True},
        "total": {"type": "number", "description": "Total amount paid", "nullable": True},
        "line_items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "nullable": True},
                    "quantity": {"type": "number", "nullable": True},
                    "unit_price": {"type": "number", "nullable": True},
                    "amount": {"type": "number", "nullable": True},
                },
            },
            "description": "Individual line items on the receipt",
        },
        "merchant_confidence": {"type": "number", "description": "0.0-1.0 confidence for merchant extraction", "nullable": True},
        "amount_confidence": {"type": "number", "description": "0.0-1.0 confidence for amount extraction", "nullable": True},
        "date_confidence": {"type": "number", "description": "0.0-1.0 confidence for date extraction", "nullable": True},
        "invoice_confidence": {"type": "number", "description": "0.0-1.0 confidence for invoice number extraction", "nullable": True},
    },
    "required": ["merchant", "total", "line_items"],
}

_EXTRACTION_PROMPT = """You are a receipt/invoice data extraction system. Analyze this document and extract structured information.

RULES:
1. Extract ONLY information that is actually visible in the document.
2. NEVER invent, guess, or fabricate any values.
3. Return null for any field you cannot confidently determine.
4. Preserve invoice/receipt numbers EXACTLY as printed (do not modify or reformat them).
5. Extract line items when they are visible.
6. Identify the currency from symbols (₹=INR, $=USD, €=EUR, £=GBP) or text.
7. Extract subtotal, tax, and total as separate values when available.
8. Format dates as YYYY-MM-DD.
9. For amounts, return numeric values without currency symbols or commas.
10. Do not infer business information that is not present in the document.
11. For confidence scores, rate your extraction confidence from 0.0 (not confident) to 1.0 (very confident) for each field.

Extract the receipt/invoice data from this document."""


class GeminiReceiptExtractor(ReceiptExtractor):
    """Extracts receipt data using Google Gemini document understanding."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self._api_key = api_key or settings.GEMINI_API_KEY
        self._model = model or settings.GEMINI_MODEL

        if not self._api_key:
            raise ValueError(
                "GEMINI_API_KEY is required. Set it in .env or pass it explicitly."
            )

    def _get_client(self):
        """Lazy-init the Gemini client."""
        from google import genai
        return genai.Client(api_key=self._api_key)

    def extract(self, file_data: bytes, mime_type: str) -> ExtractionResult:
        """
        Send file to Gemini and extract structured receipt data.
        """
        import time
        from google import genai
        from google.genai import types

        client = self._get_client()

        t_start = time.time()
        logger.info(
            f"[GeminiExtractor] Sending request to Gemini Vision API "
            f"(model={self._model}, mime_type={mime_type}, size={len(file_data):,} bytes)"
        )

        try:
            # Build the content parts: file + prompt
            file_part = types.Part.from_bytes(data=file_data, mime_type=mime_type)
            text_part = types.Part.from_text(text=_EXTRACTION_PROMPT)

            response = client.models.generate_content(
                model=self._model,
                contents=[file_part, text_part],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=_RECEIPT_SCHEMA,
                ),
            )

            elapsed = time.time() - t_start
            logger.info(f"[GeminiExtractor] Response received from Gemini in {elapsed:.2f}s")

            # Parse the response
            raw_text = response.text
            raw_response = {
                "model": self._model,
                "response_text": raw_text,
                "usage_metadata": str(response.usage_metadata) if hasattr(response, "usage_metadata") else None,
            }

            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError as e:
                logger.error(f"[GeminiExtractor] Gemini returned invalid JSON: {e} | Raw text: {raw_text[:500]}")
                raise ValueError(f"Gemini returned invalid JSON: {e}")

            # Separate confidence scores from data
            confidence_scores = {
                "merchant": parsed.pop("merchant_confidence", None),
                "amount": parsed.pop("amount_confidence", None),
                "date": parsed.pop("date_confidence", None),
                "invoice": parsed.pop("invoice_confidence", None),
            }

            # Calculate overall confidence
            valid_scores = [v for v in confidence_scores.values() if v is not None]
            confidence_scores["overall"] = (
                round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else None
            )

            logger.info(
                f"[GeminiExtractor] Extracted successfully: merchant='{parsed.get('merchant')}', "
                f"total={parsed.get('total')}, currency={parsed.get('currency')}, "
                f"overall_confidence={confidence_scores.get('overall')}"
            )

            return ExtractionResult(
                raw_response=raw_response,
                extracted_data=parsed,
                confidence_scores=confidence_scores,
                provider="gemini",
            )

        except ValueError:
            raise
        except Exception as exc:
            elapsed = time.time() - t_start
            logger.error(f"[GeminiExtractor] Gemini API call failed after {elapsed:.2f}s: {exc}")
            raise RuntimeError(f"Gemini extraction failed: {exc}") from exc


def get_extractor() -> ReceiptExtractor:
    """Factory — returns the configured receipt extractor."""
    return GeminiReceiptExtractor()
