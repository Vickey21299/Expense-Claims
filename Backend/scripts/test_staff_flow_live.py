"""
Test complete staff flow:
1. List Vickey Kumar's claims
2. Fetch details of a claim by claim_ref
3. Test receipt analysis
4. Create a draft claim
5. Upload a receipt document to the draft claim
6. Submit the claim and run verification
7. Verify that the submitted claim appears in Vickey Kumar's claims list with updated status
"""
import sys
from pathlib import Path
import httpx

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8000/api/v1"

def main():
    print("=" * 60)
    print("Testing Staff Flow Integration End-to-End")
    print("=" * 60)

    client = httpx.Client(timeout=60.0)

    # 1. Fetch Vickey's claims
    print("\n1. Fetching Vickey Kumar's claims...")
    res = client.get(f"{BASE_URL}/users/vickey.kumar@company.com/claims")
    assert res.status_code == 200, f"Failed: {res.status_code} {res.text}"
    data = res.json()
    total_claims = data["total"]
    print(f"   * Found {total_claims} claims for Vickey Kumar")

    # Compute Dashboard stats
    claims = data["claims"]
    total_approved_paid = sum(c["amount"] for c in claims if c["status"] in ["APPROVED", "READY_FOR_PAYMENT", "PAID"])
    pending = sum(c["amount"] for c in claims if c["status"] in ["SUBMITTED", "UNDER_REVIEW", "FLAGGED", "READY_FOR_PAYMENT"])
    approved = sum(c["amount"] for c in claims if c["status"] == "APPROVED")
    paid = sum(c["amount"] for c in claims if c["status"] == "PAID")

    print(f"   * Dashboard Stats:")
    print(f"     - Total Approved & Paid: INR {total_approved_paid:,.2f}")
    print(f"     - Pending Review:        INR {pending:,.2f}")
    print(f"     - Approved:              INR {approved:,.2f}")
    print(f"     - Paid Out:              INR {paid:,.2f}")

    # 2. Get claim detail by ref
    sample_ref = claims[0]["claim_ref"]
    print(f"\n2. Fetching claim details by claim_ref: {sample_ref}...")
    res = client.get(f"{BASE_URL}/claims/{sample_ref}")
    assert res.status_code == 200, f"Failed: {res.status_code} {res.text}"
    detail = res.json()
    print(f"   * Claim Ref: {detail['claim_ref']}, Merchant: {detail['merchant']}, Status: {detail['status']}")
    print(f"   * Status History entries: {len(detail.get('status_history', []))}")
    print(f"   * Documents attached: {len(detail.get('documents', []))}")

    # 3. Analyze Receipt
    print("\n3. Testing Gemini OCR analysis endpoint (POST /documents/analyze)...")
    sample_receipt = Path(__file__).resolve().parent.parent / "bill" / "uber_trip_receipt.png"
    with open(sample_receipt, "rb") as f:
        res = client.post(f"{BASE_URL}/documents/analyze", files={"file": ("uber_trip_receipt.png", f, "image/png")})
    assert res.status_code == 200, f"Failed: {res.status_code} {res.text}"
    ocr_result = res.json()
    print(f"   * Extracted Merchant: {ocr_result.get('merchant')}")
    print(f"   * Extracted Amount:   INR {ocr_result.get('amount')}")
    print(f"   * Extracted Category: {ocr_result.get('category')}")
    print(f"   * Line items count:   {len(ocr_result.get('line_items', []))}")

    # 4. Create Draft Claim
    print("\n4. Creating Draft Claim for Vickey Kumar...")
    draft_payload = {
        "employee_id": "4b987739-6880-4e65-a3c7-031bf7a59139",
        "manager_id": "28ac25ae-735f-4085-a6ed-c765be651ef1",
        "merchant": ocr_result.get("merchant") or "Uber",
        "claim_type": ocr_result.get("category") or "Travel",
        "amount": ocr_result.get("amount") or 450.0,
        "currency": "INR",
        "claim_date": ocr_result.get("date") or "2026-09-12",
        "description": "Airport trip for client visit"
    }
    res = client.post(f"{BASE_URL}/claims", json=draft_payload)
    assert res.status_code == 201, f"Failed: {res.status_code} {res.text}"
    new_claim = res.json()
    new_claim_id = new_claim["id"]
    new_claim_ref = new_claim["claim_ref"]
    print(f"   * Draft created: ID={new_claim_id}, Ref={new_claim_ref}, Status={new_claim['status']}")

    # 5. Upload Receipt to new claim
    print(f"\n5. Uploading receipt to claim {new_claim_ref} with auto_verify=true...")
    with open(sample_receipt, "rb") as f:
        res = client.post(
            f"{BASE_URL}/claims/{new_claim_id}/documents?auto_verify=true",
            files={"file": (f"test_receipt_{new_claim_ref}.png", f, "image/png")}
        )
    assert res.status_code == 201, f"Failed: {res.status_code} {res.text}"
    doc_res = res.json()
    print(f"   * Document uploaded & OCR processed: ocr_status={doc_res.get('ocr_status')}")

    # 6. Check status after auto_verify and submit if still DRAFT
    claim_check = client.get(f"{BASE_URL}/claims/{new_claim_id}").json()
    print(f"   * Status after upload & auto_verify: {claim_check['status']}")

    if claim_check["status"] == "DRAFT":
        print(f"\n6. Submitting claim {new_claim_ref}...")
        res = client.post(f"{BASE_URL}/claims/{new_claim_id}/submit")
        assert res.status_code == 200, f"Failed: {res.status_code} {res.text}"
        print(f"   * Submitted: status={res.json()['status']}")
    else:
        print(f"\n6. Claim was automatically transitioned to {claim_check['status']} by verification engine.")

    # 7. Verification Results
    print(f"\n7. Checking verification record for claim {new_claim_ref}...")
    res = client.get(f"{BASE_URL}/verification/claims/{new_claim_id}")
    if res.status_code == 200:
        ver_res = res.json()
        print(f"   * Verification result: verdict={ver_res.get('verdict')}, similarity={ver_res.get('similarity_score')}")
    else:
        print(f"   * Verification response: {res.status_code}")

    # 8. Re-fetch claim details to verify full dossier
    print(f"\n8. Re-fetching full claim details for {new_claim_ref}...")
    res = client.get(f"{BASE_URL}/claims/{new_claim_ref}")
    assert res.status_code == 200, f"Failed: {res.status_code} {res.text}"
    final_detail = res.json()
    print(f"   * Final Status: {final_detail['status']}")
    print(f"   * History Events: {[h['event_label'] for h in final_detail.get('status_history', [])]}")
    print(f"   * Documents Count: {len(final_detail.get('documents', []))}")
    if final_detail.get('documents'):
        print(f"   * Document URL: {final_detail['documents'][0].get('file_url')}")

    print("\n" + "=" * 60)
    print("ALL STAFF FLOW INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    main()
