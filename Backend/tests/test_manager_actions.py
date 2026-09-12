"""
tests/test_manager_actions.py
Unit tests for Session 7: Manager Actions.
Covers authorization enforcement, dossier inspection, clean approval to READY_FOR_PAYMENT,
flagged direct approval blocking, context confirmation to MANAGER_CONFIRMED, and rejection.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import supabase
from app.models.enums import ClaimStatus, VerificationStatus, FinanceDecision
from main import app

client = TestClient(app)


@pytest.fixture
def test_data():
    employee_id = str(uuid4())
    manager_id = str(uuid4())
    other_manager_id = str(uuid4())
    claim_id = str(uuid4())

    claim_clean = {
        "id": claim_id,
        "claim_ref": "CLM-CLEAN-01",
        "employee_id": employee_id,
        "manager_id": manager_id,
        "merchant": "Uber",
        "claim_type": "Travel",
        "amount": 450.0,
        "currency": "INR",
        "status": ClaimStatus.UNDER_REVIEW.value,
        "verification_status": VerificationStatus.CLEAN.value,
        "ocr_status": "COMPLETED",
        "finance_status": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    claim_flagged = {
        "id": claim_id,
        "claim_ref": "CLM-FLAGGED-01",
        "employee_id": employee_id,
        "manager_id": manager_id,
        "merchant": "Uber",
        "claim_type": "Travel",
        "amount": 450.0,
        "currency": "INR",
        "status": ClaimStatus.FLAGGED.value,
        "verification_status": VerificationStatus.FLAGGED.value,
        "ocr_status": "COMPLETED",
        "finance_status": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


    return {
        "employee_id": employee_id,
        "manager_id": manager_id,
        "other_manager_id": other_manager_id,
        "claim_id": claim_id,
        "claim_clean": claim_clean,
        "claim_flagged": claim_flagged,
    }


class TestManagerAuthorization:
    """Ensure assigned manager enforcement and self-approval blocking."""

    def test_self_approval_blocked(self, test_data):
        with patch.object(supabase, "table") as mock_table:
            mock_select = MagicMock()
            mock_select.select.return_value.eq.return_value.single.return_value.execute.return_value.data = test_data["claim_clean"]
            mock_table.return_value = mock_select

            response = client.post(
                f"/api/v1/manager/claims/{test_data['claim_id']}/approve",
                json={"manager_id": test_data["employee_id"], "decision": "APPROVED", "comment": "Trying self-approval"},
            )
            assert response.status_code == 403
            assert "Self-approval is not permitted" in response.json()["detail"]

    def test_unassigned_manager_blocked(self, test_data):
        with patch.object(supabase, "table") as mock_table:
            mock_select = MagicMock()
            mock_select.select.return_value.eq.return_value.single.return_value.execute.return_value.data = test_data["claim_clean"]
            mock_table.return_value = mock_select

            response = client.post(
                f"/api/v1/manager/claims/{test_data['claim_id']}/approve",
                json={"manager_id": test_data["other_manager_id"], "decision": "APPROVED", "comment": "Unassigned manager"},
            )
            assert response.status_code == 403
            assert "You are not the assigned manager" in response.json()["detail"]


class TestCleanClaimApproval:
    """Test approving clean claims directly to READY_FOR_PAYMENT."""

    def test_approve_clean_claim_transitions_to_ready_for_payment(self, test_data):
        with patch.object(supabase, "table") as mock_table:
            # Mock select claim
            mock_select = MagicMock()
            mock_select.select.return_value.eq.return_value.single.return_value.execute.return_value.data = test_data["claim_clean"]

            # Mock update
            mock_update = MagicMock()
            mock_update.update.return_value.eq.return_value.execute.return_value.data = [test_data["claim_clean"]]

            # Mock review insert
            mock_review_insert = MagicMock()
            mock_review_insert.insert.return_value.execute.return_value.data = [{
                "id": str(uuid4()),
                "claim_id": test_data["claim_id"],
                "manager_id": test_data["manager_id"],
                "decision": "APPROVED",
                "comment": "Looks good",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }]

            # Route mock by table name
            def table_router(name):
                if name == "claims":
                    m = MagicMock()
                    m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = test_data["claim_clean"]
                    m.update.return_value.eq.return_value.execute.return_value.data = [test_data["claim_clean"]]
                    return m
                elif name == "manager_reviews":
                    return mock_review_insert
                elif name == "claim_status_history":
                    m = MagicMock()
                    m.insert.return_value.execute.return_value.data = []
                    return m
                return MagicMock()

            mock_table.side_effect = table_router

            response = client.post(
                f"/api/v1/manager/claims/{test_data['claim_id']}/approve",
                json={"manager_id": test_data["manager_id"], "decision": "APPROVED", "comment": "Looks good"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["decision"] == "APPROVED"
            assert data["comment"] == "Looks good"


class TestFlaggedClaimEnforcement:
    """Ensure flagged claims cannot be directly approved and require business context."""

    def test_approve_flagged_claim_is_blocked(self, test_data):
        with patch.object(supabase, "table") as mock_table:
            m = MagicMock()
            m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = test_data["claim_flagged"]
            mock_table.return_value = m

            response = client.post(
                f"/api/v1/manager/claims/{test_data['claim_id']}/approve",
                json={"manager_id": test_data["manager_id"], "decision": "APPROVED"},
            )
            assert response.status_code == 400
            assert "Flagged claims cannot be directly approved" in response.json()["detail"]
            assert "/confirm" in response.json()["detail"]

    def test_confirm_flagged_claim_requires_comment(self, test_data):
        with patch.object(supabase, "table") as mock_table:
            m = MagicMock()
            m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = test_data["claim_flagged"]
            mock_table.return_value = m

            response = client.post(
                f"/api/v1/manager/claims/{test_data['claim_id']}/confirm",
                json={"manager_id": test_data["manager_id"], "comment": "   "},
            )
            assert response.status_code == 422
            assert "Manager comment/reason is required" in response.json()["detail"]

    def test_confirm_flagged_claim_transitions_to_manager_confirmed(self, test_data):
        with patch.object(supabase, "table") as mock_table:
            mock_review_insert = MagicMock()
            mock_review_insert.insert.return_value.execute.return_value.data = [{
                "id": str(uuid4()),
                "claim_id": test_data["claim_id"],
                "manager_id": test_data["manager_id"],
                "decision": "CONFIRMED",
                "comment": "Legitimate duplicate travel for two different clients on same day.",
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }]

            def table_router(name):
                if name == "claims":
                    m = MagicMock()
                    m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = test_data["claim_flagged"]
                    m.update.return_value.eq.return_value.execute.return_value.data = [test_data["claim_flagged"]]
                    return m
                elif name == "manager_reviews":
                    return mock_review_insert
                elif name == "claim_status_history":
                    m = MagicMock()
                    m.insert.return_value.execute.return_value.data = []
                    return m
                return MagicMock()

            mock_table.side_effect = table_router

            response = client.post(
                f"/api/v1/manager/claims/{test_data['claim_id']}/confirm",
                json={
                    "manager_id": test_data["manager_id"],
                    "comment": "Legitimate duplicate travel for two different clients on same day.",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["decision"] == "CONFIRMED"
            assert "Legitimate duplicate travel" in data["comment"]


class TestManagerReject:
    """Ensure rejection requires comment and records correctly."""

    def test_reject_requires_comment(self, test_data):
        with patch.object(supabase, "table") as mock_table:
            m = MagicMock()
            m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = test_data["claim_clean"]
            mock_table.return_value = m

            response = client.post(
                f"/api/v1/manager/claims/{test_data['claim_id']}/reject",
                json={"manager_id": test_data["manager_id"], "decision": "REJECTED", "comment": ""},
            )
            assert response.status_code == 422
            assert "rejection reason is required" in response.json()["detail"]


class TestManagerDossier:
    """Test comprehensive review dossier retrieval."""

    def test_manager_claim_dossier_structure(self, test_data):
        with patch.object(supabase, "table") as mock_table:
            def table_router(name):
                m = MagicMock()
                if name == "claims":
                    m.select.return_value.eq.return_value.single.return_value.execute.return_value.data = test_data["claim_flagged"]
                elif name == "users":
                    m.select.return_value.eq.return_value.execute.return_value.data = [{
                        "id": test_data["employee_id"],
                        "full_name": "Vickey Kumar",
                        "email": "vickey.kumar@company.com",
                        "department": "Engineering",
                        "role": "staff",
                    }]
                elif name == "claim_documents":
                    m.select.return_value.eq.return_value.execute.return_value.data = [{
                        "id": str(uuid4()),
                        "file_name": "receipt.png",
                        "file_url": "https://storage/receipt.png",
                    }]
                elif name == "claim_extracted_data":
                    m.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [{
                        "merchant_normalized": "Uber",
                        "total": 450.0,
                    }]
                elif name == "claim_verifications":
                    m.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [{
                        "decision": "POTENTIAL_DUPLICATE",
                        "similarity_score": 0.95,
                        "explanation": "Automation Alert: 95% duplicate risk",
                        "evidence": {
                            "llm_analysis": {
                                "duplicate_risk_percentage": 95,
                                "risk_classification": "CRITICAL RISK",
                                "matched_claim_ref": "CLM-8103",
                                "reasoning": "Matching invoice and amount.",
                                "manager_recommendation": "Automation Alert: Verify before approving.",
                                "suggested_action": "VERIFY_REIMBURSEMENT",
                            },
                            "all_candidates": [],
                        },
                    }]
                elif name == "claim_status_history":
                    m.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
                return m

            mock_table.side_effect = table_router

            response = client.get(f"/api/v1/manager/claims/{test_data['claim_id']}")
            assert response.status_code == 200
            data = response.json()

            assert "claim" in data
            assert data["claim"]["claim_ref"] == "CLM-FLAGGED-01"
            assert data["employee"]["email"] == "vickey.kumar@company.com"
            assert data["llm_analysis"]["risk_classification"] == "CRITICAL RISK"
            assert data["allowed_actions"] == ["CONFIRM_CONTEXT", "REJECT"]
