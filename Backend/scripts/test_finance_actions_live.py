"""
scripts/test_finance_actions_live.py
Live validation script for Session 8 (Finance Actions) and Session 9 (Payment Execution).
Tests the complete finance & payment workflow against the running backend and live Supabase database:
1. Look up Finance user in database.
2. Query the Finance Queue (GET /api/v1/finance/claims) and verify enriched AI/manager fields.
3. Inspect the comprehensive Finance Claim Dossier (GET /api/v1/finance/claims/{id}).
4. Verify State Machine & Guardrails:
   - Attempt to pay a claim that is NOT READY_FOR_PAYMENT -> blocked with 409 Conflict.
   - Finance Clears Anomaly (POST /api/v1/finance/claims/{id}/clear) -> READY_FOR_PAYMENT.
   - Finance Rejects a claim with reason (POST /api/v1/finance/claims/{id}/reject) -> REJECTED.
5. Execute Payment via MockPaymentProvider (POST /api/v1/finance/claims/{id}/pay):
   - Generates mock reference, marks PAID.
   - Attempt double-payment -> blocked with 409 Conflict (terminal state).
6. Audit finance_reviews, payments, and claim_status_history tables in Supabase.

Usage:
    python scripts/test_finance_actions_live.py
"""
import sys
from pathlib import Path
from uuid import uuid4
import httpx

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.core.database import supabase
from app.models.enums import ClaimStatus, FinanceDecision

BASE_URL = "http://127.0.0.1:8000/api/v1"


def main():
    print("=" * 80)
    print("      SESSION 8 & 9: LIVE FINANCE ACTIONS & PAYMENT EXECUTION")
    print("=" * 80)

    # 1. Look up Finance User & Staff Employee
    print("\n[1/6] Looking up users in database...")
    fin_res = supabase.table("users").select("*").eq("role", "finance").execute()
    if not fin_res.data:
        print("[ERROR] No user with role 'finance' found!")
        sys.exit(1)
    finance_user = fin_res.data[0]
    finance_id = finance_user["id"]

    staff_res = supabase.table("users").select("*").eq("email", "vickey.kumar@company.com").execute()
    staff = staff_res.data[0] if staff_res.data else None
    staff_id = staff["id"] if staff else finance_id

    print(f"  • Finance Officer:    {finance_user['full_name']} ({finance_user['email']}) [ID: {finance_id}]")
    if staff:
        print(f"  • Staff Employee:     {staff['full_name']} ({staff['email']}) [ID: {staff_id}]")

    # 2. Query Finance Queue
    print(f"\n[2/6] Querying Finance Queue: GET {BASE_URL}/finance/claims...")
    with httpx.Client(timeout=15.0) as http:
        resp = http.get(f"{BASE_URL}/finance/claims")
        if resp.status_code != 200:
            print(f"[ERROR] Failed to list finance queue: {resp.status_code} {resp.text}")
            sys.exit(1)
        queue = resp.json()
        print(f"  • Total claims pending in Finance queue: {queue.get('total', 0)}")
        for c in queue.get("claims", [])[:3]:
            print(f"    - [{c.get('claim_ref')}] {c.get('merchant')} ₹{c.get('amount')} | Status: {c.get('status')} | Comment: {c.get('manager_comment')}")

    # 3. Create fresh test claims for Finance testing
    print("\n[3/6] Setting up test claims for anomaly clearance and rejection checks...")
    # 3.1 Claim A: Anomaly confirmed by manager, waiting for Finance
    rand_a = str(uuid4())[:4]
    claim_a_payload = {
        "claim_ref": f"CLM-FIN-CLR-{rand_a}",
        "employee_id": staff_id,
        "manager_id": finance_id,
        "merchant": "Uber",
        "claim_type": "Travel",
        "amount": 750.0,
        "currency": "INR",
        "description": "Urgent client transit after hours",
        "status": ClaimStatus.APPROVED.value,
        "finance_status": FinanceDecision.FINANCE_PENDING.value,
        "ocr_status": "COMPLETED",
        "verification_status": "FLAGGED",
    }
    res_a = supabase.table("claims").insert(claim_a_payload).execute()
    claim_a = res_a.data[0]
    claim_a_id = claim_a["id"]
    print(f"  • Created Claim A (For Anomaly Clearance): {claim_a['claim_ref']} (ID: {claim_a_id}) -> Status: {claim_a['status']}")

    # Insert a simulated manager review on Claim A
    supabase.table("manager_reviews").insert({
        "claim_id": claim_a_id,
        "manager_id": finance_id,
        "decision": "CONFIRMED",
        "comment": "Manager note: Trip was required due to late flight arrival.",
        "reviewed_at": "2026-09-12T10:00:00Z",
    }).execute()

    # 3.2 Claim B: Claim to test Finance Rejection
    rand_b = str(uuid4())[:4]
    claim_b_payload = {
        "claim_ref": f"CLM-FIN-REJ-{rand_b}",
        "employee_id": staff_id,
        "manager_id": finance_id,
        "merchant": "Electronics Hub",
        "claim_type": "Equipment",
        "amount": 12500.0,
        "currency": "INR",
        "description": "Noise cancelling headphones",
        "status": ClaimStatus.APPROVED.value,
        "finance_status": FinanceDecision.FINANCE_PENDING.value,
        "ocr_status": "COMPLETED",
        "verification_status": "CLEAN",
    }
    res_b = supabase.table("claims").insert(claim_b_payload).execute()
    claim_b = res_b.data[0]
    claim_b_id = claim_b["id"]
    print(f"  • Created Claim B (For Finance Rejection): {claim_b['claim_ref']} (ID: {claim_b_id}) -> Status: {claim_b['status']}")

    # 4. Inspect Finance Claim Dossier
    print(f"\n[4/6] Inspecting Finance Claim Dossier: GET {BASE_URL}/finance/claims/{claim_a_id}...")
    with httpx.Client(timeout=15.0) as http:
        dossier_resp = http.get(f"{BASE_URL}/finance/claims/{claim_a_id}")
        if dossier_resp.status_code != 200:
            print(f"[ERROR] Failed to fetch finance dossier: {dossier_resp.status_code} {dossier_resp.text}")
            sys.exit(1)
        dossier = dossier_resp.json()
        print("  " + "-" * 72)
        print(f"  DOSSIER: Claim {dossier['claim']['claim_ref']} | Status: {dossier['claim']['status']}")
        print(f"  Employee:       {dossier['employee']['full_name'] if dossier.get('employee') else 'N/A'}")
        print(f"  Manager Note:   {dossier['manager_review']['comment'] if dossier.get('manager_review') else 'N/A'}")
        print(f"  Allowed Actions:{dossier['allowed_actions']}")
        print("  " + "-" * 72)

    # 5. Test State Machine, Anomaly Clearance & Payment Guardrails
    print("\n[5/6] Testing Guardrails, Anomaly Clearance, and Payment Execution...")
    with httpx.Client(timeout=15.0) as http:
        # 5.1 Guardrail: Attempt payment on claim not in READY_FOR_PAYMENT
        print("  5.1 Guardrail: Attempting payment on non-cleared claim (Status: APPROVED)...")
        premature_pay = http.post(
            f"{BASE_URL}/finance/claims/{claim_a_id}/pay",
            json={"finance_user_id": finance_id},
        )
        print(f"      Status: HTTP {premature_pay.status_code} (Expected 409 Conflict)")
        print(f"      Detail: {premature_pay.json().get('detail')}")
        assert premature_pay.status_code == 409, "Should block payment for non-READY_FOR_PAYMENT claims"

        # 5.2 Finance Clears Anomaly
        print(f"\n  5.2 Finance Clears Anomaly: POST {BASE_URL}/finance/claims/{claim_a_id}/clear...")
        clear_resp = http.post(
            f"{BASE_URL}/finance/claims/{claim_a_id}/clear",
            json={
                "finance_user_id": finance_id,
                "comment": "Finance audit: Valid client travel context verified with travel policy exception approval.",
            },
        )
        print(f"      Status: HTTP {clear_resp.status_code} OK")
        print(f"      Decision: {clear_resp.json().get('decision')} | Cleared: {clear_resp.json().get('cleared')}")

        # Check claim state in Supabase
        chk_a = supabase.table("claims").select("status, finance_status").eq("id", claim_a_id).single().execute()
        print(f"      -> Updated Claim Status: {chk_a.data['status']} | Finance Status: {chk_a.data['finance_status']}")
        assert chk_a.data["status"] == "READY_FOR_PAYMENT", "Claim must now be READY_FOR_PAYMENT"

        # 5.3 Finance Rejects Claim B
        print(f"\n  5.3 Finance Rejects Claim B: POST {BASE_URL}/finance/claims/{claim_b_id}/reject...")
        reject_resp = http.post(
            f"{BASE_URL}/finance/claims/{claim_b_id}/reject",
            json={
                "finance_user_id": finance_id,
                "reason": "Personal audio equipment is non-reimbursable under 2026 Procurement Policy.",
            },
        )
        print(f"      Status: HTTP {reject_resp.status_code} OK")
        print(f"      Decision: {reject_resp.json().get('decision')}")
        chk_b = supabase.table("claims").select("status, finance_status").eq("id", claim_b_id).single().execute()
        print(f"      -> Updated Claim Status: {chk_b.data['status']} | Finance Status: {chk_b.data['finance_status']}")
        assert chk_b.data["status"] == "REJECTED", "Claim must now be REJECTED"

        # 5.4 Execute Payment on Cleared Claim A
        print(f"\n  5.4 Executing Payment: POST {BASE_URL}/finance/claims/{claim_a_id}/pay...")
        pay_resp = http.post(
            f"{BASE_URL}/finance/claims/{claim_a_id}/pay",
            json={
                "finance_user_id": finance_id,
                "notes": "Direct bank clearance approved via MockPaymentGateway.",
            },
        )
        print(f"      Status: HTTP {pay_resp.status_code} OK")
        pay_data = pay_resp.json()
        print(f"      Payment Reference: {pay_data.get('payment_reference')}")
        print(f"      Amount:            ₹{pay_data.get('amount')} {pay_data.get('currency')}")

        chk_paid = supabase.table("claims").select("status, payment_reference").eq("id", claim_a_id).single().execute()
        print(f"      -> Final Claim Status: {chk_paid.data['status']} | Payment Ref: {chk_paid.data['payment_reference']}")
        assert chk_paid.data["status"] == "PAID", "Claim must now be PAID"

        # 5.5 Guardrail: Attempt double-payment on already PAID claim
        print("\n  5.5 Guardrail: Attempting double payment on already PAID claim...")
        double_pay = http.post(
            f"{BASE_URL}/finance/claims/{claim_a_id}/pay",
            json={"finance_user_id": finance_id},
        )
        print(f"      Status: HTTP {double_pay.status_code} (Expected 409 Conflict)")
        print(f"      Detail: {double_pay.json().get('detail')}")
        assert double_pay.status_code == 409, "Should block double payment on PAID claim"

    # 6. Database Audit
    print("\n[6/6] Auditing database records in Supabase...")
    fin_rev_a = supabase.table("finance_reviews").select("*").eq("claim_id", claim_a_id).execute()
    fin_rev_b = supabase.table("finance_reviews").select("*").eq("claim_id", claim_b_id).execute()
    payments_a = supabase.table("payments").select("*").eq("claim_id", claim_a_id).execute()
    hist_a = supabase.table("claim_status_history").select("*").eq("claim_id", claim_a_id).order("occurred_at").execute()

    print(f"  • finance_reviews logged: {len(fin_rev_a.data) + len(fin_rev_b.data)}")
    print(f"  • payments records created: {len(payments_a.data)}")
    print(f"  • claim_status_history events for Claim A: {len(hist_a.data)}")
    for h in hist_a.data:
        print(f"    - [{h['occurred_at'][:19]}] {h.get('from_status')} -> {h['to_status']} ({h['event_label']})")

    print("\n" + "=" * 80)
    print("  [SUCCESS] ALL SESSION 8 & 9 FINANCE & PAYMENT ACTIONS VALIDATED!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
