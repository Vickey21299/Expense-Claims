"""
tests/test_finance_and_payments.py
Unit tests for Session 8 (Finance Actions & Dossier) and Session 9 (Payment Execution & Provider Abstraction).
Covers finance queue enrichment, full dossier assembly, anomaly clearance, finance rejection with reasons,
payment execution on READY_FOR_PAYMENT, prevention of payment on non-eligible or terminal states,
and MockPaymentProvider abstraction.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import supabase
from app.models.enums import ClaimStatus, VerificationStatus, FinanceDecision
from app.models.payments import PayoutRequest
from app.services.payment import MockPaymentProvider, PaymentService
from main import app

client = TestClient(app)


@pytest.fixture
def test_data():
    employee_id = str(uuid4())
    manager_id = str(uuid4())
    finance_id = str(uuid4())
    claim_id = str(uuid4())

    claim_confirmed = {
        "id": claim_id,
        "claim_ref": "CLM-MGR-CONFIRMED-01",
        "employee_id": employee_id,
        "manager_id": manager_id,
        "merchant": "Uber",
        "claim_type": "Travel",
        "amount": 450.0,
        "currency": "INR",
        "status": ClaimStatus.MANAGER_CONFIRMED.value,
        "verification_status": VerificationStatus.FLAGGED.value,
        "ocr_status": "COMPLETED",
        "finance_status": FinanceDecision.FINANCE_PENDING.value,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    claim_ready = {
        "id": claim_id,
        "claim_ref": "CLM-READY-PAY-01",
        "employee_id": employee_id,
        "manager_id": manager_id,
        "merchant": "Marriott",
        "claim_type": "Accommodation",
        "amount": 6200.0,
        "currency": "INR",
        "status": ClaimStatus.READY_FOR_PAYMENT.value,
        "verification_status": VerificationStatus.CLEAN.value,
        "ocr_status": "COMPLETED",
        "finance_status": FinanceDecision.FINANCE_CLEARED.value,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    claim_paid = {
        **claim_ready,
        "status": ClaimStatus.PAID.value,
        "payment_reference": "TXN-PAY-20260912-1234ABCD",
    }

    return {
        "employee_id": employee_id,
        "manager_id": manager_id,
        "finance_id": finance_id,
        "claim_id": claim_id,
        "claim_confirmed": claim_confirmed,
        "claim_ready": claim_ready,
        "claim_paid": claim_paid,
    }


# ===========================================================================
# 1. MockPaymentProvider Tests
# ===========================================================================
def test_mock_payment_provider():
    import asyncio

    async def _run():
        provider = MockPaymentProvider(provider_name="TestBankGateway", channel="NEFT_TEST")
        req = PayoutRequest(
            claim_id=uuid4(),
            amount=1500.0,
            currency="INR",
            recipient_id=uuid4(),
        )
        res = await provider.execute_payout(req)
        assert res.success is True
        assert res.provider_name == "TestBankGateway"
        assert res.channel == "NEFT_TEST"
        assert res.transaction_reference.startswith("TXN-PAY-")
        assert res.details.get("status") == "SETTLED"

        # Custom reference
        custom_req = PayoutRequest(
            claim_id=uuid4(),
            amount=500.0,
            currency="INR",
            recipient_id=uuid4(),
            reference_id="CUSTOM-REF-9999",
        )
        custom_res = await provider.execute_payout(custom_req)
        assert custom_res.transaction_reference == "CUSTOM-REF-9999"

    asyncio.run(_run())


# ===========================================================================
# 2. Finance Queue Tests
# ===========================================================================
def test_finance_queue(test_data):
    claims = [test_data["claim_confirmed"], test_data["claim_ready"]]
    with patch.object(supabase, "table") as mock_table:
        # Mock claims select
        mock_claims_q = MagicMock()
        mock_claims_q.select.return_value = mock_claims_q
        mock_claims_q.in_.return_value = mock_claims_q
        mock_claims_q.order.return_value = mock_claims_q
        mock_claims_q.execute.return_value = MagicMock(data=claims)

        # Mock manager_reviews
        mock_mgr_q = MagicMock()
        mock_mgr_q.select.return_value = mock_mgr_q
        mock_mgr_q.in_.return_value = mock_mgr_q
        mock_mgr_q.order.return_value = mock_mgr_q
        mock_mgr_q.execute.return_value = MagicMock(data=[
            {"claim_id": test_data["claim_id"], "comment": "Legitimate business context confirmed."}
        ])

        # Mock verifications
        mock_ver_q = MagicMock()
        mock_ver_q.select.return_value = mock_ver_q
        mock_ver_q.in_.return_value = mock_ver_q
        mock_ver_q.order.return_value = mock_ver_q
        mock_ver_q.execute.return_value = MagicMock(data=[
            {
                "claim_id": test_data["claim_id"],
                "evidence": {
                    "llm_analysis": {
                        "duplicate_risk_percentage": 90,
                        "risk_classification": "HIGH RISK",
                        "reasoning": "High similarity on amount and employee.",
                        "manager_recommendation": "Automation alert: verify client trip.",
                    }
                }
            }
        ])

        def table_side_effect(name):
            if name == "claims":
                return mock_claims_q
            elif name == "manager_reviews":
                return mock_mgr_q
            elif name == "claim_verifications":
                return mock_ver_q
            return MagicMock()

        mock_table.side_effect = table_side_effect

        resp = client.get("/api/v1/finance/claims")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["claims"][0]["manager_comment"] == "Legitimate business context confirmed."
        assert body["claims"][0]["duplicate_risk_percentage"] == 90
        assert body["claims"][0]["risk_classification"] == "HIGH RISK"


# ===========================================================================
# 3. Finance Claim Dossier Tests
# ===========================================================================
def test_finance_claim_dossier(test_data):
    claim = test_data["claim_confirmed"]
    with patch.object(supabase, "table") as mock_table:
        mock_claim_tbl = MagicMock()
        mock_claim_tbl.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=claim)

        mock_user_tbl = MagicMock()
        mock_user_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": test_data["employee_id"],
            "full_name": "Vickey Kumar",
            "email": "vickey.kumar@company.com",
            "department": "Engineering",
            "role": "staff",
            "job_title": "Software Engineer",
        }])

        mock_docs_tbl = MagicMock()
        mock_docs_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "file_name": "uber_trip.pdf",
            "file_url": "https://storage.supabase.com/receipts/uber_trip.pdf",
        }])

        mock_ocr_tbl = MagicMock()
        mock_ocr_tbl.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[{
            "merchant": "Uber",
            "total_amount": 450.0,
            "currency": "INR",
        }])

        mock_ver_tbl = MagicMock()
        mock_ver_tbl.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[{
            "verification_status": "FLAGGED",
            "evidence": {
                "llm_analysis": {
                    "duplicate_risk_percentage": 92,
                    "risk_classification": "HIGH RISK",
                    "reasoning": "Duplicate ride pattern on same day.",
                    "manager_recommendation": "Automation Alert: Verify if duplicate.",
                },
                "all_candidates": [
                    {
                        "matched_claim_id": str(uuid4()),
                        "claim_ref": "CLM-PREV-01",
                        "similarity_score": 0.95,
                        "age_days": 1,
                        "status": "APPROVED",
                        "signals": ["Same employee", "Exact amount match"],
                        "field_scores": {
                            "merchant_similarity": 1.0,
                            "amount_similarity": 1.0,
                            "date_similarity": 0.9,
                            "category_similarity": 1.0,
                            "invoice_similarity": 0.8,
                            "receipt_hash_match": False,
                            "same_employee": True,
                        },
                    }
                ]
            }
        }])

        mock_mgr_tbl = MagicMock()
        mock_mgr_tbl.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[{
            "decision": "CONFIRMED",
            "comment": "Manager confirms this was urgent client visit.",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }])

        mock_pay_tbl = MagicMock()
        mock_pay_tbl.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

        mock_hist_tbl = MagicMock()
        mock_hist_tbl.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "to_status": ClaimStatus.MANAGER_CONFIRMED.value,
            "event_label": "Manager Confirmed Business Context",
            "comment": "Manager confirms this was urgent client visit.",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }])

        def table_resolver(name):
            if name == "claims":
                return mock_claim_tbl
            elif name == "users":
                return mock_user_tbl
            elif name == "claim_documents":
                return mock_docs_tbl
            elif name == "claim_extracted_data":
                return mock_ocr_tbl
            elif name == "claim_verifications":
                return mock_ver_tbl
            elif name == "manager_reviews":
                return mock_mgr_tbl
            elif name == "payments":
                return mock_pay_tbl
            elif name == "claim_status_history":
                return mock_hist_tbl
            return MagicMock()

        mock_table.side_effect = table_resolver

        resp = client.get(f"/api/v1/finance/claims/{test_data['claim_id']}")
        assert resp.status_code == 200
        dossier = resp.json()
        assert dossier["claim"]["claim_ref"] == "CLM-MGR-CONFIRMED-01"
        assert dossier["employee"]["email"] == "vickey.kumar@company.com"
        assert len(dossier["documents"]) == 1
        assert dossier["extracted_data"]["merchant"] == "Uber"
        assert dossier["llm_analysis"]["duplicate_risk_percentage"] == 92
        assert dossier["manager_review"]["comment"] == "Manager confirms this was urgent client visit."
        assert len(dossier["matched_candidates"]) == 1
        assert "CLEAR_ANOMALY" in dossier["allowed_actions"]
        assert "REJECT" in dossier["allowed_actions"]


# ===========================================================================
# 4. Finance Anomaly Clearance Tests
# ===========================================================================
def test_finance_clear_anomaly_success(test_data):
    claim = test_data["claim_confirmed"]
    with patch.object(supabase, "table") as mock_table:
        mock_select = MagicMock()
        mock_select.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=claim)

        mock_update = MagicMock()
        mock_update.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[claim])

        mock_review_insert = MagicMock()
        mock_review_insert.insert.return_value.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "claim_id": test_data["claim_id"],
            "finance_user_id": test_data["finance_id"],
            "decision": FinanceDecision.FINANCE_CLEARED.value,
            "cleared": True,
            "comment": "Anomaly cleared based on client audit schedule.",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }])

        mock_hist_insert = MagicMock()
        mock_hist_insert.insert.return_value.execute.return_value = MagicMock()

        def table_resolver(name):
            if name == "claims":
                tbl = MagicMock()
                tbl.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=claim)
                tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[claim])
                return tbl
            elif name == "finance_reviews":
                return mock_review_insert
            elif name == "claim_status_history":
                return mock_hist_insert
            return MagicMock()

        mock_table.side_effect = table_resolver

        resp = client.post(
            f"/api/v1/finance/claims/{test_data['claim_id']}/clear",
            json={
                "finance_user_id": test_data["finance_id"],
                "comment": "Anomaly cleared based on client audit schedule.",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == FinanceDecision.FINANCE_CLEARED.value
        assert body["cleared"] is True


def test_finance_clear_invalid_status_conflict(test_data):
    claim_submitted = {**test_data["claim_confirmed"], "status": ClaimStatus.SUBMITTED.value}
    with patch.object(supabase, "table") as mock_table:
        mock_tbl = MagicMock()
        mock_tbl.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=claim_submitted)
        mock_table.return_value = mock_tbl

        resp = client.post(
            f"/api/v1/finance/claims/{test_data['claim_id']}/clear",
            json={"finance_user_id": test_data["finance_id"]},
        )
        assert resp.status_code == 409
        assert "Finance can only clear claims in MANAGER_CONFIRMED or APPROVED status" in resp.json()["detail"]


# ===========================================================================
# 5. Finance Rejection Tests
# ===========================================================================
def test_finance_reject_claim_success(test_data):
    claim = test_data["claim_confirmed"]
    with patch.object(supabase, "table") as mock_table:
        mock_review_insert = MagicMock()
        mock_review_insert.insert.return_value.execute.return_value = MagicMock(data=[{
            "id": str(uuid4()),
            "claim_id": test_data["claim_id"],
            "finance_user_id": test_data["finance_id"],
            "decision": FinanceDecision.FINANCE_REJECTED.value,
            "cleared": False,
            "comment": "Policy limit exceeded: daily taxi cap is INR 400.",
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }])

        def table_resolver(name):
            if name == "claims":
                tbl = MagicMock()
                tbl.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=claim)
                tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[claim])
                return tbl
            elif name == "finance_reviews":
                return mock_review_insert
            elif name == "claim_status_history":
                tbl = MagicMock()
                tbl.insert.return_value.execute.return_value = MagicMock()
                return tbl
            return MagicMock()

        mock_table.side_effect = table_resolver

        resp = client.post(
            f"/api/v1/finance/claims/{test_data['claim_id']}/reject",
            json={
                "finance_user_id": test_data["finance_id"],
                "reason": "Policy limit exceeded: daily taxi cap is INR 400.",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["decision"] == FinanceDecision.FINANCE_REJECTED.value
        assert body["cleared"] is False


def test_finance_reject_missing_reason_fails(test_data):
    resp = client.post(
        f"/api/v1/finance/claims/{test_data['claim_id']}/reject",
        json={"finance_user_id": test_data["finance_id"], "reason": "   "},
    )
    assert resp.status_code == 422
    assert "A reason is required" in resp.json()["detail"]


# ===========================================================================
# 6. Payment Execution Tests
# ===========================================================================
def test_finance_pay_success(test_data):
    claim = test_data["claim_ready"]
    now_iso = datetime.now(timezone.utc).isoformat()
    mock_payment_row = {
        "id": str(uuid4()),
        "claim_id": test_data["claim_id"],
        "payment_reference": "TXN-PAY-20260912-TEST99",
        "amount": claim["amount"],
        "currency": claim["currency"],
        "processed_by": test_data["finance_id"],
        "processed_at": now_iso,
        "notes": "Paid via batch run",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    with patch.object(supabase, "table") as mock_table:
        def table_resolver(name):
            if name == "claims":
                tbl = MagicMock()
                tbl.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=claim)
                tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[claim])
                return tbl
            elif name == "payments":
                tbl = MagicMock()
                tbl.insert.return_value.execute.return_value = MagicMock(data=[mock_payment_row])
                return tbl
            elif name == "claim_status_history":
                tbl = MagicMock()
                tbl.insert.return_value.execute.return_value = MagicMock()
                return tbl
            return MagicMock()

        mock_table.side_effect = table_resolver

        resp = client.post(
            f"/api/v1/finance/claims/{test_data['claim_id']}/pay",
            json={
                "finance_user_id": test_data["finance_id"],
                "notes": "Paid via batch run",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["claim_id"] == test_data["claim_id"]
        assert body["amount"] == 6200.0
        assert body["payment_reference"].startswith("TXN-PAY-")


def test_finance_pay_blocked_on_non_eligible_status(test_data):
    # Try paying a claim in MANAGER_CONFIRMED before clearing
    claim = test_data["claim_confirmed"]
    with patch.object(supabase, "table") as mock_table:
        mock_tbl = MagicMock()
        mock_tbl.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=claim)
        mock_table.return_value = mock_tbl

        resp = client.post(
            f"/api/v1/finance/claims/{test_data['claim_id']}/pay",
            json={"finance_user_id": test_data["finance_id"]},
        )
        assert resp.status_code == 409
        assert "Only claims in READY_FOR_PAYMENT status can be paid" in resp.json()["detail"]


def test_finance_pay_blocked_on_already_paid_terminal_state(test_data):
    # Try paying an already PAID claim
    claim = test_data["claim_paid"]
    with patch.object(supabase, "table") as mock_table:
        mock_tbl = MagicMock()
        mock_tbl.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=claim)
        mock_table.return_value = mock_tbl

        resp = client.post(
            f"/api/v1/finance/claims/{test_data['claim_id']}/pay",
            json={"finance_user_id": test_data["finance_id"]},
        )
        assert resp.status_code == 409
        assert "PAID is a terminal state" in resp.json()["detail"]


def test_payments_router_endpoint(test_data):
    claim = test_data["claim_ready"]
    now_iso = datetime.now(timezone.utc).isoformat()
    mock_payment_row = {
        "id": str(uuid4()),
        "claim_id": test_data["claim_id"],
        "payment_reference": "TXN-PAY-CUSTOM-111",
        "amount": claim["amount"],
        "currency": claim["currency"],
        "processed_by": test_data["finance_id"],
        "processed_at": now_iso,
        "notes": "Direct /payments call",
        "created_at": now_iso,
        "updated_at": now_iso,
    }

    with patch.object(supabase, "table") as mock_table:
        def table_resolver(name):
            if name == "claims":
                tbl = MagicMock()
                tbl.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=claim)
                tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[claim])
                return tbl
            elif name == "payments":
                tbl = MagicMock()
                tbl.insert.return_value.execute.return_value = MagicMock(data=[mock_payment_row])
                return tbl
            elif name == "claim_status_history":
                tbl = MagicMock()
                tbl.insert.return_value.execute.return_value = MagicMock()
                return tbl
            return MagicMock()

        mock_table.side_effect = table_resolver

        resp = client.post(
            "/api/v1/payments",
            json={
                "claim_id": test_data["claim_id"],
                "amount": claim["amount"],
                "currency": claim["currency"],
                "processed_by": test_data["finance_id"],
                "notes": "Direct /payments call",
                "payment_reference": "TXN-PAY-CUSTOM-111",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["payment_reference"] == "TXN-PAY-CUSTOM-111"
