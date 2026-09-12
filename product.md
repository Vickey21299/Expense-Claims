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

---

## 10. 🚀 Future Work & Scalability Roadmap (Scaling from 1 to 100,000+ Users)

To transition this system from an initial pilot/prototype to a battle-tested, enterprise-grade production platform serving 100,000+ concurrent employees, managers, and finance teams, the following multi-pillar roadmap will be executed in upcoming phases:

### 1. 🔍 Production-Grade Code Quality & Security Hardening
- **Static Analysis & Strict Typing**: Enforce strict Python typing (`mypy --strict`), Ruff linter, and formatting pipelines to eliminate edge-case runtime type errors.
- **Security Audits & OWASP Top 10**: 
  - Sanitize all file uploads with anti-virus scanners (ClamAV) before Supabase storage.
  - Implement MIME sniffing verification (magic bytes check) to prevent malicious executable masquerading as PNG/PDF.
  - SQL injection prevention via parameterized SQLAlchemy queries and Pydantic v2 input validation models.
- **Robust Exception Handling & Resilient Retries**:
  - Implement exponential backoff and circuit breakers (via `tenacity`) for external services (Google Gemini API, Supabase, Payment webhooks).

### 2. 📊 Observability, Telemetry & Grafana Monitoring
- **Prometheus & Grafana Dashboards**:
  - Export system metrics: HTTP request latency (p50, p95, p99), requests per second (RPS), error rate (4xx/5xx), and database connection pool saturation.
  - Track domain-specific KPIs: OCR processing latency, duplicate detection rate, Gemini token consumption per hour, and approval SLA turnaround times.
- **Distributed Tracing (OpenTelemetry)**: Trace end-to-end user transactions across Frontend ➔ FastAPI ➔ Supabase ➔ Gemini API to pinpoint microsecond bottlenecks.
- **Error Tracking & Alerting**: Real-time error monitoring with Sentry or Datadog, with PagerDuty alerts on elevated error spikes or failed payment disbursements.

### 3. ⚡ High-Concurrency Architecture & Scaling to 100,000+ Users
- **Asynchronous Processing Pipeline**:
  - Offload heavy operations (Gemini Vision OCR extraction, multi-signal candidate similarity scoring, PDF export generation) to an asynchronous worker queue (Celery or ARQ backed by Redis / RabbitMQ).
  - Web requests return an instant HTTP 202 Accepted with a job ID, allowing the UI to poll or receive updates via WebSockets/SSE.
- **Database Scaling & Connection Pooling**:
  - Deploy **PgBouncer** / Supabase Supavisor connection pooling to support tens of thousands of active client connections without exhausting database socket limits.
  - Configure PostgreSQL **Read Replicas** to separate heavy analytical queries (Finance reports, category aggregations) from transactional writes (claim submissions, approvals).
  - Implement **Table Partitioning**: Partition `claims` and `claim_status_history` tables by fiscal year or month to maintain sub-10ms index seek performance across millions of rows.

### 4. 💰 FinOps & Cost Optimization
- **Gemini API Token Optimization**:
  - **Tiered Gating**: Never call Gemini LLM on clean claims; ensure Tier 1 & Tier 2 deterministic checks filter out 85%+ of duplicate-free claims at zero AI token cost.
  - **Exact Hash Cache**: If an identical receipt SHA-256 hash was analyzed previously, retrieve cached OCR extraction and forensic reasoning directly from Redis/Postgres without re-prompting Gemini.
  - **Model Sizing**: Utilize `gemini-2.5-flash` or `gemini-2.5-flash-lite` for high-throughput OCR and reserve high-reasoning models only for complex forensic edge cases.
- **Infrastructure Cost Controls**: Auto-scale container instances (AWS ECS Fargate / Kubernetes KEDA) based on CPU/memory and queue depth, scaling down to minimum capacity during off-peak hours.

### 5. 🛡️ Rate Limiting & Traffic Throttling
- **Multi-Tier Rate Limiting (`slowapi` / Redis Token Bucket)**:
  - **Per-IP Limits**: Max 100 requests/minute for unauthenticated endpoints to prevent DDoS and automated probing.
  - **Per-User Limits**: Max 20 receipt uploads per hour per employee to curb spam submissions and prevent storage quota exhaustion.
  - **AI Endpoint Throttling**: Strict burst and sustained concurrency caps on OCR and verification endpoints to prevent provider quota exhaustion and unexpected billing spikes.
- **DDoS Mitigation**: Place the application behind Cloudflare or AWS CloudFront with Web Application Firewall (WAF) rules and automated bot detection.

### 6. 🔐 Enterprise Authentication & Identity Access Management (IAM)
- **Production Auth Migration**: Replace seeded mock users with enterprise **OAuth 2.0 / OIDC / SAML 2.0** Single Sign-On (SSO) integrated with Google Workspace, Microsoft Entra ID (Azure AD), or Okta.
- **Stateless JWT Tokens**: Issue cryptographically signed, short-lived JWT access tokens with secure HTTP-only refresh cookies.
- **Granular RBAC & ABAC**: Attribute-Based Access Control enforcing organizational hierarchy (e.g., managers can only access claims belonging to their direct reporting tree).

### 7. 🧪 Automated Load & Stress Testing (1 to 100,000 Users)
- **Load Testing with Locust & k6**:
  - Design realistic load test scenarios simulating 1,000, 10,000, and 100,000 concurrent active users.
  - Test sustained throughput, burst spikes (e.g., month-end expense filing rush), and verify p99 API latency stays under 300ms for core workflows.
  - Chaos engineering tests to verify zero data loss during worker restarts or database failovers.

### 8. 🏦 Live Banking & Corporate ERP Integrations
- **Real Payment Gateways**: Connect `PaymentService` to production disbursement APIs (RazorpayX, Stripe Treasury, ICICI/HDFC Corporate Banking APIs) for instant real-time bank IMPS/NEFT transfers.
- **ERP Accounting Sync**: Bi-directional automated synchronization of settled expense entries with SAP, Oracle NetSuite, QuickBooks, or Xero for real-time ledger balancing.

