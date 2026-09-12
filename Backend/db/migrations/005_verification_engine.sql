-- =============================================================================
-- Expense Claims System — Verification Engine Tables
-- Version : 005
-- Created : 2026-09-12
-- Run this in: Supabase SQL Editor (Dashboard -> SQL Editor -> New query)
-- =============================================================================

-- 1. claim_verifications — Stores full verification runs, decisions & explainability
CREATE TABLE IF NOT EXISTS claim_verifications (
  id                        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  claim_id                  UUID NOT NULL REFERENCES claims(id) ON DELETE CASCADE,

  decision                  TEXT NOT NULL
                            CHECK (decision IN ('CLEAN', 'POTENTIAL_DUPLICATE', 'BORDERLINE', 'WAITING_FOR_EXISTING_CLAIM', 'ESCALATE_TO_MANAGER')),
  similarity_score          NUMERIC(5, 4) NOT NULL DEFAULT 0.0,

  strongest_match_claim_id  UUID REFERENCES claims(id) ON DELETE SET NULL,
  matched_claim_status      TEXT,
  matched_claim_age_days    INT,
  wait_until                TIMESTAMPTZ,

  field_scores              JSONB NOT NULL DEFAULT '{}'::jsonb,
  triggered_rules           JSONB NOT NULL DEFAULT '[]'::jsonb,
  evidence                  JSONB NOT NULL DEFAULT '{}'::jsonb,
  explanation               TEXT,

  engine_version            TEXT NOT NULL DEFAULT '1.0.0-deterministic',
  verified_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE claim_verifications IS 'Persists verification engine decisions, similarity metrics, and audit evidence.';

CREATE INDEX IF NOT EXISTS idx_claim_verifications_claim_id     ON claim_verifications(claim_id);
CREATE INDEX IF NOT EXISTS idx_claim_verifications_decision     ON claim_verifications(decision);
CREATE INDEX IF NOT EXISTS idx_claim_verifications_verified_at  ON claim_verifications(verified_at DESC);
