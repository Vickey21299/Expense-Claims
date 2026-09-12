# 📘 Product Specification & Business Rules Guide (`product.md`)

> **Context & Purpose**: This document is the single authoritative product specification, business rules guide, financial threshold reference, and lifecycle policy document for the **AI-Powered Expense Claim & Forensic Duplicate Detection System**. 
> Use this high-density guide for instant project context, business logic, constraints, and decision rules with minimal token consumption.

---

## 1. 🎯 Product Mission & Overview

### What It Is
An enterprise-grade, multi-tier corporate expense reimbursement and automated forensic fraud-prevention system. It streamlines employee out-of-pocket claims, eliminates duplicate reimbursements, and enforces strict organizational compliance between employees, managers, and finance teams.

### Core Value Drivers
1. **Frictionless Submission**: Gemini Vision AI extracts receipts (PDF/images) into line items in seconds.
2. **Forensic Duplicate Prevention**: Multi-signal similarity checks (file hash, merchant name distance, invoice number, exact date proximity, amount variance) and Gemini LLM forensic reasoning flag repeat submissions before money moves.
3. **True Separation of Duties**: 
   - **Managers** evaluate **business legitimacy** ("Did this business travel/dinner actually happen?").
   - **Finance** evaluates **organizational integrity** ("Has this invoice already been paid elsewhere in the company?").
4. **Terminal Payment Settlement**: Enforces absolute guardrails preventing double payouts or editing paid claims.
5. **Real-Time SLA & Audit Trail**: Every status change, review comment, and turnaround time delta is permanently recorded in an immutable ledger.

---

## 2. 💰 Financial Limits, Thresholds & Policy Rules

| Rule / Threshold | Value / Constraint | Enforcement Level | Description & Rationale |
| :--- | :--- | :--- | :--- |
| **Minimum Claim Amount** | **₹1.00** | System Enforced | Claims cannot be ₹0 or negative. |
| **Maximum Per-Claim Limit** | **₹10,000** | Policy Guardrail | Standard ceiling for regular staff expense claims. Claims above ₹10,000 are flagged as policy exceptions requiring director escalation. |
| **Audit & Tax Threshold** | **₹5,000** | Finance Mandate | Any claim exceeding ₹5,000 requires verified GST/Tax identification and detailed line-item matching before Finance clearance. |
| **Receipt Requirement** | **Mandatory** | System Enforced | A valid receipt (PDF, PNG, JPG, WEBP) is strictly required for claim submission. No receipt = No reimbursement. |
| **Receipt Stale Limit** | **90 Days** | Engine Check | Receipts older than 90 days from current date are flagged as `STALE_RECEIPT` for manager review. |
| **Supported Currencies** | **INR (`₹`) Default** | Multi-currency supported | Base currency is INR. Multi-currency conversions are normalized to INR base. |
| **Max File Upload Size** | **10 MB** | System Enforced | Receipts exceeding 10MB are rejected by the upload validator. |
| **Accepted File Formats** | **PDF, PNG, JPEG, WEBP** | System Enforced | Non-receipt files (executables, archives, documents) return HTTP 415 / 400. |

---

## 3. 👥 User Roles & Segregation of Duties

```
               ┌────────────────┐
               │ Staff Employee │ (Submits Claim + Receipt)
               └───────┬────────┘
                       │
             [Verification Engine]
             ┌─────────┴─────────┐
             │                   │
      (Clean Path)        (Flagged Path)
             │                   │
             ▼                   ▼
    ┌────────────────┐  ┌────────────────┐
    │ Manager Review │  │ Manager Review │
    │   (Approve)    │  │(Confirm Context)
    └────────┬───────┘  └────────┬───────┘
             │                   │
             │                   ▼
             │          ┌────────────────┐
             │          │ Finance Review │
             │          │(Clear Anomaly) │
             │          └────────┬───────┘
             │                   │
             └─────────┬─────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │ READY_FOR_PAYMENT   │
            └──────────┬──────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   Finance Payout    │ ──► [PAID (Terminal)]
            └─────────────────────┘
```

### 1. Staff (Employee) — e.g., `Vickey Kumar (usr-001)`
- **Capabilities**: Create drafts, upload receipts, review auto-extracted fields, submit claims, view personal claims and audit timelines.
- **Restrictions**: 
  - Cannot approve or review own claims.
  - Cannot change claim status once submitted.
  - Cannot modify payment details or references.

### 2. Approving Manager — e.g., `Rahul Sharma (usr-mgr-001)`
- **Capabilities**: Review direct reports' claims, inspect OCR items, view duplicate flags and AI forensic evidence, approve clean claims, confirm business context on flagged claims, or reject claims with mandatory comment.
- **Core Responsibility**: Answering *"Is this expense necessary, authentic, and incurred for legitimate business activities?"*
- **Restrictions**:
  - **Self-Approval Blocked**: Cannot approve own claims (routes to next hierarchy level or Finance).
  - Cannot alter financial payout amounts or payment bank references.

### 3. Financial Controller — e.g., `Anita Joshi (usr-fin-001)`
- **Capabilities**: View all organization-wide claims, audit flagged exceptions, clear duplicate anomalies with mandatory audit comments, reject fraudulent claims, disburse simulated bank/UPI payouts, inspect department budget reports.
- **Core Responsibility**: Answering *"Has this invoice ever been paid before across any employee, department, or time period?"* and managing company disbursements.
- **Restrictions**:
  - Cannot bypass manager approval on clean claims (manager must approve first).
  - Cannot pay claims unless they reach `READY_FOR_PAYMENT`.

---

## 4. 🔄 End-to-End Lifecycle & State Machine

### Official Claim Statuses (`ClaimStatus`)
1. `DRAFT`: Claim initiated; receipt uploaded; editable by employee.
2. `SUBMITTED`: Submitted by employee; OCR finalized; deterministic & AI verification executed.
3. `UNDER_REVIEW`: Manager has opened and is reviewing the claim.
4. `FLAGGED`: Automated verification engine detected duplicate similarity score >= 40% or rule violation.
5. `MANAGER_CONFIRMED`: Manager validated the business context for a flagged claim and forwarded to Finance.
6. `APPROVED`: Manager approved a clean claim (automatically eligible for payment queue).
7. `READY_FOR_PAYMENT`: Cleared by Finance (or clean-approved by Manager); ready for disbursement.
8. `PAID`: **Terminal State**. Funds disbursed; transaction reference logged. **No further actions permitted.**
9. `REJECTED`: Rejected by Manager or Finance with documented reason.

### Allowed State Transitions
```
DRAFT              ──► SUBMITTED
SUBMITTED          ──► UNDER_REVIEW, APPROVED, FLAGGED, REJECTED
UNDER_REVIEW       ──► APPROVED, FLAGGED, REJECTED
FLAGGED            ──► MANAGER_CONFIRMED, REJECTED
MANAGER_CONFIRMED  ──► READY_FOR_PAYMENT, REJECTED
APPROVED           ──► READY_FOR_PAYMENT, REJECTED
READY_FOR_PAYMENT  ──► PAID, REJECTED
PAID               ──► [TERMINAL — NO TRANSITIONS ALLOWED]
REJECTED           ──► [TERMINAL]
```

---

## 5. 🤖 AI Verification & Forensic Engine Rules

The verification engine operates on a cost- and speed-optimized tiered model:

```
Incoming Claim ──► Tier 1: Candidate Retrieval (Fast DB Index Query)
                           │
                           ▼
                  Tier 2: Deterministic Similarity Scoring
                           ├─ Exact File Hash (SHA-256)
                           ├─ Merchant Distance (Levenshtein & Trigrams)
                           ├─ Date Delta (Within 0 - 30 days)
                           ├─ Amount Delta (Exact or partial match)
                           └─ Invoice Number Exact Match
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
    Score < 40% (Clean)          Score >= 40% (Borderline / Flagged)
             │                           │
      [Status: CLEAN]             Tier 3: Gemini Forensic Analysis
                                         │
                                  Produces:
                                  • Duplicate Risk %
                                  • Risk Classification (LOW/MED/HIGH)
                                  • AI Reasoning Explanation
                                  • Actionable Manager Recommendation
```

### Forensic Risk Classifications
- **LOW RISK (0% – 39%)**: Claim proceeds on the **Clean Path** directly to the Manager for standard approval.
- **MEDIUM RISK (40% – 69%)**: Borderline similarity (e.g., same merchant & amount, different date). Claim marked `FLAGGED`. Requires Manager context confirmation + Finance anomaly clearance.
- **HIGH RISK (70% – 100%)**: Strong duplicate signal (e.g., exact receipt hash match, identical invoice number). Claim marked `FLAGGED`. Prominently alerts Manager and Finance with side-by-side evidence.

---

## 6. 💳 Payment Disbursal & Settlement Rules

- **Provider**: Handled by `PaymentService` via extensible `MockPaymentProvider` (simulates instant UPI / NEFT bank settlement).
- **Payment Reference Format**: Unique deterministic transaction code:
  `TXN-PAY-{YYYYMMDD}-{HEX6}` (e.g., `TXN-PAY-20260912-9A8C1E`).
- **Conflict Guardrails**:
  - Attempting to pay an already `PAID` claim returns `HTTP 409 Conflict` (`"PAID is a terminal state"`).
  - Attempting to pay an unapproved claim (`SUBMITTED`, `FLAGGED`, `DRAFT`) returns `HTTP 409 Conflict`.
  - Payment execution atomically inserts record into `payments` table and writes audit log to `claim_status_history`.

---

## 7. ⏱️ SLA, Audit Trail & Comment Rules

1. **Manager Justification**:
   - Required when confirming a `FLAGGED` claim (`confirmClaimContext`).
   - Recorded in `manager_reviews` and `claim_status_history`.
   - Displayed as a stylized quote card in Staff and Finance views.
2. **Finance Clearance / Rejection Reason**:
   - Mandatory reason required for any rejection (`rejectClaim`).
   - Clearance notes required for clearing exceptions (`clearFinancialException`).
3. **Turnaround (SLA) Tracking**:
   - System tracks exact delta timestamps between milestones (`+27s` OCR to Verification, `+1h 45m` Submission to Manager Review, `+3h 10m` Approval to Payout).
   - Displayed on the UI with total cycle turnaround pill (e.g., `⚡ Turnaround: 2h 15m`).

---

## 8. 📐 Core Assumptions & Architectural Decisions

1. **Storage**: Receipt files are uploaded to the Supabase Storage bucket `receipts`. The system stores the public/signed URL, file hash, and MIME type.
2. **Database Integrity**: All critical business rules (self-approval prevention, terminal state enforcement, status transition validity) are enforced at the **backend API and PostgreSQL layer**, never relying solely on frontend UI checks.
3. **Seeded Test Environment**:
   - Staff Submitter: `Vickey Kumar` (`usr-001` / `vickey.kumar@company.com`)
   - Approving Manager: `Rahul Sharma` (`usr-mgr-001` / `rahul.sharma@company.com`)
   - Finance Controller: `Anita Joshi` (`usr-fin-001` / `anita.joshi@company.com`)
4. **Offline Resilience**: The system operates with robust fallback mechanisms; if Gemini OCR Vision experiences network timeouts, users can manually verify or input line items.

---

## 9. ⚡ Quick Reference Matrix for AI & Developers

| Topic | Quick Answer / Reference |
| :--- | :--- |
| **Claim Ref Format** | `CLM-XXXXX` (e.g., `CLM-01247`) |
| **Payment Ref Format** | `TXN-PAY-YYYYMMDD-XXXXXX` (e.g., `TXN-PAY-20260912-A1B2C3`) |
| **Max Claim Amount** | ₹10,000 |
| **Tax Audit Threshold** | ₹5,000 |
| **Receipt Max Size** | 10 MB |
| **Allowed File Types** | `application/pdf`, `image/png`, `image/jpeg`, `image/webp` |
| **OCR Model** | Google Gemini 2.5 Flash / Pro (`gemini-2.5-flash`) |
| **Staff Claim Route** | `GET /api/v1/users/{email}/claims` |
| **Manager Queue Route** | `GET /api/v1/manager/claims?manager_id={uuid}` |
| **Finance Queue Route** | `GET /api/v1/finance/claims` |
| **Terminal State** | `PAID` (cannot be changed or deleted) |
