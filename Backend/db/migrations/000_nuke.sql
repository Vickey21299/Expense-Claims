-- =============================================================================
-- NUKE SCRIPT — Drop everything and start fresh
-- Run this BEFORE 001_initial_schema.sql
-- =============================================================================

-- Drop all tables (CASCADE handles foreign key dependencies)
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS finance_reviews CASCADE;
DROP TABLE IF EXISTS manager_reviews CASCADE;
DROP TABLE IF EXISTS claim_status_history CASCADE;
DROP TABLE IF EXISTS duplicate_matches CASCADE;
DROP TABLE IF EXISTS verification_results CASCADE;
DROP TABLE IF EXISTS claim_items CASCADE;
DROP TABLE IF EXISTS claim_documents CASCADE;
DROP TABLE IF EXISTS claims CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop all enums
DROP TYPE IF EXISTS user_role CASCADE;
DROP TYPE IF EXISTS claim_status CASCADE;
DROP TYPE IF EXISTS ocr_status CASCADE;
DROP TYPE IF EXISTS verification_status CASCADE;
DROP TYPE IF EXISTS document_type CASCADE;
DROP TYPE IF EXISTS finance_decision CASCADE;

-- Drop trigger function
DROP FUNCTION IF EXISTS trigger_set_updated_at CASCADE;

-- =============================================================================
-- Database is now clean. Run 001_initial_schema.sql next.
-- =============================================================================
