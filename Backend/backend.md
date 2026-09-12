# Backend Architecture & File Index Guide

> **Purpose**: This document serves as a high-density reference guide for developers and AI assistants. Use this index to identify **which files to read** and **which files are IRRELEVANT (DO NOT READ)** for specific tasks to save tokens and time.

---

## 🧭 Quick File Relevance Matrix

| File / Folder Path | Type & Role | Token Relevance for AI | Read When... |
| :--- | :--- | :--- | :--- |
| `main.py` | FastAPI Application Entry Point | 🟢 **CORE** | Checking middleware, CORS, lifespan, router registrations |
| `app/core/config.py` | Environment Settings & Pydantic Config | 🟢 **CORE** | Checking env vars (Supabase, Gemini API keys, ports) |
| `app/core/database.py` | Supabase Client Singleton | 🟢 **CORE** | Checking Supabase client initialization |
| `app/core/logging.py` | Structured Logging Utility | 🟡 **SUPPORT** | Checking logger formatting |
| `app/models/enums.py` | All System Enums & Allowed Transitions | 🟢 **CRITICAL** | Checking claim statuses, roles, review decisions |
| `app/models/claims.py` | Pydantic Schemas for Claims & Items | 🟢 **CRITICAL** | Working on Claim creation, listing, schemas |
| `app/models/documents.py`| Pydantic Schemas for OCR & Receipts | 🟢 **CRITICAL** | Working on Receipt uploads & OCR responses |
| `app/models/reviews.py` | Pydantic Schemas for Manager & Finance | 🟢 **CRITICAL** | Working on approvals, rejections, dossiers |
| `app/models/verification.py`| Pydantic Schemas for Verification & LLM | 🟢 **CRITICAL** | Working on anomaly detection & risk scoring |
| `app/models/payments.py` | Pydantic Schemas for Payments | 🟢 **CRITICAL** | Working on payout records & execution |
| `app/models/users.py` | Pydantic Schemas for User CRUD | 🟢 **CRITICAL** | Working on User profiles & auth |
| `app/routers/claims.py` | Staff & Claim Lifecycle Endpoints | 🟢 **CORE ROUTER** | Working on Staff claims, drafts, submit, history |
| `app/routers/documents.py` | Document Upload & OCR Endpoints | 🟢 **CORE ROUTER** | Working on instant OCR analyze, upload, extract |
| `app/routers/reviews.py` | Manager & Finance Endpoints | 🟢 **CORE ROUTER** | Working on Manager/Finance queues, dossiers, actions |
| `app/routers/verification.py`| Deterministic Verification Endpoints | 🟢 **CORE ROUTER** | Working on duplicate checks & verification runner |
| `app/routers/payments.py` | Payment Processing Endpoints | 🟢 **CORE ROUTER** | Working on finance payments & listing |
| `app/routers/users.py` | User Management Endpoints | 🟢 **CORE ROUTER** | Working on user lookups by email/external_id |
| `app/routers/health.py` | Health Check Endpoints | 🟡 **SUPPORT** | Checking backend & DB health status |
| `app/services/extraction.py` | Gemini Vision OCR Extractor | 🟢 **CORE SERVICE** | Working on Gemini prompt & OCR extraction logic |
| `app/services/normalization.py`| Receipt Field Normalization & Parsing | 🟢 **CORE SERVICE** | Working on currency, date, merchant parsing |
| `app/services/validation.py` | Deterministic Receipt Field Validation | 🟢 **CORE SERVICE** | Working on amount/date sanity rules |
| `app/services/ocr_pipeline.py`| Unified In-Memory Pipeline Coordinator | 🟢 **CORE SERVICE** | Working on upload-and-verify combined flow |
| `app/services/storage.py` | Supabase Storage File Handler | 🟢 **CORE SERVICE** | Working on file validation, mime types, checksums |
| `app/services/verification/*`| Verification Engine & Forensic Analysis | 🟢 **CORE SERVICE** | Working on candidate retrieval, similarity, LLM check |
| `app/services/payment/*` | Payment Service & Mock Gateway Provider | 🟢 **CORE SERVICE** | Working on transaction generation & payouts |
| `product.md` | Product Specs, Rules, Limits & Policy | 🟢 **CRITICAL** | Checking business rules, money caps, roles, SLAs |
| `db/migrations/*.sql` | SQL Schema Migrations | 🟡 **REFERENCE** | Only read if altering DB tables/enums |
| `db/database.md` | Schema & Entity Relationship Docs | 🟡 **REFERENCE** | High-level DB architecture reference |
| `scripts/*` | Standalone CLI Test Scripts | 🔴 **IRRELEVANT / DO NOT READ** | Do NOT read unless running local CLI debug tests |
| `tests/*` | Pytest Unit & Integration Test Suites | 🔴 **IRRELEVANT / DO NOT READ** | Do NOT read unless running/debugging automated pytest |
| `bill/*` | Sample Receipt Files (PDF/JPG/PNG) | 🔴 **IRRELEVANT / DO NOT READ** | Binary asset folder |
| `venv/`, `__pycache__/`, `.pytest_cache/` | Python Runtime & Cache Folders | 🔴 **IRRELEVANT / DO NOT READ** | Never read |

---

## 🏗️ Architectural Layer Overview

```
                          Frontend (React + Vite)
                                    │
                              HTTP / REST
                                    ▼
                     FastAPI Application (main.py)
   ┌────────────────────────────────┴──────────────────────────────┐
   │                                                               │
Routers:                                                           │
 ├─ claims.py ──────► (Staff lifecycle, Submit, History, Items)   │
 ├─ documents.py ───► (Receipt Upload, Instant OCR Analyze)        │
 ├─ reviews.py ─────► (Manager Review Queue, Finance Queue)       │
 ├─ verification.py ► (Run Deterministic Verification)            │
 ├─ payments.py ────► (Payment Processing & History)               │
 ├─ users.py ───────► (User Profiles & Lookups)                   │
 └─ health.py ──────► (Health Checks)                              │
   │                                                               │
Services:                                                          │
 ├─ storage.py ────────► Supabase Storage ("receipts" bucket)     │
 ├─ extraction.py ─────► Gemini 1.5/2.0 Flash Vision OCR           │
 ├─ normalization.py ──► Regex & Date/Currency Parsers            │
 ├─ validation.py ─────► Rule-based Receipt Validator             │
 ├─ ocr_pipeline.py ───► In-Memory Streamlined Coordinator         │
 ├─ verification/ ─────► Engine, Vector/Text Similarity, Rules, LLM│
 └─ payment/ ──────────► PaymentService & Mock Gateway Provider    │
                                    │
                                    ▼
                         Database (Supabase / Postgres)
```

---

## 📂 Detailed Folder Breakdown

### 1. `app/core/` (Core Setup)
- **`config.py`**: Reads `.env` using Pydantic Settings (`SUPABASE_URL`, `SUPABASE_KEY`, `GEMINI_API_KEY`, `CORS_ORIGINS`).
- **`database.py`**: Initializes the global `supabase: Client` instance used across routers and services.
- **`logging.py`**: Standardized JSON/console logger.

### 2. `app/models/` (Data Contracts)
- **`enums.py`**: Source of truth for `ClaimStatus`, `UserRole`, `DocumentType`, `OcrProcessingStatus`, `VerificationStatus`, `FinanceDecision`, `ALLOWED_TRANSITIONS`.
- **`claims.py`**: `ClaimCreate`, `ClaimUpdate`, `ClaimOut`, `ClaimListOut`, `ClaimDetailOut`, `ClaimSubmitResponse`.
- **`documents.py`**: `DocumentUploadResponse`, `ExtractedDataOut`, `DocumentDetailOut`, `UnifiedPipelineResponse`.
- **`reviews.py`**: `ManagerReviewCreate`, `ManagerConfirmContext`, `ManagerClaimDossierOut`, `FinanceClearAction`, `FinanceRejectAction`, `FinancePayAction`, `FinanceClaimDossierOut`.
- **`verification.py`**: `VerificationRunOut`, `CandidateMatch`, `LlmVerificationAnalysis`.
- **`payments.py`**: `PaymentCreate`, `PaymentOut`, `PaymentListOut`.
- **`users.py`**: `UserCreate`, `UserUpdate`, `UserOut`, `UserListOut`.

### 3. `app/routers/` (API Controllers)
- **`claims.py`**: Staff CRUD for claims, line items, status history tracking, and submission.
- **`documents.py`**:
  - `POST /documents/analyze`: Instant OCR for create-claim form (returns extracted merchant, amount, date, category).
  - `POST /claims/{id}/documents/upload-and-verify`: Streamlined single-pass receipt upload + OCR + verification.
- **`reviews.py`**:
  - Manager endpoints: Pending list, dossier with AI risk analysis, clean approval (`/approve`), flagged confirmation (`/confirm`), rejection (`/reject`).
  - Finance endpoints: Review queue, finance dossier with matched duplicates, clearing anomaly (`/clear`), finance rejection (`/reject`), finance payment trigger (`/pay`).
- **`verification.py`**: Manual or automated triggering of the multi-factor verification engine.
- **`payments.py`**: Payout record execution and listing.
- **`users.py`**: User lookup by UUID, email, or `external_id` (e.g. `usr-001`).
- **`health.py`**: Basic liveness and Supabase connectivity checks.

### 4. `app/services/` (Business Logic)
- **`storage.py`**: File type sniffing (magic bytes), 10MB limit enforcement, checksum computation, Supabase bucket uploads.
- **`extraction.py`**: Calls Gemini Vision with JSON prompt to extract merchant, invoice number, date, amounts, tax, items.
- **`normalization.py`**: Sanitizes merchant names, parses ISO dates, extracts float amounts and currency codes.
- **`validation.py`**: Checks extracted receipts for missing required fields, future dates, zero amounts, currency mismatches.
- **`ocr_pipeline.py`**: Orchestrates storage, extraction, normalization, validation, and auto-verification without disk writes.
- **`verification/`**:
  - `engine.py`: Orchestrates candidate search, scoring, and status transitions (`CLEAN` vs `FLAGGED`).
  - `retrieval.py`: Finds candidate claims by same user, same amount, or similar dates.
  - `similarity.py`: Jaro-Winkler, Levenshtein, amount delta, and date proximity scoring.
  - `llm_analysis.py`: Gemini second-opinion forensic analysis for borderline duplicate risks.
  - `rules.py`: Hard business constraints (e.g. claim age limit, amount thresholds).
- **`payment/`**:
  - `service.py`: Transitions claims to `PAID` and writes immutable audit records to `payments` table.
  - `provider.py`: Simulates banking gateway / UPI payment disbursement.

---

## 🚫 Safe Token Savings Guide: What NOT to Load

When asked to implement frontend or backend tasks:
1. **NEVER read `Backend/venv/` or `__pycache__/`**.
2. **NEVER read `Backend/scripts/`** during normal frontend or backend API coding. They are one-off test scripts.
3. **NEVER read `Backend/tests/`** unless you are specifically tasked with fixing or running `pytest`.
4. **NEVER read `Backend/db/migrations/`** unless you need to write a new SQL migration. Use `app/models/enums.py` and `database.md` for schema contracts.
5. **NEVER load sample binary files in `Backend/bill/`**.
