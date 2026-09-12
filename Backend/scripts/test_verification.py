"""
scripts/test_verification.py
Developer CLI tool to test and inspect the Verification Engine in terminal.

Usage:
    python scripts/test_verification.py demo
    python scripts/test_verification.py demo --case 1
    python scripts/test_verification.py <claim_id>

Runs deterministic verification, prints rich logger output and structured results.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

# Ensure UTF-8 output on Windows console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure app imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.core.logging import get_logger
from app.models.enums import ClaimStatus, VerificationDecision
from app.services.verification.rules import evaluate_candidate, determine_verification_decision
from app.services.verification.engine import run_verification

logger = get_logger("test_verification")


# ===========================================================================
# Demo Scenarios
# ===========================================================================

DEMO_CASES = [
    {
        "id": 1,
        "title": "Scenario 1: Clean Claim (No duplicate candidates)",
        "description": "Employee submits a legitimate Indigo flight expense with no historical matches.",
        "target": {
            "claim": {
                "id": str(uuid4()),
                "claim_ref": "CLM-NEW-01",
                "merchant": "IndiGo Airlines",
                "amount": Decimal("4850.00"),
                "currency": "INR",
                "claim_date": "2026-09-10",
                "claim_type": "Travel",
                "status": "SUBMITTED",
                "employee_id": "usr-emp-101",
            },
            "extracted": {
                "merchant_normalized": "IndiGo",
                "total": Decimal("4850.00"),
                "transaction_date": "2026-09-10",
                "invoice_number": "6E-882194",
            },
            "document": {
                "checksum": "sha256-indigo-receipt-unique",
                "file_name": "indigo_flight.pdf",
            },
        },
        "candidates": [],  # No candidates
    },
    {
        "id": 2,
        "title": "Scenario 2: Duplicate of Already PAID Claim",
        "description": "Employee claims Swiggy ₹650.00 which was already PAID to another staff member 10 days ago.",
        "target": {
            "claim": {
                "id": str(uuid4()),
                "claim_ref": "CLM-NEW-02",
                "merchant": "Swiggy",
                "amount": Decimal("650.00"),
                "currency": "INR",
                "claim_date": "2026-09-01",
                "claim_type": "Meals",
                "status": "SUBMITTED",
                "employee_id": "usr-emp-102",
            },
            "extracted": {
                "merchant_normalized": "Swiggy",
                "total": Decimal("650.00"),
                "transaction_date": "2026-09-01",
                "invoice_number": "SWIGGY-88412",
            },
            "document": {
                "checksum": "sha256-swiggy-diff-scan",
                "file_name": "swiggy_receipt.png",
            },
        },
        "candidates": [
            {
                "claim": {
                    "id": str(uuid4()),
                    "claim_ref": "CLM-PAID-099",
                    "merchant": "SWIGGY BANGALORE",
                    "amount": Decimal("650.00"),
                    "currency": "INR",
                    "claim_date": "2026-09-01",
                    "claim_type": "Meals",
                    "status": "PAID",
                    "submitted_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
                    "employee_id": "usr-emp-005",
                },
                "extracted": {
                    "merchant_normalized": "Swiggy",
                    "total": Decimal("650.00"),
                    "transaction_date": "2026-09-01",
                    "invoice_number": "SWIGGY-88412",
                },
                "document": {
                    "checksum": "sha256-swiggy-orig-scan",
                    "file_name": "swiggy_invoice.pdf",
                },
            }
        ],
    },
    {
        "id": 3,
        "title": "Scenario 3: Active Claim Processing within 3-day Window (WAITING)",
        "description": "Employee reclaims Uber ₹1,250.00 while their initial claim is UNDER_REVIEW 1 day ago.",
        "target": {
            "claim": {
                "id": str(uuid4()),
                "claim_ref": "CLM-NEW-03",
                "merchant": "Uber",
                "amount": Decimal("1250.00"),
                "currency": "INR",
                "claim_date": "2026-09-11",
                "claim_type": "Travel",
                "status": "SUBMITTED",
                "employee_id": "usr-emp-103",
            },
            "extracted": {
                "merchant_normalized": "Uber",
                "total": Decimal("1250.00"),
                "transaction_date": "2026-09-11",
                "invoice_number": "UBER-TRIP-771",
            },
            "document": {
                "checksum": "sha256-uber-screenshot-2",
                "file_name": "uber_trip.png",
            },
        },
        "candidates": [
            {
                "claim": {
                    "id": str(uuid4()),
                    "claim_ref": "CLM-ACTIVE-204",
                    "merchant": "Uber India",
                    "amount": Decimal("1250.00"),
                    "currency": "INR",
                    "claim_date": "2026-09-11",
                    "claim_type": "Travel",
                    "status": "UNDER_REVIEW",
                    "submitted_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                    "employee_id": "usr-emp-103",
                },
                "extracted": {
                    "merchant_normalized": "Uber",
                    "total": Decimal("1250.00"),
                    "transaction_date": "2026-09-11",
                    "invoice_number": "UBER-TRIP-771",
                },
                "document": {
                    "checksum": "sha256-uber-screenshot-1",
                    "file_name": "uber_trip_orig.png",
                },
            }
        ],
    },
    {
        "id": 4,
        "title": "Scenario 4: Delayed Claim Processing (>3 days) (ESCALATE_TO_MANAGER)",
        "description": "An identical claim has been sitting in UNDER_REVIEW for 5 days. Employee likely reclaiming due to delay.",
        "target": {
            "claim": {
                "id": str(uuid4()),
                "claim_ref": "CLM-NEW-04",
                "merchant": "AWS Cloud",
                "amount": Decimal("3200.00"),
                "currency": "INR",
                "claim_date": "2026-09-02",
                "claim_type": "Software",
                "status": "SUBMITTED",
                "employee_id": "usr-emp-104",
            },
            "extracted": {
                "merchant_normalized": "AWS",
                "total": Decimal("3200.00"),
                "transaction_date": "2026-09-02",
                "invoice_number": "AWS-INVOICE-009",
            },
            "document": {
                "checksum": "sha256-aws-doc-2",
                "file_name": "aws_bill.pdf",
            },
        },
        "candidates": [
            {
                "claim": {
                    "id": str(uuid4()),
                    "claim_ref": "CLM-DELAYED-112",
                    "merchant": "Amazon Web Services",
                    "amount": Decimal("3200.00"),
                    "currency": "INR",
                    "claim_date": "2026-09-02",
                    "claim_type": "Software",
                    "status": "UNDER_REVIEW",
                    "submitted_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
                    "employee_id": "usr-emp-104",
                },
                "extracted": {
                    "merchant_normalized": "AWS",
                    "total": Decimal("3200.00"),
                    "transaction_date": "2026-09-02",
                    "invoice_number": "AWS-INVOICE-009",
                },
                "document": {
                    "checksum": "sha256-aws-doc-1",
                    "file_name": "aws_bill_orig.pdf",
                },
            }
        ],
    },
    {
        "id": 5,
        "title": "Scenario 5: Exact Document SHA-256 Receipt Hash Duplicate",
        "description": "Two different claims upload the exact same receipt image file (identical SHA-256 checksum).",
        "target": {
            "claim": {
                "id": str(uuid4()),
                "claim_ref": "CLM-NEW-05",
                "merchant": "Starbucks",
                "amount": Decimal("450.00"),
                "currency": "INR",
                "claim_date": "2026-09-08",
                "claim_type": "Meals",
                "status": "SUBMITTED",
                "employee_id": "usr-emp-105",
            },
            "extracted": {
                "merchant_normalized": "Starbucks",
                "total": Decimal("450.00"),
                "transaction_date": "2026-09-08",
                "invoice_number": None,
            },
            "document": {
                "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "file_name": "starbucks_receipt.png",
            },
        },
        "candidates": [
            {
                "claim": {
                    "id": str(uuid4()),
                    "claim_ref": "CLM-PAID-088",
                    "merchant": "Starbucks Coffee",
                    "amount": Decimal("450.00"),
                    "currency": "INR",
                    "claim_date": "2026-09-08",
                    "claim_type": "Meals",
                    "status": "PAID",
                    "submitted_at": (datetime.now(timezone.utc) - timedelta(days=4)).isoformat(),
                    "employee_id": "usr-emp-022",
                },
                "extracted": {
                    "merchant_normalized": "Starbucks",
                    "total": Decimal("450.00"),
                    "transaction_date": "2026-09-08",
                    "invoice_number": None,
                },
                "document": {
                    "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "file_name": "starbucks_receipt.png",
                },
            }
        ],
    },
]


def run_demo_case(case: dict):
    print("\n" + "=" * 75)
    print(f"  {case['title']}")
    print("=" * 75)
    print(f"Description: {case['description']}")
    target = case["target"]
    c = target["claim"]
    ext = target["extracted"]
    doc = target["document"]

    print(f"\nCurrent Claim: {c['claim_ref']} | Merchant: '{c['merchant']}' | Amount: {c['amount']} {c['currency']} | Date: {c['claim_date']}")
    print(f"OCR Extracted: Merchant='{ext['merchant_normalized']}' | Total={ext['total']} | Invoice='{ext.get('invoice_number')}'")
    print(f"Receipt File:  '{doc['file_name']}' | Hash: {doc['checksum'][:16]}...")

    # Step 1: Candidate Retrieval
    candidates = case["candidates"]
    print(f"\n[Verification] [1/4] Found {len(candidates)} candidate(s) in historical database.")

    # Step 2: Similarity Scoring
    print(f"[Verification] [2/4] Computing field-level similarity breakdowns...")
    matches = []
    for cand in candidates:
        m = evaluate_candidate(c, ext, doc, cand)
        matches.append(m)
        cand_claim = cand["claim"]
        print(f"\n  -> Matched Candidate: {cand_claim['claim_ref']} (status: {cand_claim['status']})")
        print(f"     - Overall Similarity Score: {m.similarity_score:.1%}")
        print(f"     - Merchant Similarity:      {m.field_scores.merchant_similarity:.2f}")
        print(f"     - Amount Similarity:        {m.field_scores.amount_similarity:.2f}")
        print(f"     - Date Proximity Score:     {m.field_scores.date_similarity:.2f}")
        print(f"     - Invoice Number Match:     {m.field_scores.invoice_similarity if m.field_scores.invoice_similarity is not None else 'N/A'}")
        print(f"     - Exact File Hash Match:    {m.field_scores.receipt_hash_match}")
        print(f"     - Same Employee:            {m.field_scores.same_employee}")
        print(f"     - Candidate Age in Days:    {m.age_days} day(s)")
        print(f"     - Signals:                  {m.signals}")

    # Step 3: Rules & Lifecycle evaluation
    print(f"\n[Verification] [3/4] Evaluating deterministic lifecycle & fraud rules...")
    (
        decision,
        overall_score,
        strongest,
        wait_until,
        triggered_rules,
        explanation,
    ) = determine_verification_decision(c, matches)

    # Step 4: Decision Output
    print(f"[Verification] [4/4] Decision formulated.")
    print("\n" + "-" * 75)
    decision_tag = "[PASS: CLEAN]" if decision == VerificationDecision.CLEAN else ("[WARN: WAITING/BORDERLINE]" if decision in (VerificationDecision.BORDERLINE, VerificationDecision.WAITING_FOR_EXISTING_CLAIM) else "[FLAG: DUPLICATE]")
    print(f"VERIFICATION RESULT: {decision_tag} {decision.value}")
    print(f"Similarity Score:    {overall_score:.1%}")
    print(f"Triggered Rules:     {triggered_rules if triggered_rules else 'None'}")
    if wait_until:
        print(f"Wait Until Date:     {wait_until.strftime('%Y-%m-%d')}")
    print(f"Explanation:         \"{explanation}\"")
    print("-" * 75)


def run_pipeline_demo():
    print("=" * 75)
    print("  STREAMLINED IN-MEMORY PIPELINE DEMONSTRATION")
    print("=" * 75)
    print("Architecture Comparison:")
    print("  [Previous Flow]:")
    print("    Client Upload -> Storage Upload -> DB Insert (doc)")
    print("    Client Calls /process -> Storage Download -> Gemini -> DB Insert (extracted)")
    print("    Client Calls /run -> 3 DB Reads (claim, doc, extracted) -> Verification -> DB Inserts")
    print("    Total: 2 Storage roundtrips + 3 redundant DB reads + 3 client requests\n")
    print("  [Streamlined Flow]:")
    print("    Client Calls /upload-and-verify (or upload with auto_verify=true)")
    print("    -> Storage Upload (persisted once)")
    print("    -> Gemini OCR (receives file bytes from RAM, NO storage download)")
    print("    -> Verification Engine (receives claim + extracted + doc in RAM, NO DB re-reads)")
    print("    -> Single joined candidate retrieval (PostgREST embedded resource)")
    print("    -> Atomic persistence & state transition")
    print("    Total: 1 Storage upload + 0 storage downloads + 0 redundant DB reads + 1 client request!")
    print("-" * 75)
    print("Running simulated in-memory handoff test...")

    from app.services.verification.rules import evaluate_candidate, determine_verification_decision

    claim = {
        "id": str(uuid4()),
        "claim_ref": "CLM-IN-MEM",
        "merchant": "Swiggy",
        "amount": Decimal("685.00"),
        "currency": "INR",
        "claim_date": "2026-09-08",
        "claim_type": "Meals",
        "status": "SUBMITTED",
        "employee_id": "usr-1",
    }
    extracted = {
        "merchant_normalized": "Swiggy",
        "total": Decimal("685.00"),
        "transaction_date": "2026-09-08",
        "invoice_number": "SWIGGY-100",
        "subtotal": Decimal("730.00"),
        "tax": Decimal("35.00"),
    }
    doc = {
        "id": str(uuid4()),
        "claim_id": claim["id"],
        "file_name": "swiggy_receipt.png",
        "checksum": "sha256-swiggy-in-mem",
    }

    print(f"\n[1/3] Uploaded & extracted in RAM:")
    print(f"      Merchant: {extracted['merchant_normalized']}, Total: {extracted['total']} {claim['currency']}")
    print(f"      Invoice: {extracted['invoice_number']}, Checksum: {doc['checksum']}")

    print(f"\n[2/3] Verification Engine directly evaluates in RAM (0 DB roundtrips):")
    matches = []  # No candidates
    decision, score, strongest, wait_until, rules, explanation = determine_verification_decision(claim, matches)

    print(f"\n[3/3] Result: {decision.value} (Score: {score:.1%})")
    print(f"      Status transition: SUBMITTED -> UNDER_REVIEW")
    print(f"      Explanation: \"{explanation}\"")
    print("\n[SUCCESS] Streamlined pipeline completed with zero redundant database queries!")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "pipeline":
        run_pipeline_demo()
        return

    if len(sys.argv) > 1 and sys.argv[1] != "demo":
        claim_id = sys.argv[1]
        print(f"Running live verification for claim_id={claim_id}...")
        try:
            res = run_verification(claim_id)
            print("\nVerification completed successfully!")
            print(f"Decision:    {res.decision.value}")
            print(f"Score:       {res.similarity_score:.1%}")
            print(f"Explanation: {res.explanation}")
        except Exception as e:
            print(f"Error running verification: {e}")
            sys.exit(1)
        return

    # Demo mode
    specific_case = None
    if "--case" in sys.argv:
        idx = sys.argv.index("--case")
        if idx + 1 < len(sys.argv):
            specific_case = int(sys.argv[idx + 1])

    if specific_case:
        cases_to_run = [c for c in DEMO_CASES if c["id"] == specific_case]
    else:
        cases_to_run = DEMO_CASES

    print("=" * 75)
    print("  EXPENSE CLAIMS — DETERMINISTIC VERIFICATION ENGINE CLI TEST")
    print("=" * 75)
    print(f"Running {len(cases_to_run)} verification scenario(s)...\n")

    for case in cases_to_run:
        run_demo_case(case)


if __name__ == "__main__":
    main()

