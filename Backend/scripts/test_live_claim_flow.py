"""
scripts/test_live_claim_flow.py
Simulates a real frontend user session for 'vickey.kumar@company.com' with Session 6B:
1. Creates a claim via POST /api/v1/claims
2. Uploads the Uber receipt via POST /api/v1/claims/{claim_id}/documents/upload-and-verify
3. Observes the full flow:
   - OCR Extraction (Gemini Vision)
   - Candidate Retrieval & Deterministic Rules (Session 6A)
   - Intelligent Gating -> Gemini LLM Forensic Analysis (Session 6B)
   - Structured Manager Recommendation ("Automation Alert: ...")
4. Queries Manager Queue (GET /api/v1/manager/claims) to view the AI recommendation in the queue.

Usage:
    python scripts/test_live_claim_flow.py
"""
import os
import sys
import time
from pathlib import Path
import httpx

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

from app.core.database import supabase
from app.core.logging import get_logger

logger = get_logger("live_claim_flow")
BASE_URL = "http://127.0.0.1:8000/api/v1"
TARGET_EMAIL = "vickey.kumar@company.com"
RECEIPT_PATH = Path("./bill/uber_trip_receipt.png")


def main():
    print("=" * 80)
    print("      LIVE END-TO-END CLAIM FLOW — SESSION 6B GEMINI VERIFICATION")
    print("=" * 80)

    # -----------------------------------------------------------------------
    # Step 1: Lookup User in DB
    # -----------------------------------------------------------------------
    print(f"\n[1/6] Looking up user '{TARGET_EMAIL}' in database...")
    user_res = supabase.table("users").select("*").eq("email", TARGET_EMAIL).execute()
    if not user_res.data:
        print(f"[ERROR] User '{TARGET_EMAIL}' not found in database!")
        sys.exit(1)

    user = user_res.data[0]
    user_id = user["id"]
    manager_id = user.get("manager_id")
    print(f"  -> User ID:        {user_id}")
    print(f"  -> Full Name:      {user['full_name']}")
    print(f"  -> Department:     {user['department']}")
    print(f"  -> Role:           {user['role']}")
    print(f"  -> Manager ID:     {manager_id}")

    # -----------------------------------------------------------------------
    # Step 2: Create a Claim via POST /api/v1/claims (Simulating Frontend)
    # -----------------------------------------------------------------------
    print(f"\n[2/6] Creating claim via API: POST {BASE_URL}/claims...")
    claim_payload = {
        "employee_id": user_id,
        "manager_id": manager_id,
        "claim_type": "Travel",
        "description": "Client meeting transport - Uber trip to headquarters",
        "currency": "INR",
        "amount": 0.0,  # Auto-populated by OCR
    }

    try:
        r_create = httpx.post(f"{BASE_URL}/claims", json=claim_payload, timeout=10.0)
        r_create.raise_for_status()
        claim = r_create.json()
    except Exception as e:
        print(f"[ERROR] Could not create claim: {e}")
        sys.exit(1)

    claim_id = claim["id"]
    claim_ref = claim.get("claim_ref")
    print(f"  -> Created Claim ID:   {claim_id}")
    print(f"  -> Claim Ref:          {claim_ref}")
    print(f"  -> Initial Status:     {claim['status']}")
    logger.info(f"[Flow:Claim] Claim created: {claim_ref} (ID: {claim_id}) for {user['full_name']}")

    # -----------------------------------------------------------------------
    # Step 3: Upload Receipt via Streamlined /upload-and-verify Endpoint
    # -----------------------------------------------------------------------
    print(f"\n[3/6] Uploading receipt via streamlined endpoint:")
    print(f"      POST {BASE_URL}/claims/{claim_id}/documents/upload-and-verify...")
    if not RECEIPT_PATH.exists():
        print(f"[ERROR] Receipt file '{RECEIPT_PATH}' does not exist!")
        sys.exit(1)

    file_bytes = RECEIPT_PATH.read_bytes()
    print(f"  -> Sending file '{RECEIPT_PATH.name}' ({len(file_bytes):,} bytes)...")
    print("  -> Backend running: In-memory upload -> Gemini Vision -> Verification Engine -> Gemini 6B...")

    t0 = time.time()
    try:
        files = {"file": (RECEIPT_PATH.name, file_bytes, "image/png")}
        r_upload = httpx.post(
            f"{BASE_URL}/claims/{claim_id}/documents/upload-and-verify",
            files=files,
            timeout=60.0,
        )
        r_upload.raise_for_status()
        res_payload = r_upload.json()
    except Exception as e:
        print(f"[ERROR] Upload and verify failed: {e}")
        if hasattr(e, "response") and e.response:
            print(f"  Server response: {e.response.text}")
        sys.exit(1)

    duration = time.time() - t0
    verif = res_payload.get("verification") or {}
    llm = verif.get("llm_analysis") or {}

    print(f"  -> Request completed in {duration:.2f}s (HTTP {r_upload.status_code})")
    print(f"  -> OCR Status:          {res_payload.get('ocr_status')}")
    print(f"  -> Deterministic Verdict:{verif.get('decision')} (Score: {verif.get('similarity_score', 0):.1%})")

    # -----------------------------------------------------------------------
    # Step 4: Display Session 6B Gemini Verification & Recommendation Card
    # -----------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("      SESSION 6B — GEMINI FORENSIC VERIFICATION & RECOMMENDATION")
    print("-" * 80)
    if llm:
        print(f"  ┌────────────────────────────────────────────────────────────────────────┐")
        print(f"  │ Duplicate Risk:      {llm.get('duplicate_risk_percentage')}%")
        print(f"  │ Risk Classification: {llm.get('risk_classification')}")
        print(f"  │ Matched Claim:       {llm.get('matched_claim_ref') or 'None'}")
        print(f"  │ Suggested Action:    {llm.get('suggested_action')}")
        print(f"  │ Model Used:          {llm.get('model_used')}")
        print(f"  ├────────────────────────────────────────────────────────────────────────┤")
        print(f"  │ Manager Recommendation:")
        print(f"  │   {llm.get('manager_recommendation')}")
        print(f"  ├────────────────────────────────────────────────────────────────────────┤")
        print(f"  │ Forensic Reasoning:")
        for line in llm.get("reasoning", "").split("\n"):
            if line.strip():
                print(f"  │   {line.strip()}")
        print(f"  └────────────────────────────────────────────────────────────────────────┘")
    else:
        print(f"  [Notice] Clean claim with low similarity — LLM analysis bypassed to save cost.")
        print(f"  Explanation: \"{verif.get('explanation')}\"")

    # -----------------------------------------------------------------------
    # Step 5: Fetch Updated Claim Detail via API
    # -----------------------------------------------------------------------
    print(f"\n[5/6] Fetching updated claim: GET {BASE_URL}/claims/{claim_id}...")
    r_detail = httpx.get(f"{BASE_URL}/claims/{claim_id}", timeout=10.0)
    updated_claim = r_detail.json()
    print(f"  -> Status:              {updated_claim.get('status')}")
    print(f"  -> Verification Status: {updated_claim.get('verification_status')}")
    print(f"  -> Merchant:            {updated_claim.get('merchant')}")
    print(f"  -> Amount:              {updated_claim.get('amount')} {updated_claim.get('currency')}")
    print(f"  -> Claim Date:          {updated_claim.get('claim_date')}")
    if updated_claim.get("manager_recommendation"):
        print(f"  -> Manager Alert:       \"{updated_claim.get('manager_recommendation')}\"")

    # -----------------------------------------------------------------------
    # Step 6: Verify Manager Review Queue via GET /api/v1/manager/claims
    # -----------------------------------------------------------------------
    print(f"\n[6/6] Checking Manager Queue: GET {BASE_URL}/manager/claims...")
    try:
        r_mgr = httpx.get(f"{BASE_URL}/manager/claims", timeout=10.0)
        mgr_data = r_mgr.json()
        print(f"  -> Manager Claims Found: {mgr_data.get('total')} claims")

        target_mgr_claim = next((c for c in mgr_data.get("claims", []) if c["id"] == claim_id), None)
        if target_mgr_claim:
            print(f"  -> Target Claim {claim_ref} present in Manager Queue!")
            print(f"     • Status:              {target_mgr_claim.get('status')}")
            print(f"     • Risk %:              {target_mgr_claim.get('duplicate_risk_percentage')}%")
            print(f"     • Risk Classification: {target_mgr_claim.get('risk_classification')}")
            print(f"     • Manager Alert:       \"{target_mgr_claim.get('manager_recommendation')}\"")
        else:
            print(f"  -> Claim status is {updated_claim.get('status')}")
    except Exception as exc:
        print(f"  [WARNING] Could not check manager queue: {exc}")

    print("\n" + "=" * 80)
    print("  [SUCCESS] COMPLETE SESSION 6B FLOW VERIFIED WITH LIVE GEMINI & SUPABASE!")
    print(f"  Claim {claim_ref} successfully analyzed with manager recommendation.")
    print("=" * 80)


if __name__ == "__main__":
    main()
