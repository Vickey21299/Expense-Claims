# Complete API Reference Manual (`/api/v1`)

> **Base URL**: `http://localhost:8000/api/v1`  
> **Interactive Swagger UI**: `http://localhost:8000/docs`  
> **ReDoc**: `http://localhost:8000/redoc`

---

## 📋 Table of Contents
1. [Staff & Claims Lifecycle API](#1-staff--claims-lifecycle-api)
2. [Documents & Instant OCR API](#2-documents--instant-ocr-api)
3. [Verification & Anomaly Engine API](#3-verification--anomaly-engine-api)
4. [Manager Review & Approval API](#4-manager-review--approval-api)
5. [Finance Review & Payment Clearing API](#5-finance-review--payment-clearing-api)
6. [Payment Processing API](#6-payment-processing-api)
7. [User Management API](#7-user-management-api)
8. [Health & Diagnostics API](#8-health--diagnostics-api)

---

## 1. Staff & Claims Lifecycle API

### 1.1 List Claims
- **Method & Path**: `GET /api/v1/claims`
- **Query Parameters**:
  - `status` (*optional string*): Filter by status (`DRAFT`, `SUBMITTED`, `UNDER_REVIEW`, `FLAGGED`, `APPROVED`, `MANAGER_CONFIRMED`, `READY_FOR_PAYMENT`, `PAID`, `REJECTED`, `CANCELLED`).
  - `employee_id` (*optional UUID*): Filter by employee user ID.
  - `manager_id` (*optional UUID*): Filter by manager user ID.
  - `finance_status` (*optional string*): `FINANCE_PENDING`, `FINANCE_CLEARED`, `FINANCE_REJECTED`, `FINANCE_EXCEPTION`.
  - `limit` (*default 50, max 200*).
  - `offset` (*default 0*).
- **Response** `200 OK`:
```json
{
  "total": 12,
  "claims": [
    {
      "id": "c39a0614-fa5f-4a30-80a5-f860e0a53cb3",
      "claim_ref": "CLM-1031",
      "employee_id": "4b987739-6880-4e65-a3c7-031bf7a59139",
      "manager_id": "28ac25ae-735f-4085-a6ed-c765be651ef1",
      "merchant_name": "Uber",
      "amount": 840.0,
      "currency": "INR",
      "category": "Travel",
      "expense_date": "2026-09-10",
      "description": "Cab to client site",
      "status": "SUBMITTED",
      "verification_status": "CLEAN",
      "finance_status": null,
      "created_at": "2026-09-10T09:10:00Z",
      "submitted_at": "2026-09-10T09:15:00Z"
    }
  ]
}
```

### 1.2 Create Draft Claim
- **Method & Path**: `POST /api/v1/claims`
- **Status Code**: `201 Created`
- **Request Body**:
```json
{
  "employee_id": "4b987739-6880-4e65-a3c7-031bf7a59139",
  "manager_id": "28ac25ae-735f-4085-a6ed-c765be651ef1",
  "claim_ref": "CLM-48291", 
  "merchant_name": "Uber",
  "amount": 840.0,
  "currency": "INR",
  "category": "Travel",
  "expense_date": "2026-09-10",
  "description": "Cab to client site"
}
```
*(Note: `claim_ref` is auto-generated uniquely if omitted)*.

### 1.3 Get Claim Detail
- **Method & Path**: `GET /api/v1/claims/{claim_id}`
- **Path Param**: `claim_id` can be either the **UUID** (`c39a0614-...`) OR human-readable `claim_ref` (`CLM-1031`).
- **Response** `200 OK`: Returns full claim detail object, including `status_history`, `documents`, and `line_items`.

### 1.4 Update Draft Claim
- **Method & Path**: `PUT /api/v1/claims/{claim_id}`
- **Restrictions**: Allowed ONLY when claim is in `DRAFT` status.
- **Request Body**: Subset of fields to update (`merchant_name`, `amount`, `category`, `expense_date`, `description`, etc.).

### 1.5 Delete Draft Claim
- **Method & Path**: `DELETE /api/v1/claims/{claim_id}`
- **Restrictions**: Allowed ONLY when claim is in `DRAFT` status.

### 1.6 Submit Claim
- **Method & Path**: `POST /api/v1/claims/{claim_id}/submit`
- **Description**: Transitions claim `DRAFT` → `SUBMITTED` (or triggers verification pipeline).
- **Request Body** (*optional*):
```json
{
  "comment": "Submitting quarterly business travel claim",
  "actor_name": "Vickey Kumar"
}
```
- **Response** `200 OK`:
```json
{
  "claim_id": "c39a0614-fa5f-4a30-80a5-f860e0a53cb3",
  "claim_ref": "CLM-1031",
  "status": "SUBMITTED",
  "submitted_at": "2026-09-12T11:00:00Z",
  "message": "Claim submitted successfully and forwarded to manager review"
}
```

### 1.7 Get Claim Status History
- **Method & Path**: `GET /api/v1/claims/{claim_id}/history`
- **Response** `200 OK`: List of lifecycle transitions:
```json
[
  {
    "id": "hist-001",
    "from_status": "DRAFT",
    "to_status": "SUBMITTED",
    "event_label": "Claim submitted",
    "comment": "Submitting receipt",
    "occurred_at": "2026-09-12T11:00:00Z"
  }
]
```

---

## 2. Documents & Instant OCR API

### 2.1 Instant OCR Receipt Analysis (Pre-submit / Form Autofill)
- **Method & Path**: `POST /api/v1/documents/analyze`
- **Content-Type**: `multipart/form-data`
- **Form Body**: `file`: Binary file (PDF, PNG, JPG, WEBP - max 10MB).
- **Description**: Runs Gemini Vision extraction in-memory and returns structured expense fields to auto-populate the frontend form.
- **Response** `200 OK`:
```json
{
  "merchant": "Uber India Systems Pvt Ltd",
  "amount": 840.0,
  "date": "2026-09-10",
  "currency": "INR",
  "category": "Travel",
  "description": "Expense at Uber India Systems Pvt Ltd (Invoice #CRN-9842)",
  "invoice_number": "CRN-9842",
  "confidence_scores": {
    "merchant": 0.98,
    "total": 0.99,
    "transaction_date": 0.95
  },
  "line_items": [
    {
      "description": "Uber Premier trip fare",
      "amount": 840.0,
      "quantity": 1
    }
  ],
  "warnings": []
}
```

### 2.2 Upload & Streamlined Auto-Verify
- **Method & Path**: `POST /api/v1/claims/{claim_id}/documents/upload-and-verify`
- **Content-Type**: `multipart/form-data`
- **Form Body**: `file`: Binary receipt file.
- **Description**: Uploads to Supabase Storage, extracts via OCR, validates, and runs duplicate verification in a single atomic pass.

### 2.3 Upload Receipt Document
- **Method & Path**: `POST /api/v1/claims/{claim_id}/documents`
- **Query Param**: `auto_verify=true|false`
- **Form Body**: `file`: Binary receipt file.

### 2.4 Trigger Standalone OCR Processing
- **Method & Path**: `POST /api/v1/claims/{claim_id}/documents/{document_id}/process`
- **Query Param**: `force=true|false` (force re-extraction if already completed).

### 2.5 Get Extracted OCR Data
- **Method & Path**: `GET /api/v1/claims/{claim_id}/documents/{document_id}/extracted`

---

## 3. Verification & Anomaly Engine API

### 3.1 Run Verification Engine
- **Method & Path**: `POST /api/v1/verification/claims/{claim_id}/run`
- **Description**: Compares the claim against all historical claims using fuzzy matching (merchant text), amount tolerances (exact / ±5%), and date windows (±7 days / ±30 days). Evaluates duplicate risk score and triggers Gemini forensic analysis for borderline cases.
- **Response** `200 OK`:
```json
{
  "claim_id": "c39a0614-fa5f-4a30-80a5-f860e0a53cb3",
  "verification_status": "FLAGGED",
  "risk_score": 0.88,
  "is_duplicate": true,
  "explanation": "High similarity (88%) to historical claim CLM-1021 with identical invoice #CRN-9842.",
  "all_candidates": [
    {
      "claim_id": "uuid-previous-claim",
      "claim_ref": "CLM-1021",
      "merchant_name": "Uber",
      "amount": 840.0,
      "similarity_score": 0.92,
      "match_reasons": ["Identical invoice number", "Exact amount match"]
    }
  ]
}
```

### 3.2 Get Latest Verification Result
- **Method & Path**: `GET /api/v1/verification/claims/{claim_id}`

---

## 4. Manager Review & Approval API

### 4.1 Manager Claims Queue & History
- **Method & Path**: `GET /api/v1/manager/claims`
- **Query Parameters**:
  - `manager_id` (*optional UUID*): Filter claims assigned to this manager.
  - `status` (*optional string*): 
    - Omit or pass `"ALL"` to fetch all active team claims across all statuses (`SUBMITTED`, `UNDER_REVIEW`, `FLAGGED`, `APPROVED`, `MANAGER_CONFIRMED`, `READY_FOR_PAYMENT`, `PAID`, `REJECTED`).
    - Pass `"PENDING"` for reviewable claims (`SUBMITTED`, `UNDER_REVIEW`, `FLAGGED`).
    - Pass `"APPROVED"` for approved/confirmed/cleared claims.
    - Pass `"REJECTED"` for rejected claims.
- **Response** `200 OK`: Returns claims enriched with employee profile, AI risk score, duplicate risk percentage, and manager comments.

### 4.2 Get Manager Claim Review Dossier
- **Method & Path**: `GET /api/v1/manager/claims/{claim_id}`
- **Description**: Comprehensive dossier including employee profile, receipt images, OCR extraction, Gemini forensic reasoning, candidate duplicates, and permitted action buttons (`APPROVE`, `CONFIRM_CONTEXT`, `REJECT`).

### 4.3 Manager Approves Clean Claim
- **Method & Path**: `POST /api/v1/manager/claims/{claim_id}/approve`
- **Rules**:
  - Direct approval is **BLOCKED** if claim is `FLAGGED` (manager must use `/confirm` instead).
  - Self-approval is **BLOCKED** (manager cannot approve their own claim).
  - Transitions claim: `SUBMITTED` / `UNDER_REVIEW` → `READY_FOR_PAYMENT`.
- **Request Body**:
```json
{
  "manager_id": "28ac25ae-735f-4085-a6ed-c765be651ef1",
  "comment": "Approved - genuine business travel."
}
```

### 4.4 Manager Confirms Business Context (Flagged Claims)
- **Method & Path**: `POST /api/v1/manager/claims/{claim_id}/confirm`
- **Rules**:
  - Requires justification comment explaining why the duplicate/flagged expense is legitimate (e.g., separate legs of the same conference trip).
  - Transitions claim: `FLAGGED` → `MANAGER_CONFIRMED` (forwarded to Finance queue).
- **Request Body**:
```json
{
  "manager_id": "28ac25ae-735f-4085-a6ed-c765be651ef1",
  "comment": "Verified with employee: round-trip cab fare booked separately on the same date."
}
```

### 4.5 Manager Rejects Claim
- **Method & Path**: `POST /api/v1/manager/claims/{claim_id}/reject`
- **Rules**: Requires rejection comment. Transitions claim → `REJECTED`.
- **Request Body**:
```json
{
  "manager_id": "28ac25ae-735f-4085-a6ed-c765be651ef1",
  "comment": "Duplicate claim already reimbursed last month."
}
```

---

## 5. Finance Review & Payment Clearing API

### 5.1 Finance Queue
- **Method & Path**: `GET /api/v1/finance/claims`
- **Query Parameter**: `finance_status` (`FINANCE_PENDING`, `FINANCE_CLEARED`, `FINANCE_REJECTED`, `FINANCE_EXCEPTION`).
- **Description**: Lists all claims in `APPROVED`, `MANAGER_CONFIRMED`, or `READY_FOR_PAYMENT`. Enriched with manager review comments and AI forensic findings.

### 5.2 Finance Claim Review Dossier
- **Method & Path**: `GET /api/v1/finance/claims/{claim_id}`
- **Description**: Complete financial audit dossier including employee bank details, manager justification, matched historical claims, and OCR receipts.

### 5.3 Finance Clears Anomaly
- **Method & Path**: `POST /api/v1/finance/claims/{claim_id}/clear`
- **Rules**: Applicable to `MANAGER_CONFIRMED` or `APPROVED` claims. Transitions claim to `READY_FOR_PAYMENT` with `finance_status="FINANCE_CLEARED"`.
- **Request Body**:
```json
{
  "finance_user_id": "usr-fin-001",
  "comment": "Manager justification reviewed and approved for disbursement."
}
```

### 5.4 Finance Rejects Claim
- **Method & Path**: `POST /api/v1/finance/claims/{claim_id}/reject`
- **Request Body**:
```json
{
  "finance_user_id": "usr-fin-001",
  "reason": "Tax invoice missing valid GSTIN and corporate billing entity name."
}
```

### 5.5 Finance Executes Direct Payment
- **Method & Path**: `POST /api/v1/finance/claims/{claim_id}/pay`
- **Rules**: Claim must be `READY_FOR_PAYMENT`. Transitions claim → `PAID` (terminal state).
- **Request Body**:
```json
{
  "finance_user_id": "usr-fin-001",
  "payment_reference": "TXN-UPI-98241029",
  "notes": "Processed via HDFC Corporate Banking"
}
```

---

## 6. Payment Processing API

### 6.1 List Payments
- **Method & Path**: `GET /api/v1/payments`
- **Query Parameters**: `limit`, `offset`.

### 6.2 Get Payment Details
- **Method & Path**: `GET /api/v1/payments/{payment_id}`

### 6.3 Create Payment Record
- **Method & Path**: `POST /api/v1/payments`
- **Request Body**:
```json
{
  "claim_id": "c39a0614-fa5f-4a30-80a5-f860e0a53cb3",
  "processed_by": "usr-fin-001",
  "payment_reference": "TXN-882193",
  "notes": "Automated NEFT transfer"
}
```

---

## 7. User Management API

### 7.1 List Users
- **Method & Path**: `GET /api/v1/users`
- **Query Parameters**: `role` (`STAFF`, `MANAGER`, `FINANCE`, `ADMIN`), `is_active`, `email`, `external_id`.

### 7.2 Get User by Identifier
- **Method & Path**: `GET /api/v1/users/{identifier}`
- **Path Parameter**: Supports **UUID** (`4b987739-...`), **external_id** (`usr-001`), or **email** (`vickey.kumar@company.com`).

### 7.3 List Claims for a Specific User
- **Method & Path**: `GET /api/v1/users/{identifier}/claims`
- **Path Parameter**: UUID, external_id (`usr-001`), or email.
- **Query Parameter**: `status` (optional filter).

---

## 8. Health & Diagnostics API

### 8.1 API Liveness Check
- **Method & Path**: `GET /api/v1/health`
- **Response**: `{"status": "ok", "timestamp": "...", "version": "1.0.0"}`

### 8.2 Database Connectivity Check
- **Method & Path**: `GET /api/v1/health/db`
- **Response**: `{"status": "ok", "database": "connected", "latency_ms": 12.4}`
