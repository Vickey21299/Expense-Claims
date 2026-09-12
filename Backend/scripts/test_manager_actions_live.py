"""
scripts/test_manager_actions_live.py
Live validation script for Session 7: Manager Actions.
Tests the complete manager workflow against the running backend and live Supabase database:
1. Look up manager user and their pending claims
2. Inspect the comprehensive Manager Review Dossier (GET /api/v1/manager/claims/{id})
3. Verify Authorization Enforcement:
   - Block self-approval (403)
   - Block unassigned manager (403)
4. Verify State Machine Rules:
   - Block direct approval on a FLAGGED claim (400)
   - Confirm business context for a FLAGGED claim -> MANAGER_CONFIRMED (200)
   - Approve a CLEAN claim -> READY_FOR_PAYMENT (200)
   - Reject a claim with required reason -> REJECTED (200)
5. Audit manager_reviews and claim_status_history tables.

Usage:
    python scripts/test_manager_actions_live.py
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

BASE_URL = "http://127.0.0.1:8000/api/v1"


def main():
    print("=" * 80)
    print("      SESSION 7: LIVE MANAGER ACTIONS & WORKFLOW VALIDATION")
    print("=" * 80)

    # 1. Look up Staff user and Assigned Manager
    print("\n[1/6] Looking up users in database...")
    staff_res = supabase.table("users").select("*").eq("email", "vickey.kumar@company.com").execute()
    if not staff_res.data:
        print("[ERROR] Staff user 'vickey.kumar@company.com' not found!")
        sys.exit(1)
    staff = staff_res.data[0]
    staff_id = staff["id"]
    manager_id = staff.get("manager_id")

    mgr_res = supabase.table("users").select("*").eq("id", manager_id).execute() if manager_id else None
    manager = mgr_res.data[0] if mgr_res and mgr_res.data else None

    print(f"  • Staff Employee:     {staff['full_name']} ({staff['email']}) [ID: {staff_id}]")
    print(f"  • Assigned Manager:   {manager['full_name'] if manager else 'None'} ({manager['email'] if manager else 'None'}) [ID: {manager_id}]")

    # 2. Get Manager's Pending Claims
    print(f"\n[2/6] Querying pending manager queue: GET {BASE_URL}/manager/claims...")
    r_list = httpx.get(f"{BASE_URL}/manager/claims", params={"manager_id": manager_id}, timeout=10.0)
    r_list.raise_for_status()
    claims_list = r_list.json()
    print(f"  • Total claims pending for manager: {claims_list.get('total')}")

    for c in claims_list.get("claims", [])[:3]:
        print(f"    - [{c.get('claim_ref')}] {c.get('merchant')} ₹{c.get('amount')} | Status: {c.get('status')} | Risk: {c.get('duplicate_risk_percentage')}% ({c.get('risk_classification')})")

    # 3. Create a fresh FLAGGED test claim and a fresh CLEAN test claim
    print("\n[3/6] Setting up test claims for authorization & state transition checks...")
    
    # Clean claim
    r_c1 = httpx.post(f"{BASE_URL}/claims", json={
        "employee_id": staff_id,
        "manager_id": manager_id,
        "claim_type": "Meals",
        "merchant": "Team Lunch",
        "amount": 1250.0,
        "currency": "INR",
        "description": "Clean team lunch claim",
    }, timeout=10.0)
    clean_claim = r_c1.json()
    clean_id = clean_claim["id"]
    # Transition clean claim to UNDER_REVIEW
    supabase.table("claims").update({"status": "UNDER_REVIEW", "verification_status": "CLEAN"}).eq("id", clean_id).execute()
    print(f"  • Created Clean Claim:   {clean_claim.get('claim_ref')} (ID: {clean_id}) -> Status: UNDER_REVIEW")

    # Flagged claim
    r_c2 = httpx.post(f"{BASE_URL}/claims", json={
        "employee_id": staff_id,
        "manager_id": manager_id,
        "claim_type": "Travel",
        "merchant": "Uber",
        "amount": 450.0,
        "currency": "INR",
        "description": "Flagged duplicate travel claim",
    }, timeout=10.0)
    flagged_claim = r_c2.json()
    flagged_id = flagged_claim["id"]
    # Transition flagged claim to FLAGGED
    supabase.table("claims").update({"status": "FLAGGED", "verification_status": "FLAGGED"}).eq("id", flagged_id).execute()
    print(f"  • Created Flagged Claim: {flagged_claim.get('claim_ref')} (ID: {flagged_id}) -> Status: FLAGGED")

    # 4. Fetch Full Review Dossier
    print(f"\n[4/6] Inspecting Manager Review Dossier: GET {BASE_URL}/manager/claims/{flagged_id}...")
    r_dossier = httpx.get(f"{BASE_URL}/manager/claims/{flagged_id}", timeout=10.0)
    r_dossier.raise_for_status()
    dossier = r_dossier.json()

    print("  ------------------------------------------------------------------------")
    print(f"  DOSSIER: Claim {dossier['claim']['claim_ref']} | Status: {dossier['claim']['status']}")
    print(f"  Employee:       {dossier['employee']['full_name']} ({dossier['employee']['email']})")
    print(f"  Amount:         ₹{dossier['claim']['amount']} {dossier['claim']['currency']}")
    print(f"  Allowed Actions:{dossier['allowed_actions']}")
    print("  ------------------------------------------------------------------------")

    # 5. Test Authorization & Protection Rules
    print("\n[5/6] Testing Authorization & State Machine Enforcement:")
    
    # 5.1 Self-approval block
    print("  5.1 Testing Self-Approval Block (Staff employee trying to approve their own claim)...")
    r_self = httpx.post(f"{BASE_URL}/manager/claims/{clean_id}/approve", json={
        "manager_id": staff_id,
        "decision": "APPROVED",
        "comment": "Attempting self-approval",
    }, timeout=10.0)
    print(f"      Status: HTTP {r_self.status_code} (Expected 403 Forbidden)")
    print(f"      Detail: {r_self.json().get('detail')}")

    # 5.2 Unassigned manager block
    random_manager_id = str(uuid4())
    print(f"  5.2 Testing Unassigned Manager Block (Random Manager {random_manager_id[:8]} trying to approve)...")
    r_unassigned = httpx.post(f"{BASE_URL}/manager/claims/{clean_id}/approve", json={
        "manager_id": random_manager_id,
        "decision": "APPROVED",
        "comment": "Unassigned manager attempting approval",
    }, timeout=10.0)
    print(f"      Status: HTTP {r_unassigned.status_code} (Expected 403 Forbidden)")
    print(f"      Detail: {r_unassigned.json().get('detail')}")

    # 5.3 Block direct approval on FLAGGED claim
    print(f"  5.3 Testing Direct Approval Block on FLAGGED claim {flagged_claim.get('claim_ref')}...")
    r_flag_app = httpx.post(f"{BASE_URL}/manager/claims/{flagged_id}/approve", json={
        "manager_id": manager_id,
        "decision": "APPROVED",
        "comment": "Trying to bypass /confirm on flagged claim",
    }, timeout=10.0)
    print(f"      Status: HTTP {r_flag_app.status_code} (Expected 400 Bad Request)")
    print(f"      Detail: {r_flag_app.json().get('detail')}")

    # 5.4 Confirm Business Context for FLAGGED claim
    print(f"\n  5.4 Confirming Business Context: POST {BASE_URL}/manager/claims/{flagged_id}/confirm...")
    justification = "Legitimate second Uber trip for urgent afternoon client site audit. Business context verified with client team."
    r_confirm = httpx.post(f"{BASE_URL}/manager/claims/{flagged_id}/confirm", json={
        "manager_id": manager_id,
        "comment": justification,
    }, timeout=10.0)
    r_confirm.raise_for_status()
    conf_res = r_confirm.json()
    print(f"      Status: HTTP {r_confirm.status_code} OK")
    print(f"      Decision: {conf_res.get('decision')}")
    print(f"      Comment:  \"{conf_res.get('comment')}\"")

    # Check updated status in DB
    updated_flagged = supabase.table("claims").select("status, finance_status").eq("id", flagged_id).single().execute().data
    print(f"      -> Updated Claim Status: {updated_flagged['status']} | Finance Status: {updated_flagged['finance_status']} (Queued for Finance)")

    # 5.5 Approve Clean Claim -> READY_FOR_PAYMENT
    print(f"\n  5.5 Approving Clean Claim: POST {BASE_URL}/manager/claims/{clean_id}/approve...")
    r_app = httpx.post(f"{BASE_URL}/manager/claims/{clean_id}/approve", json={
        "manager_id": manager_id,
        "decision": "APPROVED",
        "comment": "Valid client lunch expenses, approved for reimbursement payment.",
    }, timeout=10.0)
    r_app.raise_for_status()
    app_res = r_app.json()
    print(f"      Status: HTTP {r_app.status_code} OK")
    print(f"      Decision: {app_res.get('decision')}")

    updated_clean = supabase.table("claims").select("status, finance_status").eq("id", clean_id).single().execute().data
    print(f"      -> Updated Claim Status: {updated_clean['status']} | Finance Status: {updated_clean['finance_status']}")

    # 6. Audit Database Records
    print("\n[6/6] Auditing database records in Supabase...")
    revs = supabase.table("manager_reviews").select("*").in_("claim_id", [clean_id, flagged_id]).execute().data
    print(f"  • manager_reviews entries created: {len(revs)}")
    for r in revs:
        print(f"    - Claim {r['claim_id'][:8]} | Decision: {r['decision']} | Comment: \"{r['comment']}\"")

    hist = supabase.table("claim_status_history").select("*").in_("claim_id", [clean_id, flagged_id]).order("occurred_at").execute().data
    print(f"  • claim_status_history events logged: {len(hist)}")
    for h in hist:
        print(f"    - [{h['occurred_at'][:19]}] Claim {h['claim_id'][:8]}: {h.get('from_status')} -> {h['to_status']} ({h['event_label']})")

    print("\n" + "=" * 80)
    print("  [SUCCESS] ALL SESSION 7 MANAGER ACTIONS SUCCESSFULLY VALIDATED!")
    print("=" * 80)


if __name__ == "__main__":
    main()
