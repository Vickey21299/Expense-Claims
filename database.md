# Expense Claims System — Database Documentation

Comprehensive schema specification, entity-relationship diagrams, enum references, state lifecycles, indexes, and setup instructions for PostgreSQL on Supabase.

---

## 1. Architecture Overview

The database is built on **PostgreSQL (Supabase)** and follows a relational model with strict referential integrity:

- **Primary Keys:** UUID v4 generated via `uuid-ossp` (`uuid_generate_v4()`).
- **Timestamps:** ISO 8601 with timezone (`TIMESTAMPTZ`), automated `updated_at` triggers.
- **Audit Trails:** Immutable history tables (`claim_status_history`) for compliance.
- **Full-Text & Similarity Search:** Trigram index (`pg_trgm`) on merchant names.
- **Generated Columns:** `claim_items.total_amount` is computed automatically (`quantity * unit_price`).

---

## 2. Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    users ||--o{ users : "manages (manager_id)"
    users ||--o{ claims : "submits (employee_id)"
    users ||--o{ claims : "assigned to (manager_id)"
    users ||--o{ manager_reviews : "reviews (manager_id)"
    users ||--o{ finance_reviews : "clears/rejects (finance_user_id)"
    users ||--o{ payments : "processes (processed_by)"
    users ||--o{ duplicate_matches : "resolves (resolved_by)"
    users ||--o{ claim_status_history : "acts as (actor_id)"

    claims ||--o{ claim_documents : "contains (claim_id)"
    claims ||--o{ claim_items : "contains (claim_id)"
    claims ||--o{ verification_results : "undergoes (claim_id)"
    claims ||--o{ duplicate_matches : "matched against (claim_id)"
    claims ||--o{ duplicate_matches : "historical target (matched_claim_id)"
    claims ||--o{ claim_status_history : "tracks lifecycle (claim_id)"
    claims ||--o{ manager_reviews : "receives (claim_id)"
    claims ||--o{ finance_reviews : "receives (claim_id)"
    claims ||--o| payments : "settled by (claim_id)"

    %% OCR Pipeline & Verification Engine Extensions
    claim_documents ||--o{ claim_items : "extracted from (document_id)"
    claim_documents ||--o{ ocr_processing : "processed by (document_id)"
    claims ||--o{ claim_extracted_data : "has extracted (claim_id)"
    claim_documents ||--o{ claim_extracted_data : "extracted into (document_id)"
    ocr_processing ||--o{ claim_extracted_data : "generates (ocr_processing_id)"
    claims ||--o{ claim_verifications : "verified by (claim_id)"
    claims ||--o{ claim_verifications : "strongest match (strongest_match_claim_id)"

    users {
        UUID id PK
        TEXT external_id UK
        TEXT email UK
        TEXT full_name
        TEXT department
        user_role role
        TEXT job_title
        UUID manager_id FK
        BOOLEAN is_active
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    claims {
        UUID id PK
        TEXT claim_ref UK
        UUID employee_id FK
        UUID manager_id FK
        TEXT merchant
        TEXT claim_type
        NUMERIC amount
        CHAR currency
        DATE claim_date
        TEXT description
        claim_status status
        ocr_status ocr_status
        verification_status verification_status
        finance_decision finance_status
        TEXT payment_reference
        TIMESTAMPTZ submitted_at
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    claim_documents {
        UUID id PK
        UUID claim_id FK
        document_type document_type
        TEXT file_name
        TEXT file_url
        TEXT storage_path
        TEXT checksum
        BIGINT file_size_bytes
        TEXT mime_type
        TEXT ocr_raw_text
        NUMERIC ocr_confidence
        TIMESTAMPTZ ocr_processed_at
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    ocr_processing {
        UUID id PK
        UUID document_id FK
        TEXT status
        TEXT provider
        TEXT provider_request_id
        JSONB raw_response
        TEXT error_code
        TEXT error_message
        INT retry_count
        TIMESTAMPTZ started_at
        TIMESTAMPTZ completed_at
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    claim_extracted_data {
        UUID id PK
        UUID claim_id FK
        UUID document_id FK
        UUID ocr_processing_id FK
        TEXT merchant
        TEXT merchant_normalized
        TEXT invoice_number
        DATE transaction_date
        CHAR currency
        NUMERIC subtotal
        NUMERIC tax
        NUMERIC total
        JSONB line_items
        JSONB normalized_data
        JSONB confidence_scores
        JSONB validation_warnings
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }

    claim_verifications {
        UUID id PK
        UUID claim_id FK
        TEXT decision
        NUMERIC similarity_score
        UUID strongest_match_claim_id FK
        TEXT matched_claim_status
        INT matched_claim_age_days
        TIMESTAMPTZ wait_until
        JSONB field_scores
        JSONB triggered_rules
        JSONB evidence
        TEXT explanation
        TEXT engine_version
        TIMESTAMPTZ verified_at
        TIMESTAMPTZ created_at
    }

    claim_items {
        UUID id PK
        UUID claim_id FK
        UUID document_id FK
        TEXT description
        NUMERIC quantity
        NUMERIC unit_price
        NUMERIC total_amount "GENERATED"
        CHAR currency
        TEXT extracted_by
        NUMERIC confidence
        TIMESTAMPTZ created_at
    }

    verification_results {
        UUID id PK
        UUID claim_id FK
        TEXT check_name
        BOOLEAN passed
        TEXT message
        TEXT severity
        TIMESTAMPTZ checked_at
    }

    duplicate_matches {
        UUID id PK
        UUID claim_id FK
        UUID matched_claim_id FK
        NUMERIC similarity_score
        TEXT assessment
        JSONB signals
        TEXT detected_by
        BOOLEAN resolved
        UUID resolved_by FK
        TIMESTAMPTZ resolved_at
        TEXT resolution_note
        TIMESTAMPTZ detected_at
    }

    claim_status_history {
        UUID id PK
        UUID claim_id FK
        claim_status from_status
        claim_status to_status
        TEXT event_label
        TEXT comment
        UUID actor_id FK
        TEXT actor_name
        TIMESTAMPTZ occurred_at
    }

    manager_reviews {
        UUID id PK
        UUID claim_id FK
        UUID manager_id FK
        TEXT decision
        TEXT comment
        TIMESTAMPTZ reviewed_at
        TIMESTAMPTZ created_at
    }

    finance_reviews {
        UUID id PK
        UUID claim_id FK
        UUID finance_user_id FK
        finance_decision decision
        BOOLEAN cleared
        TEXT comment
        TIMESTAMPTZ reviewed_at
        TIMESTAMPTZ created_at
    }

    payments {
        UUID id PK
        UUID claim_id FK,UK
        TEXT payment_reference UK
        NUMERIC amount
        CHAR currency
        UUID processed_by FK
        TIMESTAMPTZ processed_at
        TEXT notes
        TIMESTAMPTZ created_at
        TIMESTAMPTZ updated_at
    }
```

---

## 3. Custom Enum & Domain Types

| Enum Name / Type | Allowed Values | Description |
|---|---|---|
| `user_role` | `'staff'`, `'manager'`, `'finance'` | System access & permission role |
| `claim_status` | `'DRAFT'`, `'SUBMITTED'`, `'UNDER_REVIEW'`, `'FLAGGED'`, `'MANAGER_CONFIRMED'`, `'APPROVED'`, `'REJECTED'`, `'READY_FOR_PAYMENT'`, `'PAID'` | Main lifecycle state machine status |
| `ocr_status` | `'PENDING'`, `'PROCESSING'`, `'COMPLETED'`, `'FAILED'`, `'SKIPPED'` | Receipt parsing status on claim |
| `ocr_pipeline_status` | `'PENDING'`, `'PROCESSING'`, `'EXTRACTED'`, `'NORMALIZED'`, `'COMPLETED'`, `'FAILED'` | Granular status in `ocr_processing` |
| `verification_status`| `'PENDING'`, `'CLEAN'`, `'FLAGGED'`, `'ERROR'` | Automated policy check outcome on claim |
| `verification_decision`| `'CLEAN'`, `'POTENTIAL_DUPLICATE'`, `'BORDERLINE'`, `'WAITING_FOR_EXISTING_CLAIM'`, `'ESCALATE_TO_MANAGER'` | Granular engine decision in `claim_verifications` |
| `document_type` | `'RECEIPT'`, `'INVOICE'`, `'BOARDING_PASS'`, `'OTHER'` | Attached file classification |
| `finance_decision` | `'FINANCE_PENDING'`, `'FINANCE_CLEARED'`, `'FINANCE_REJECTED'`, `'FINANCE_EXCEPTION'` | Finance verification state |

---

## 4. Claim Lifecycle & State Pipeline

### 4.1 Visual Lifecycle Flow

```mermaid
flowchart LR
    %% Pipeline Stages
    subgraph Stage1 ["1. Creation"]
        Draft["📝 DRAFT"]
    end

    subgraph Stage2 ["2. Submission & Verification Engine"]
        Submitted["📨 SUBMITTED"]
        Flagged["⚠️ FLAGGED"]
    end

    subgraph Stage3 ["3. Manager Review"]
        UnderReview["⏳ UNDER_REVIEW"]
        Approved["✅ APPROVED"]
        ManagerConfirmed["🛡️ MANAGER_CONFIRMED"]
    end

    subgraph Stage4 ["4. Finance Audit & Settlement"]
        Ready["🏦 READY_FOR_PAYMENT"]
        Paid["🎉 PAID<br/><i>(Terminal)</i>"]
    end

    subgraph Stage5 ["Terminal Exit"]
        Rejected["🚫 REJECTED<br/><i>(Terminal)</i>"]
    end

    %% Primary Progression Flow
    Draft -->|Employee Submits| Submitted
    Submitted -->|Clean Verification| UnderReview
    Submitted -->|Duplicate / Anomaly Detected| Flagged
    Submitted -->|Fast-Track Clean| Approved
    
    UnderReview -->|Manager Approves| Approved
    UnderReview -->|Flag Anomaly| Flagged
    
    Flagged -->|Manager Confirms Context| ManagerConfirmed
    ManagerConfirmed -->|Finance Clears Exception| Ready
    Approved -->|Queued for Payment| Ready
    Ready -->|Payment Settled| Paid

    %% Rejection Routes
    Submitted -.->|Reject| Rejected
    UnderReview -.->|Reject| Rejected
    Flagged -.->|Reject| Rejected
    ManagerConfirmed -.->|Finance Reject| Rejected
    Approved -.->|Finance Reject| Rejected
    Ready -.->|Reject| Rejected
```

### 4.2 State Transition Matrix

| Current State | Target State | Trigger / Action | Allowed Actor | Condition / Notes |
|---|---|---|---|---|
| — | **`DRAFT`** | Create claim draft | Staff | Claim initialized with receipts / items |
| **`DRAFT`** | **`SUBMITTED`** | Submit claim | Staff | All required fields & receipts attached |
| **`DRAFT`** | *Deleted* | Delete draft | Staff | Draft permanently deleted |
| **`SUBMITTED`** | **`UNDER_REVIEW`** | Open / start review | Manager | Manager begins evaluating claim |
| **`SUBMITTED`** | **`FLAGGED`** | Auto verification flag | Verification Engine | Similarity score >= 40% or duplicate detected |
| **`SUBMITTED`** | **`APPROVED`** | Fast-track clean approval | Manager | Direct approval without detailed queue |
| **`SUBMITTED`** | **`REJECTED`** | Reject claim | Manager | Reason required in review comment |
| **`UNDER_REVIEW`**| **`FLAGGED`** | Flag suspicious items | Manager | Duplicate match or policy exception found |
| **`UNDER_REVIEW`**| **`APPROVED`** | Approve clean claim | Manager | Moves clean claim to Payment Queue |
| **`UNDER_REVIEW`**| **`REJECTED`** | Reject claim | Manager | Rejection comment recorded in history |
| **`FLAGGED`** | **`MANAGER_CONFIRMED`**| Confirm business context | Manager | Manager provides required justification note |
| **`FLAGGED`** | **`REJECTED`** | Reject flagged claim | Manager | Confirmed duplicate or fraudulent |
| **`MANAGER_CONFIRMED`**| **`READY_FOR_PAYMENT`** | Finance clear anomaly | Finance | Clears financial exception with comment |
| **`MANAGER_CONFIRMED`**| **`REJECTED`** | Finance rejection | Finance | Financial exception rejected |
| **`APPROVED`** | **`READY_FOR_PAYMENT`** | Ready for payment queue | Manager / Finance | Clean claim queued for disbursement |
| **`APPROVED`** | **`REJECTED`** | Finance rejection | Finance | Non-compliant tax or missing compliance docs |
| **`READY_FOR_PAYMENT`** | **`PAID`** | Record disbursement | Finance | Payment reference generated (Terminal State) |
| **`READY_FOR_PAYMENT`** | **`REJECTED`** | Payment failure / cancel | Finance | Final audit rejection |

---

## 5. Table Specifications

### 5.1 `users`
Stores all staff members, managers, and finance team users. Supports hierarchical reporting via self-referencing `manager_id`.

| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY | `uuid_generate_v4()` | Unique user identifier |
| `external_id` | `TEXT` | UNIQUE | `NULL` | Legacy/seed reference (e.g. `usr-001`) |
| `email` | `TEXT` | NOT NULL, UNIQUE | — | Corporate email address |
| `full_name` | `TEXT` | NOT NULL | — | Full display name |
| `department` | `TEXT` | — | `NULL` | Department (e.g. Engineering, Sales) |
| `role` | `user_role`| NOT NULL | `'staff'` | User role: `staff`, `manager`, `finance` |
| `job_title` | `TEXT` | — | `NULL` | Designatory title |
| `manager_id` | `UUID` | REFERENCES `users(id)` | `NULL` | Direct manager UUID |
| `is_active` | `BOOLEAN` | NOT NULL | `TRUE` | Whether user account is active |
| `created_at` | `TIMESTAMPTZ`| NOT NULL | `NOW()` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ`| NOT NULL | `NOW()` | Auto-updated on record modification |

---

### 5.2 `claims`
The core expense claim entity.

| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY | `uuid_generate_v4()` | Unique claim ID |
| `claim_ref` | `TEXT` | UNIQUE | `NULL` | Human-readable ref code (e.g. `CLM-1031`) |
| `employee_id` | `UUID` | NOT NULL, REFERENCES `users(id)` | — | User who owns the claim |
| `manager_id` | `UUID` | REFERENCES `users(id)` | `NULL` | Assigned reviewing manager |
| `merchant` | `TEXT` | — | `NULL` | Vendor/Merchant name (e.g. Uber, Amazon) |
| `claim_type` | `TEXT` | NOT NULL | — | Category (Travel, Office Supplies, Meals, etc.) |
| `amount` | `NUMERIC(12,2)`| NOT NULL | `0` | Total claimed amount |
| `currency` | `CHAR(3)` | NOT NULL | `'INR'` | ISO currency code |
| `claim_date` | `DATE` | — | `NULL` | Date expense occurred |
| `description` | `TEXT` | — | `NULL` | Business justification |
| `status` | `claim_status`| NOT NULL | `'DRAFT'` | Main state machine status |
| `ocr_status` | `ocr_status`| NOT NULL | `'PENDING'` | OCR processing status |
| `verification_status`| `verification_status` | NOT NULL | `'PENDING'` | Automated validation status |
| `finance_status` | `finance_decision` | — | `NULL` | Finance review state |
| `payment_reference` | `TEXT` | — | `NULL` | Reference code after payout |
| `submitted_at` | `TIMESTAMPTZ`| — | `NULL` | Timestamp when user submitted |
| `created_at` | `TIMESTAMPTZ`| NOT NULL | `NOW()` | Initial draft creation |
| `updated_at` | `TIMESTAMPTZ`| NOT NULL | `NOW()` | Auto-updated timestamp |

---

### 5.3 `claim_documents`
Stores receipt and invoice attachments along with raw OCR extraction text and confidence score.

| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY | `uuid_generate_v4()` | Unique document ID |
| `claim_id` | `UUID` | NOT NULL, REFERENCES `claims(id)` ON DELETE CASCADE | — | Parent claim ID |
| `document_type` | `document_type` | NOT NULL | `'RECEIPT'` | `RECEIPT`, `INVOICE`, `BOARDING_PASS`, `OTHER` |
| `file_name` | `TEXT` | — | `NULL` | Original filename |
| `file_url` | `TEXT` | — | `NULL` | Storage public URL (Supabase Storage) |
| `storage_path` | `TEXT` | — | `NULL` | Supabase Storage path (`claims/{claim_id}/{doc_id}/{filename}`) |
| `checksum` | `TEXT` | — | `NULL` | SHA-256 hex digest for forensic deduplication |
| `file_size_bytes` | `BIGINT` | — | `NULL` | File size in bytes |
| `mime_type` | `TEXT` | — | `NULL` | e.g. `application/pdf`, `image/jpeg` |
| `ocr_raw_text` | `TEXT` | — | `NULL` | Raw unstructured text extracted by OCR |
| `ocr_confidence` | `NUMERIC(5,4)` | — | `NULL` | OCR confidence (0.0000 to 1.0000) |
| `ocr_processed_at` | `TIMESTAMPTZ` | — | `NULL` | Completion timestamp of OCR run |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Upload timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Auto-updated timestamp |

---

### 5.4 `claim_items`
Individual line items broken down from receipts.

| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY | `uuid_generate_v4()` | Unique line item ID |
| `claim_id` | `UUID` | NOT NULL, REFERENCES `claims(id)` ON DELETE CASCADE | — | Parent claim ID |
| `document_id` | `UUID` | REFERENCES `claim_documents(id)` ON DELETE SET NULL | `NULL` | Source document if extracted |
| `description` | `TEXT` | NOT NULL | — | Item description |
| `quantity` | `NUMERIC(10,3)` | NOT NULL | `1` | Quantity |
| `unit_price` | `NUMERIC(12,2)` | NOT NULL | `0` | Unit price |
| `total_amount` | `NUMERIC(12,2)` | **GENERATED ALWAYS AS (quantity * unit_price) STORED** | — | Automatic computed line total |
| `currency` | `CHAR(3)` | NOT NULL | `'INR'` | Currency code |
| `extracted_by` | `TEXT` | — | `'MANUAL'` | `OCR` or `MANUAL` |
| `confidence` | `NUMERIC(5,4)` | — | `NULL` | Extraction confidence score |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Record creation timestamp |

---

### 5.5 `verification_results`
Stores automated rule checks (e.g. weekend expense, duplicate check, policy threshold, receipt date matching).

| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY | `uuid_generate_v4()` | Result record ID |
| `claim_id` | `UUID` | NOT NULL, REFERENCES `claims(id)` ON DELETE CASCADE | — | Target claim ID |
| `check_name` | `TEXT` | NOT NULL | — | Rule name (e.g. `policy_limit`, `weekend_check`) |
| `passed` | `BOOLEAN` | NOT NULL | — | `true` if passed, `false` if flagged |
| `message` | `TEXT` | — | `NULL` | Human-readable explanation |
| `severity` | `TEXT` | NOT NULL | `'INFO'` | `INFO`, `WARNING`, or `ERROR` |
| `checked_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Execution timestamp |

---

### 5.6 `duplicate_matches`
Tracks suspected duplicate claims flagged by automated similarity detection.

| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY | `uuid_generate_v4()` | Unique record ID |
| `claim_id` | `UUID` | NOT NULL, REFERENCES `claims(id)` ON DELETE CASCADE | — | Current claim being analyzed |
| `matched_claim_id` | `UUID` | REFERENCES `claims(id)` ON DELETE SET NULL | `NULL` | Existing claim that matched |
| `similarity_score` | `NUMERIC(5,4)` | — | `NULL` | Match percentage (0.0 to 1.0) |
| `assessment` | `TEXT` | — | `NULL` | Assessment summary |
| `signals` | `JSONB` | NOT NULL | `'[]'::jsonb` | Array of signal tags (`["same_amount", "same_merchant"]`) |
| `detected_by` | `TEXT` | — | `'RULE'` | Detection engine (`RULE`, `AI`, `MANUAL`) |
| `resolved` | `BOOLEAN` | NOT NULL | `FALSE` | Has a reviewer resolved the match? |
| `resolved_by` | `UUID` | REFERENCES `users(id)` | `NULL` | Reviewer user UUID |
| `resolved_at` | `TIMESTAMPTZ` | — | `NULL` | Resolution timestamp |
| `resolution_note` | `TEXT` | — | `NULL` | Notes on why resolved as false/valid positive |
| `detected_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Detection timestamp |

---

### 5.7 `claim_status_history`
**Immutable Audit Trail** recording every status transition. Rows in this table must never be updated or deleted.

| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY | `uuid_generate_v4()` | Audit entry ID |
| `claim_id` | `UUID` | NOT NULL, REFERENCES `claims(id)` ON DELETE CASCADE | — | Target claim ID |
| `from_status` | `claim_status` | — | `NULL` | Previous status (`NULL` on creation) |
| `to_status` | `claim_status` | NOT NULL | — | New status |
| `event_label` | `TEXT` | NOT NULL | — | Event title (e.g. `Claim Submitted`, `Approved`) |
| `comment` | `TEXT` | — | `NULL` | Reason / note added by actor |
| `actor_id` | `UUID` | REFERENCES `users(id)` | `NULL` | User UUID who performed the action |
| `actor_name` | `TEXT` | — | `NULL` | Cached actor name |
| `occurred_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Transition timestamp |

---

### 5.8 `manager_reviews`
Records manager review rounds and decisions.

| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY | `uuid_generate_v4()` | Review record ID |
| `claim_id` | `UUID` | NOT NULL, REFERENCES `claims(id)` ON DELETE CASCADE | — | Reviewed claim ID |
| `manager_id` | `UUID` | NOT NULL, REFERENCES `users(id)` | — | Reviewing manager UUID |
| `decision` | `TEXT` | NOT NULL | — | Decision code (`APPROVED`, `REJECTED`, etc.) |
| `comment` | `TEXT` | — | `NULL` | Manager review notes |
| `reviewed_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Timestamp of review |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Record creation timestamp |

---

### 5.9 `finance_reviews`
Records finance verification decisions.

| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY | `uuid_generate_v4()` | Review record ID |
| `claim_id` | `UUID` | NOT NULL, REFERENCES `claims(id)` ON DELETE CASCADE | — | Target claim ID |
| `finance_user_id` | `UUID` | NOT NULL, REFERENCES `users(id)` | — | Finance officer UUID |
| `decision` | `finance_decision` | NOT NULL | — | `FINANCE_CLEARED`, `FINANCE_REJECTED`, etc. |
| `cleared` | `BOOLEAN` | NOT NULL | `FALSE` | `true` if approved for payment |
| `comment` | `TEXT` | — | `NULL` | Finance notes |
| `reviewed_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Decision timestamp |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Record creation timestamp |

---

### 5.10 `payments`
Terminal payment record created when a claim in `READY_FOR_PAYMENT` is settled. Exactly one payment per claim (`claim_id` UNIQUE).

| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY | `uuid_generate_v4()` | Unique payment ID |
| `claim_id` | `UUID` | NOT NULL, UNIQUE, REFERENCES `claims(id)` | — | Associated claim ID |
| `payment_reference` | `TEXT` | UNIQUE | `NULL` | Bank / UPI / wire transaction ref (e.g. `PAY-2026-0910-001`) |
| `amount` | `NUMERIC(12,2)` | NOT NULL | — | Paid amount |
| `currency` | `CHAR(3)` | NOT NULL | `'INR'` | Currency code |
| `processed_by` | `UUID` | REFERENCES `users(id)` | `NULL` | Finance user who released payment |
| `processed_at` | `TIMESTAMPTZ` | — | `NULL` | Execution timestamp |
| `notes` | `TEXT` | — | `NULL` | Settlement remarks / transfer note |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Record timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Auto-updated timestamp |

---

### 5.11 `ocr_processing`
Tracks asynchronous and synchronous OCR pipeline runs per document, maintaining retry counts and raw provider responses.

| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY | `uuid_generate_v4()` | OCR run identifier |
| `document_id` | `UUID` | NOT NULL, REFERENCES `claim_documents(id)` ON DELETE CASCADE | — | Target receipt document |
| `status` | `TEXT` | CHECK (`status IN ('PENDING','PROCESSING','EXTRACTED','NORMALIZED','COMPLETED','FAILED')`) | `'PENDING'` | Pipeline step status |
| `provider` | `TEXT` | NOT NULL | `'gemini'` | OCR provider / engine |
| `provider_request_id`| `TEXT` | — | `NULL` | Upstream API request ID |
| `raw_response` | `JSONB` | — | `NULL` | Unprocessed LLM / Vision payload |
| `error_code` | `TEXT` | — | `NULL` | Failure code if errored |
| `error_message` | `TEXT` | — | `NULL` | Descriptive error message |
| `retry_count` | `INT` | NOT NULL | `0` | Number of retries executed |
| `started_at` | `TIMESTAMPTZ` | — | `NULL` | Start timestamp of OCR call |
| `completed_at` | `TIMESTAMPTZ` | — | `NULL` | End timestamp of OCR call |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Record creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Auto-updated timestamp |

---

### 5.12 `claim_extracted_data`
Normalized receipt information extracted by OCR. Exactly one primary record per successful extraction run.

| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY | `uuid_generate_v4()` | Extracted record ID |
| `claim_id` | `UUID` | NOT NULL, REFERENCES `claims(id)` ON DELETE CASCADE | — | Associated claim ID |
| `document_id` | `UUID` | NOT NULL, REFERENCES `claim_documents(id)` ON DELETE CASCADE | — | Source document ID |
| `ocr_processing_id` | `UUID` | REFERENCES `ocr_processing(id)` ON DELETE SET NULL | `NULL` | Linked OCR run attempt |
| `merchant` | `TEXT` | — | `NULL` | Raw extracted merchant name |
| `merchant_normalized`| `TEXT` | — | `NULL` | Cleaned vendor name for similarity matching |
| `invoice_number` | `TEXT` | — | `NULL` | Extracted invoice / bill number |
| `transaction_date` | `DATE` | — | `NULL` | Extracted date of expense |
| `currency` | `CHAR(3)` | — | `NULL` | Extracted currency |
| `subtotal` | `NUMERIC(12,2)` | — | `NULL` | Net amount before tax |
| `tax` | `NUMERIC(12,2)` | — | `NULL` | Total tax / GST amount |
| `total` | `NUMERIC(12,2)` | — | `NULL` | Final gross amount |
| `line_items` | `JSONB` | NOT NULL | `'[]'::jsonb` | Extracted items array |
| `normalized_data` | `JSONB` | NOT NULL | `'{}'::jsonb` | Parsed structured fields |
| `confidence_scores` | `JSONB` | NOT NULL | `'{}'::jsonb` | Field-by-field OCR confidence |
| `validation_warnings`| `JSONB` | NOT NULL | `'[]'::jsonb` | Sanitization warnings |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Creation timestamp |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Auto-updated timestamp |

---

### 5.13 `claim_verifications`
Persists verification engine decisions, deterministic similarity metrics, triggered rules, and Gemini forensic audit evidence.

| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | PRIMARY KEY | `uuid_generate_v4()` | Verification run ID |
| `claim_id` | `UUID` | NOT NULL, REFERENCES `claims(id)` ON DELETE CASCADE | — | Target claim evaluated |
| `decision` | `TEXT` | CHECK (`decision IN ('CLEAN', 'POTENTIAL_DUPLICATE', 'BORDERLINE', 'WAITING_FOR_EXISTING_CLAIM', 'ESCALATE_TO_MANAGER')`) | — | Final verification outcome |
| `similarity_score` | `NUMERIC(5,4)` | NOT NULL | `0.0` | Maximum match score (0.0000 - 1.0000) |
| `strongest_match_claim_id`| `UUID` | REFERENCES `claims(id)` ON DELETE SET NULL | `NULL` | Matched candidate claim ID |
| `matched_claim_status`| `TEXT` | — | `NULL` | Status of historical match |
| `matched_claim_age_days`| `INT` | — | `NULL` | Days elapsed since historical claim |
| `wait_until` | `TIMESTAMPTZ` | — | `NULL` | Timeout for pending candidate claim |
| `field_scores` | `JSONB` | NOT NULL | `'{}'::jsonb` | Breakdown: merchant, date, amount, file hash |
| `triggered_rules` | `JSONB` | NOT NULL | `'[]'::jsonb` | Array of deterministic rules triggered |
| `evidence` | `JSONB` | NOT NULL | `'{}'::jsonb` | Side-by-side comparison payload + LLM reasoning |
| `explanation` | `TEXT` | — | `NULL` | Human-readable explanation |
| `engine_version` | `TEXT` | NOT NULL | `'1.0.0-deterministic'` | Engine version tag |
| `verified_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Run timestamp |
| `created_at` | `TIMESTAMPTZ` | NOT NULL | `NOW()` | Record timestamp |

---

## 6. Triggers and Indexes

### Automated `updated_at` Trigger
A single PL/pgSQL trigger function automatically updates the `updated_at` timestamp before any `UPDATE` on `users`, `claims`, `claim_documents`, `ocr_processing`, `claim_extracted_data`, and `payments`:

```sql
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Performance Indexes

| Table | Index Name | Type / Columns | Purpose |
|---|---|---|---|
| `users` | `idx_users_email` | B-tree (`email`) | Quick lookup by user email |
| `users` | `idx_users_role` | B-tree (`role`) | Filter users by role |
| `users` | `idx_users_manager_id` | B-tree (`manager_id`) | Manager-to-report hierarchy lookups |
| `claims` | `idx_claims_employee_id` | B-tree (`employee_id`) | Staff member claim history queries |
| `claims` | `idx_claims_manager_id` | B-tree (`manager_id`) | Manager review queue queries |
| `claims` | `idx_claims_status` | B-tree (`status`) | Status filtering & queues |
| `claims` | `idx_claims_finance_status`| B-tree (`finance_status`)| Finance queue filtering |
| `claims` | `idx_claims_submitted_at` | B-tree (`submitted_at DESC`)| Chronological sorting of submissions |
| `claims` | `idx_claims_claim_date` | B-tree (`claim_date DESC`) | Expense date sorting |
| `claims` | `idx_claims_merchant` | GIN (`merchant gin_trgm_ops`) | Fast substring & fuzzy search on vendor names |
| `claim_documents` | `idx_claim_documents_claim_id` | B-tree (`claim_id`) | Fetch documents for a claim |
| `ocr_processing` | `idx_ocr_processing_document_id`| B-tree (`document_id`) | Link OCR attempts to document |
| `ocr_processing` | `idx_ocr_processing_status` | B-tree (`status`) | Filter OCR pipeline states |
| `claim_extracted_data`| `idx_claim_extracted_data_claim_id` | B-tree (`claim_id`) | Fast retrieval of extracted claim fields |
| `claim_extracted_data`| `idx_claim_extracted_data_document_id`| B-tree (`document_id`) | Link extracted items to document |
| `claim_extracted_data`| `idx_claim_extracted_data_merchant` | GIN (`merchant_normalized gin_trgm_ops`) | Fast vendor deduplication matching |
| `claim_verifications`| `idx_claim_verifications_claim_id` | B-tree (`claim_id`) | Retrieve verification audit for claim |
| `claim_verifications`| `idx_claim_verifications_decision` | B-tree (`decision`) | Filter claims by verification decision |
| `claim_verifications`| `idx_claim_verifications_verified_at`| B-tree (`verified_at DESC`)| Chronological audit queries |
| `claim_items` | `idx_claim_items_claim_id` | B-tree (`claim_id`) | Fetch line items for a claim |
| `verification_results`| `idx_verification_results_claim_id` | B-tree (`claim_id`) | Fetch verification results |
| `duplicate_matches` | `idx_duplicate_matches_claim_id` | B-tree (`claim_id`) | Match detection results by claim |
| `claim_status_history`| `idx_claim_status_history_claim_id` | B-tree (`claim_id`) | Claim timeline reconstruction |
| `claim_status_history`| `idx_claim_status_history_occurred_at` | B-tree (`occurred_at DESC`)| Global activity feed |
| `payments` | `idx_payments_claim_id` | B-tree (`claim_id`) | Fast 1-to-1 payment link |
| `payments` | `idx_payments_payment_reference`| B-tree (`payment_reference`) | Reconcile bank transactions |

---

## 7. Migration & Setup Instructions

The migration SQL scripts are located in `Backend/db/migrations/`:

### Step 1: Optional Reset (Fresh install)
To wipe all tables, enums, and triggers cleanly:
- Open **Supabase Dashboard** -> **SQL Editor** -> New query.
- Copy & run `Backend/db/migrations/000_nuke.sql`.

### Step 2: Apply Schema & Seeds
Execute migrations in the following order:
1. `001_initial_schema.sql`: Core schema (users, claims, claim_documents, items, reviews, payments, status_history).
2. `002_seed_data.sql`: Seed staff users (`usr-001`), managers (`usr-mgr-001`), finance controller (`usr-fin-001`), sample claims, line items, and audit history.
3. `003_ocr_pipeline.sql`: Creates `ocr_processing` and `claim_extracted_data` tables, adds `storage_path` and `checksum` to `claim_documents`.
4. `004_storage_bucket.sql`: Creates Supabase Storage bucket `receipts` with public read policies.
5. `005_verification_engine.sql`: Creates `claim_verifications` table for full deterministic and LLM explainability.
6. `006_manager_actions.sql`: Adds `MANAGER_CONFIRMED` to the `claim_status` enum.

---

## 8. Backend Integration

The FastAPI backend connects using the `supabase-py` client in `Backend/app/core/database.py`:

```python
from supabase import create_client, Client
from app.core.config import settings

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
```

Ensure the following variables are present in `Backend/.env`:
```ini
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-or-service-key
```
