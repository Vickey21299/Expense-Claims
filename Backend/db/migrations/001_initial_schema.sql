-- =============================================================================
-- Expense Claims System — Initial Schema Migration
-- Version : 001
-- Created : 2026-09-11
-- Run this in: Supabase SQL Editor (Dashboard -> SQL Editor -> New query)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 0. Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ---------------------------------------------------------------------------
-- 1. Enums  (drop stale versions first — CASCADE drops dependent columns/tables)
-- ---------------------------------------------------------------------------
DROP TYPE IF EXISTS user_role CASCADE;
DROP TYPE IF EXISTS claim_status CASCADE;
DROP TYPE IF EXISTS ocr_status CASCADE;
DROP TYPE IF EXISTS verification_status CASCADE;
DROP TYPE IF EXISTS document_type CASCADE;
DROP TYPE IF EXISTS finance_decision CASCADE;

CREATE TYPE user_role AS ENUM ('staff', 'manager', 'finance');

CREATE TYPE claim_status AS ENUM (
  'DRAFT',
  'SUBMITTED',
  'UNDER_REVIEW',
  'FLAGGED',
  'APPROVED',
  'REJECTED',
  'READY_FOR_PAYMENT',
  'PAID'
);

CREATE TYPE ocr_status AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'SKIPPED');

CREATE TYPE verification_status AS ENUM ('PENDING', 'CLEAN', 'FLAGGED', 'ERROR');

CREATE TYPE document_type AS ENUM ('RECEIPT', 'INVOICE', 'BOARDING_PASS', 'OTHER');

CREATE TYPE finance_decision AS ENUM ('FINANCE_PENDING', 'FINANCE_CLEARED', 'FINANCE_REJECTED', 'FINANCE_EXCEPTION');

-- ---------------------------------------------------------------------------
-- 2. users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  external_id     TEXT UNIQUE,
  email           TEXT NOT NULL UNIQUE,
  full_name       TEXT NOT NULL,
  department      TEXT,
  role            user_role NOT NULL DEFAULT 'staff',
  job_title       TEXT,
  manager_id      UUID REFERENCES users(id),
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE users IS 'All system users: staff, managers, and finance users.';
COMMENT ON COLUMN users.external_id IS 'Legacy/mock ID (usr-001, usr-mgr-001, etc.) for seeding and dev reference.';
COMMENT ON COLUMN users.manager_id IS 'Direct reporting manager. NULL for top-level users who route to Finance.';

CREATE INDEX IF NOT EXISTS idx_users_email      ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role       ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_manager_id ON users(manager_id);

-- ---------------------------------------------------------------------------
-- 3. claims
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS claims CASCADE;

CREATE TABLE claims (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  claim_ref           TEXT UNIQUE,

  employee_id         UUID NOT NULL REFERENCES users(id),
  manager_id          UUID REFERENCES users(id),

  merchant            TEXT,
  claim_type          TEXT NOT NULL,
  amount              NUMERIC(12, 2) NOT NULL DEFAULT 0,
  currency            CHAR(3) NOT NULL DEFAULT 'INR',
  claim_date          DATE,
  description         TEXT,

  status              claim_status NOT NULL DEFAULT 'DRAFT',

  ocr_status          ocr_status NOT NULL DEFAULT 'PENDING',
  verification_status verification_status NOT NULL DEFAULT 'PENDING',

  finance_status      finance_decision,
  payment_reference   TEXT,

  submitted_at        TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE claims IS 'Core claim record. OCR, verification, reviews, and payment info live in separate tables.';

CREATE INDEX IF NOT EXISTS idx_claims_employee_id    ON claims(employee_id);
CREATE INDEX IF NOT EXISTS idx_claims_manager_id     ON claims(manager_id);
CREATE INDEX IF NOT EXISTS idx_claims_status         ON claims(status);
CREATE INDEX IF NOT EXISTS idx_claims_finance_status ON claims(finance_status);
CREATE INDEX IF NOT EXISTS idx_claims_submitted_at   ON claims(submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_claims_claim_date     ON claims(claim_date DESC);
CREATE INDEX IF NOT EXISTS idx_claims_merchant       ON claims USING gin(merchant gin_trgm_ops);

-- ---------------------------------------------------------------------------
-- 4. claim_documents
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claim_documents (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  claim_id         UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  document_type    document_type NOT NULL DEFAULT 'RECEIPT',
  file_name        TEXT,
  file_url         TEXT,
  file_size_bytes  BIGINT,
  mime_type        TEXT,
  ocr_raw_text     TEXT,
  ocr_confidence   NUMERIC(5, 4),
  ocr_processed_at TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE claim_documents IS 'Receipt and invoice files. Stores raw OCR output — structured data goes into claim_items.';
CREATE INDEX IF NOT EXISTS idx_claim_documents_claim_id ON claim_documents(claim_id);

-- ---------------------------------------------------------------------------
-- 5. claim_items
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claim_items (
  id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  claim_id     UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  document_id  UUID REFERENCES claim_documents(id) ON DELETE SET NULL,
  description  TEXT NOT NULL,
  quantity     NUMERIC(10, 3) NOT NULL DEFAULT 1,
  unit_price   NUMERIC(12, 2) NOT NULL DEFAULT 0,
  total_amount NUMERIC(12, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
  currency     CHAR(3) NOT NULL DEFAULT 'INR',
  extracted_by TEXT DEFAULT 'MANUAL',
  confidence   NUMERIC(5, 4),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE claim_items IS 'Line items extracted from receipts. total_amount is a generated column.';
CREATE INDEX IF NOT EXISTS idx_claim_items_claim_id ON claim_items(claim_id);

-- ---------------------------------------------------------------------------
-- 6. verification_results
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS verification_results (
  id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  claim_id   UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  check_name TEXT NOT NULL,
  passed     BOOLEAN NOT NULL,
  message    TEXT,
  severity   TEXT NOT NULL DEFAULT 'INFO',
  checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE verification_results IS 'One row per verification check per claim.';
CREATE INDEX IF NOT EXISTS idx_verification_results_claim_id ON verification_results(claim_id);

-- ---------------------------------------------------------------------------
-- 7. duplicate_matches
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS duplicate_matches (
  id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  claim_id         UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  matched_claim_id UUID REFERENCES claims(id) ON DELETE SET NULL,
  similarity_score NUMERIC(5, 4),
  assessment       TEXT,
  signals          JSONB NOT NULL DEFAULT '[]'::jsonb,
  detected_by      TEXT DEFAULT 'RULE',
  resolved         BOOLEAN NOT NULL DEFAULT FALSE,
  resolved_by      UUID REFERENCES users(id),
  resolved_at      TIMESTAMPTZ,
  resolution_note  TEXT,
  detected_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE duplicate_matches IS 'Duplicate detection results. signals is a JSONB array of human-readable reasons.';
CREATE INDEX IF NOT EXISTS idx_duplicate_matches_claim_id         ON duplicate_matches(claim_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_matches_matched_claim_id ON duplicate_matches(matched_claim_id);

-- ---------------------------------------------------------------------------
-- 8. claim_status_history
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claim_status_history (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  claim_id    UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  from_status claim_status,
  to_status   claim_status NOT NULL,
  event_label TEXT NOT NULL,
  comment     TEXT,
  actor_id    UUID REFERENCES users(id),
  actor_name  TEXT,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE claim_status_history IS 'Full audit trail of every status transition. Immutable — never UPDATE or DELETE.';
CREATE INDEX IF NOT EXISTS idx_claim_status_history_claim_id    ON claim_status_history(claim_id);
CREATE INDEX IF NOT EXISTS idx_claim_status_history_occurred_at ON claim_status_history(occurred_at DESC);

-- ---------------------------------------------------------------------------
-- 9. manager_reviews
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS manager_reviews (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  claim_id    UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  manager_id  UUID NOT NULL REFERENCES users(id),
  decision    TEXT NOT NULL,
  comment     TEXT,
  reviewed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE manager_reviews IS 'Manager approve/reject decisions. One row per decision round.';
CREATE INDEX IF NOT EXISTS idx_manager_reviews_claim_id   ON manager_reviews(claim_id);
CREATE INDEX IF NOT EXISTS idx_manager_reviews_manager_id ON manager_reviews(manager_id);

-- ---------------------------------------------------------------------------
-- 10. finance_reviews
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS finance_reviews (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  claim_id        UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  finance_user_id UUID NOT NULL REFERENCES users(id),
  decision        finance_decision NOT NULL,
  cleared         BOOLEAN NOT NULL DEFAULT FALSE,
  comment         TEXT,
  reviewed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE finance_reviews IS 'Finance team decisions.';
CREATE INDEX IF NOT EXISTS idx_finance_reviews_claim_id        ON finance_reviews(claim_id);
CREATE INDEX IF NOT EXISTS idx_finance_reviews_finance_user_id ON finance_reviews(finance_user_id);

-- ---------------------------------------------------------------------------
-- 11. payments
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
  id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  claim_id          UUID NOT NULL UNIQUE REFERENCES claims(id),
  payment_reference TEXT UNIQUE,
  amount            NUMERIC(12, 2) NOT NULL,
  currency          CHAR(3) NOT NULL DEFAULT 'INR',
  processed_by      UUID REFERENCES users(id),
  processed_at      TIMESTAMPTZ,
  notes             TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE payments IS 'Payment record. One payment per claim (terminal state).';
CREATE INDEX IF NOT EXISTS idx_payments_claim_id          ON payments(claim_id);
CREATE INDEX IF NOT EXISTS idx_payments_payment_reference ON payments(payment_reference);
CREATE INDEX IF NOT EXISTS idx_payments_processed_at      ON payments(processed_at DESC);

-- ---------------------------------------------------------------------------
-- 12. updated_at trigger
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['users', 'claims', 'payments']
  LOOP
    EXECUTE format(
      'DROP TRIGGER IF EXISTS set_updated_at ON %I;
       CREATE TRIGGER set_updated_at
         BEFORE UPDATE ON %I
         FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();',
      t, t
    );
  END LOOP;
END $$;

-- =============================================================================
-- Schema 001 complete. Run 002_seed_data.sql next.
-- =============================================================================
