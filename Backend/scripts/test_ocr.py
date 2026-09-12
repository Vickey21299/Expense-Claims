"""
scripts/test_ocr.py
Developer CLI utility to test the OCR pipeline against a real receipt file.

Usage:
    python scripts/test_ocr.py ./bill/uber_trip_receipt.png
    python scripts/test_ocr.py ./bill/jio_fiber_bill.pdf
    python scripts/test_ocr.py ./bill/5595911088.pdf

Requires GEMINI_API_KEY to be set in .env or environment.
"""
import json
import os
import sys
from pathlib import Path

# Ensure app imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.services.extraction import GeminiReceiptExtractor
from app.services.normalization import normalize_receipt_data
from app.services.validation import validate_receipt


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_ocr.py <receipt_file>")
        print("  e.g. python scripts/test_ocr.py ./bill/uber_trip_receipt.png")
        sys.exit(1)

    filepath = Path(sys.argv[1])
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    # Determine MIME type from extension
    mime_map = {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }
    ext = filepath.suffix.lower()
    mime_type = mime_map.get(ext)
    if not mime_type:
        print(f"Error: Unsupported file type '{ext}'")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("Error: GEMINI_API_KEY is not set in .env or environment.")
        print("Get a free key at: https://aistudio.google.com/apikey")
        sys.exit(1)

    file_data = filepath.read_bytes()

    print(f"{'=' * 60}")
    print(f"OCR Pipeline Test")
    print(f"{'=' * 60}")
    print(f"File:      {filepath}")
    print(f"Size:      {len(file_data):,} bytes")
    print(f"MIME type: {mime_type}")
    print(f"{'=' * 60}")

    # Step 1: Extract
    print("\n[1/3] Extracting with Gemini...")
    try:
        extractor = GeminiReceiptExtractor(api_key=api_key)
        result = extractor.extract(file_data, mime_type)
        print(f"      ✓ Extraction successful (provider: {result.provider})")
    except Exception as e:
        print(f"      ✗ Extraction FAILED: {e}")
        sys.exit(1)

    # Step 2: Normalize
    print("[2/3] Normalizing...")
    normalized = normalize_receipt_data(result.extracted_data)
    print(f"      ✓ Normalization complete")

    # Step 3: Validate
    print("[3/3] Validating...")
    warnings = validate_receipt(normalized)
    error_count = sum(1 for w in warnings if w["severity"] == "ERROR")
    warn_count = sum(1 for w in warnings if w["severity"] == "WARNING")
    info_count = sum(1 for w in warnings if w["severity"] == "INFO")
    print(f"      ✓ Validation complete ({error_count} errors, {warn_count} warnings, {info_count} info)")

    # Print results
    print(f"\n{'=' * 60}")
    print(f"EXTRACTED DATA")
    print(f"{'=' * 60}")
    print(f"  Merchant:         {normalized.get('merchant', '—')}")
    print(f"  Merchant (norm):  {normalized.get('merchant_normalized', '—')}")
    print(f"  Invoice Number:   {normalized.get('invoice_number', '—')}")
    print(f"  Date:             {normalized.get('transaction_date', '—')}")
    print(f"  Currency:         {normalized.get('currency', '—')}")
    print(f"  Subtotal:         {normalized.get('subtotal', '—')}")
    print(f"  Tax:              {normalized.get('tax', '—')}")
    print(f"  Total:            {normalized.get('total', '—')}")

    line_items = normalized.get("line_items", [])
    if line_items:
        print(f"\n  LINE ITEMS ({len(line_items)}):")
        for i, item in enumerate(line_items, 1):
            desc = item.get("description", "—")
            qty = item.get("quantity", "—")
            price = item.get("unit_price", "—")
            amt = item.get("amount", "—")
            print(f"    {i}. {desc}  (qty: {qty}, unit: {price}, amount: {amt})")
    else:
        print(f"\n  LINE ITEMS: None extracted")

    print(f"\n{'=' * 60}")
    print(f"CONFIDENCE SCORES")
    print(f"{'=' * 60}")
    for key, val in result.confidence_scores.items():
        print(f"  {key:>12}: {val if val is not None else '—'}")

    if warnings:
        print(f"\n{'=' * 60}")
        print(f"VALIDATION WARNINGS ({len(warnings)})")
        print(f"{'=' * 60}")
        for w in warnings:
            icon = "❌" if w["severity"] == "ERROR" else ("⚠️" if w["severity"] == "WARNING" else "ℹ️")
            print(f"  {icon} [{w['severity']}] {w['code']}: {w['message']}")

    print(f"\n{'=' * 60}")
    print(f"Pipeline Status: {'COMPLETED ✓' if error_count == 0 else 'HAS ERRORS ✗'}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
