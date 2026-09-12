-- =============================================================================
-- Expense Claims System — OCR Pipeline Tables
-- Version : 003
-- Created : 2026-09-12
-- Run this in: Supabase SQL Editor (Dashboard -> SQL Editor -> New query)
-- Prerequisite: 001_initial_schema.sql and 002_seed_data.sql already applied
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Extend claim_documents with storage & checksum columns
-- ---------------------------------------------------------------------------
ALTER TABLE claim_documents
  ADD COLUMN IF NOT EXISTS storage_path TEXT,
  ADD COLUMN IF NOT EXISTS checksum     TEXT,
  ADD COLUMN IF NOT EXISTS updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW();

COMMENT ON COLUMN claim_documents.storage_path IS 'Supabase Storage path: claims/{claim_id}/{doc_id}/{filename}';
COMMENT ON COLUMN claim_documents.checksum     IS 'SHA-256 hex digest for deduplication';

-- Add updated_at trigger to claim_documents
DROP TRIGGER IF EXISTS set_updated_at ON claim_documents;
CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON claim_documents
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ---------------------------------------------------------------------------
-- 2. ocr_processing — tracks each OCR extraction attempt
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ocr_processing (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_id         UUID NOT NULL REFERENCES claim_documents(id) ON DELETE CASCADE,

  status              TEXT NOT NULL DEFAULT 'PENDING'
                      CHECK (status IN ('PENDING','PROCESSING','EXTRACTED','NORMALIZED','COMPLETED','FAILED')),
  provider            TEXT NOT NULL DEFAULT 'gemini',
  provider_request_id TEXT,

  raw_response        JSONB,
  error_code          TEXT,
  error_message       TEXT,
  retry_count         INT NOT NULL DEFAULT 0,

  started_at          TIMESTAMPTZ,
  completed_at        TIMESTAMPTZ,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE ocr_processing IS 'One row per OCR extraction attempt. Tracks pipeline status from PENDING through COMPLETED/FAILED.';

CREATE INDEX IF NOT EXISTS idx_ocr_processing_document_id ON ocr_processing(document_id);
CREATE INDEX IF NOT EXISTS idx_ocr_processing_status      ON ocr_processing(status);

-- Add updated_at trigger
DROP TRIGGER IF EXISTS set_updated_at ON ocr_processing;
CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON ocr_processing
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- ---------------------------------------------------------------------------
-- 3. claim_extracted_data — normalized receipt information
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claim_extracted_data (
  id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  claim_id            UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  document_id         UUID NOT NULL REFERENCES claim_documents(id) ON DELETE CASCADE,
  ocr_processing_id   UUID REFERENCES ocr_processing(id) ON DELETE SET NULL,

  -- Extracted fields
  merchant            TEXT,
  merchant_normalized TEXT,
  invoice_number      TEXT,
  transaction_date    DATE,
  currency            CHAR(3),
  subtotal            NUMERIC(12, 2),
  tax                 NUMERIC(12, 2),
  total               NUMERIC(12, 2),

  -- Structured data
  line_items          JSONB NOT NULL DEFAULT '[]'::jsonb,
  normalized_data     JSONB NOT NULL DEFAULT '{}'::jsonb,
  confidence_scores   JSONB NOT NULL DEFAULT '{}'::jsonb,
  validation_warnings JSONB NOT NULL DEFAULT '[]'::jsonb,

  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE claim_extracted_data IS 'Normalized receipt data extracted by OCR. One row per successful extraction.';

CREATE INDEX IF NOT EXISTS idx_claim_extracted_data_claim_id    ON claim_extracted_data(claim_id);
CREATE INDEX IF NOT EXISTS idx_claim_extracted_data_document_id ON claim_extracted_data(document_id);
CREATE INDEX IF NOT EXISTS idx_claim_extracted_data_merchant    ON claim_extracted_data USING gin(merchant_normalized gin_trgm_ops);

-- Add updated_at trigger
DROP TRIGGER IF EXISTS set_updated_at ON claim_extracted_data;
CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON claim_extracted_data
  FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
-- Migration 003 complete.
-- =============================================================================
