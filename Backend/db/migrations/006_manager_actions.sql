-- =============================================================================
-- Expense Claims System — Manager Actions & Status Transitions
-- Version : 006
-- Created : 2026-09-12
-- Run this in: Supabase SQL Editor (Dashboard -> SQL Editor -> New query)
-- =============================================================================

-- 1. Add MANAGER_CONFIRMED to claim_status enum if not present
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum
        JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
        WHERE pg_type.typname = 'claim_status'
          AND pg_enum.enumlabel = 'MANAGER_CONFIRMED'
    ) THEN
        ALTER TYPE claim_status ADD VALUE 'MANAGER_CONFIRMED' AFTER 'FLAGGED';
    END IF;
END
$$;
