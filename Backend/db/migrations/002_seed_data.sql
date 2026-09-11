-- =============================================================================
-- Expense Claims System — Seed Data Migration
-- Version : 002
-- Created : 2026-09-11
-- Source  : Frontend/src/data/mockClaims.js
-- Run AFTER 001_initial_schema.sql
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Users  (staff, managers, finance)
-- ---------------------------------------------------------------------------
INSERT INTO users (external_id, email, full_name, department, role, job_title) VALUES
  ('usr-001',     'vickey.kumar@company.com',  'Vickey Kumar',  'Engineering', 'staff',   'Software Engineer'),
  ('usr-mgr-001', 'rahul.sharma@company.com',  'Rahul Sharma',  'Engineering', 'manager', 'Engineering Manager'),
  ('usr-mgr-002', 'priya.mehta@company.com',   'Priya Mehta',   'Engineering', 'manager', 'Senior Engineering Manager'),
  ('usr-fin-001', 'anita.joshi@company.com',   'Anita Joshi',   'Finance',     'finance', 'Finance Controller'),
  ('usr-101',     'rahul.kumar@company.com',   'Rahul Kumar',   'Engineering', 'staff',   'Software Engineer'),
  ('usr-102',     'neha.singh@company.com',    'Neha Singh',    'Engineering', 'staff',   'Frontend Developer'),
  ('usr-103',     'amit.sharma@company.com',   'Amit Sharma',   'Engineering', 'staff',   'Backend Developer'),
  ('usr-104',     'priya.desai@company.com',   'Priya Desai',   'Design',      'staff',   'UI/UX Designer'),
  ('usr-105',     'karan.mehta@company.com',   'Karan Mehta',   'Engineering', 'staff',   'DevOps Engineer')
ON CONFLICT (external_id) DO NOTHING;

-- Set manager_id for staff (Rahul Sharma manages the engineering staff)
UPDATE users SET manager_id = (SELECT id FROM users WHERE external_id = 'usr-mgr-001')
WHERE external_id IN ('usr-001', 'usr-101', 'usr-102', 'usr-103', 'usr-105');

UPDATE users SET manager_id = (SELECT id FROM users WHERE external_id = 'usr-mgr-001')
WHERE external_id = 'usr-104';

-- Rahul Sharma reports to Priya Mehta
UPDATE users SET manager_id = (SELECT id FROM users WHERE external_id = 'usr-mgr-002')
WHERE external_id = 'usr-mgr-001';

-- ---------------------------------------------------------------------------
-- 2. Claims — mockClaims (Vickey Kumar's own claims)
-- ---------------------------------------------------------------------------

-- CLM-1031: Uber - SUBMITTED
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, submitted_at, created_at, updated_at)
SELECT 'CLM-1031',
  (SELECT id FROM users WHERE external_id = 'usr-001'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'Uber', 'Travel', 840.00, 'INR', '2026-09-10',
  'Cab to client site for project kick-off meeting',
  'SUBMITTED', 'COMPLETED', 'CLEAN',
  '2026-09-10T09:15:00Z', '2026-09-10T09:10:00Z', '2026-09-10T09:15:00Z';

-- CLM-1028: Amazon - UNDER_REVIEW
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, submitted_at, created_at, updated_at)
SELECT 'CLM-1028',
  (SELECT id FROM users WHERE external_id = 'usr-001'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'Amazon', 'Office Supplies', 2450.00, 'INR', '2026-09-09',
  'Mechanical keyboard and ergonomic mouse for WFH setup',
  'UNDER_REVIEW', 'COMPLETED', 'CLEAN',
  '2026-09-09T11:20:00Z', '2026-09-09T11:15:00Z', '2026-09-09T14:00:00Z';

-- CLM-1024: Marriott - APPROVED
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, finance_status, submitted_at, created_at, updated_at)
SELECT 'CLM-1024',
  (SELECT id FROM users WHERE external_id = 'usr-001'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'Marriott', 'Accommodation', 6200.00, 'INR', '2026-09-06',
  'Hotel stay for 1 night -- Bangalore off-site sprint',
  'APPROVED', 'COMPLETED', 'CLEAN', 'FINANCE_PENDING',
  '2026-09-06T18:00:00Z', '2026-09-06T17:50:00Z', '2026-09-07T10:30:00Z';

-- CLM-1021: Swiggy - REJECTED
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, submitted_at, created_at, updated_at)
SELECT 'CLM-1021',
  (SELECT id FROM users WHERE external_id = 'usr-001'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'Swiggy', 'Meals', 540.00, 'INR', '2026-09-03',
  'Team lunch during product planning session',
  'REJECTED', 'SKIPPED', 'CLEAN',
  '2026-09-03T14:05:00Z', '2026-09-03T14:00:00Z', '2026-09-03T17:00:00Z';

-- CLM-1018: MakeMyTrip - PAID
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, finance_status, payment_reference, submitted_at, created_at, updated_at)
SELECT 'CLM-1018',
  (SELECT id FROM users WHERE external_id = 'usr-001'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'MakeMyTrip', 'Travel', 8500.00, 'INR', '2026-08-28',
  'Round-trip train tickets -- Delhi to Mumbai for client visit',
  'PAID', 'COMPLETED', 'CLEAN', 'FINANCE_CLEARED', 'PAY-2026-09-01-001',
  '2026-08-28T10:00:00Z', '2026-08-28T09:55:00Z', '2026-09-01T15:00:00Z';

-- CLM-1015: Zoom - FLAGGED
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, submitted_at, created_at, updated_at)
SELECT 'CLM-1015',
  (SELECT id FROM users WHERE external_id = 'usr-001'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'Zoom', 'Software & Subscriptions', 1299.00, 'INR', '2026-08-25',
  'Zoom Pro monthly subscription for team calls',
  'FLAGGED', 'COMPLETED', 'FLAGGED',
  '2026-08-25T11:30:00Z', '2026-08-25T11:25:00Z', '2026-08-25T14:30:00Z';

-- CLM-1012: Cafe Coffee Day - READY_FOR_PAYMENT
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, finance_status, submitted_at, created_at, updated_at)
SELECT 'CLM-1012',
  (SELECT id FROM users WHERE external_id = 'usr-001'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'Cafe Coffee Day', 'Meals', 380.00, 'INR', '2026-08-20',
  'Client refreshments during discovery workshop',
  'READY_FOR_PAYMENT', 'SKIPPED', 'CLEAN', 'FINANCE_CLEARED',
  '2026-08-20T16:00:00Z', '2026-08-20T15:55:00Z', '2026-08-22T09:00:00Z';

-- CLM-DRAFT-1: DRAFT
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, description, status, ocr_status, verification_status, created_at, updated_at)
SELECT 'CLM-DRAFT-1',
  (SELECT id FROM users WHERE external_id = 'usr-001'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  '', 'Uncategorized', 0.00, 'INR', '',
  'DRAFT', 'PENDING', 'PENDING',
  '2026-09-10T14:00:00Z', '2026-09-10T14:00:00Z';

-- ---------------------------------------------------------------------------
-- 3. Claims — managerClaims (team members' claims reviewed by Rahul Sharma)
-- ---------------------------------------------------------------------------

-- CLM-2001: Rahul Kumar - Uber - SUBMITTED
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, submitted_at, created_at, updated_at)
SELECT 'CLM-2001',
  (SELECT id FROM users WHERE external_id = 'usr-101'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'Uber', 'Travel', 840.00, 'INR', '2026-09-10',
  'Cab to client site for quarterly business review',
  'SUBMITTED', 'COMPLETED', 'CLEAN',
  '2026-09-10T09:15:00Z', '2026-09-10T09:10:00Z', '2026-09-10T09:16:00Z';

-- CLM-2002: Neha Singh - Amazon - FLAGGED (duplicate)
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, finance_status, submitted_at, created_at, updated_at)
SELECT 'CLM-2002',
  (SELECT id FROM users WHERE external_id = 'usr-102'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'Amazon', 'Office Supplies', 2450.00, 'INR', '2026-09-08',
  'Keyboard and mouse for office workstation',
  'FLAGGED', 'COMPLETED', 'FLAGGED', 'FINANCE_EXCEPTION',
  '2026-09-08T10:30:00Z', '2026-09-08T10:25:00Z', '2026-09-08T10:32:00Z';

-- CLM-2003: Amit Sharma - Marriott - APPROVED
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, finance_status, submitted_at, created_at, updated_at)
SELECT 'CLM-2003',
  (SELECT id FROM users WHERE external_id = 'usr-103'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'Marriott', 'Accommodation', 6200.00, 'INR', '2026-09-05',
  'Hotel stay for Bangalore sprint -- 1 night',
  'APPROVED', 'COMPLETED', 'CLEAN', 'FINANCE_PENDING',
  '2026-09-05T18:00:00Z', '2026-09-05T17:50:00Z', '2026-09-06T09:30:00Z';

-- CLM-2004: Priya Desai - Swiggy - REJECTED
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, submitted_at, created_at, updated_at)
SELECT 'CLM-2004',
  (SELECT id FROM users WHERE external_id = 'usr-104'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'Swiggy', 'Meals', 540.00, 'INR', '2026-09-02',
  'Lunch order during work-from-home',
  'REJECTED', 'COMPLETED', 'CLEAN',
  '2026-09-02T13:00:00Z', '2026-09-02T12:55:00Z', '2026-09-02T15:15:00Z';

-- CLM-2005: Karan Mehta - MakeMyTrip - PAID
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, finance_status, payment_reference, submitted_at, created_at, updated_at)
SELECT 'CLM-2005',
  (SELECT id FROM users WHERE external_id = 'usr-105'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'MakeMyTrip', 'Travel', 8500.00, 'INR', '2026-08-25',
  'Round-trip flight tickets -- Mumbai to Chennai for production deployment',
  'PAID', 'COMPLETED', 'CLEAN', 'FINANCE_CLEARED', 'PAY-2026-08-29-001',
  '2026-08-25T10:00:00Z', '2026-08-25T09:50:00Z', '2026-08-29T15:00:00Z';

-- CLM-2006: Rahul Sharma (manager's own claim) - Zoom - SUBMITTED
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, submitted_at, created_at, updated_at)
SELECT 'CLM-2006',
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-002'),
  'Zoom', 'Software & Subscriptions', 1299.00, 'INR', '2026-09-01',
  'Zoom Pro subscription for team stand-ups and client calls',
  'SUBMITTED', 'COMPLETED', 'CLEAN',
  '2026-09-01T11:30:00Z', '2026-09-01T11:25:00Z', '2026-09-01T11:31:00Z';

-- CLM-2007: Rahul Kumar - WeWork - SUBMITTED
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, submitted_at, created_at, updated_at)
SELECT 'CLM-2007',
  (SELECT id FROM users WHERE external_id = 'usr-101'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'WeWork', 'Office Supplies', 3500.00, 'INR', '2026-09-09',
  'Co-working space day pass for offsite collaboration',
  'SUBMITTED', 'COMPLETED', 'CLEAN',
  '2026-09-09T17:00:00Z', '2026-09-09T16:55:00Z', '2026-09-09T17:01:00Z';

-- CLM-2008: Neha Singh - IndiGo - APPROVED / FINANCE_PENDING
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, finance_status, submitted_at, created_at, updated_at)
SELECT 'CLM-2008',
  (SELECT id FROM users WHERE external_id = 'usr-102'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'IndiGo Airlines', 'Travel', 9200.00, 'INR', '2026-09-03',
  'Return flight -- Hyderabad to Pune for design sprint',
  'APPROVED', 'COMPLETED', 'CLEAN', 'FINANCE_PENDING',
  '2026-09-03T10:00:00Z', '2026-09-03T09:55:00Z', '2026-09-04T09:00:00Z';

-- CLM-2009: Amit Sharma - OYO - READY_FOR_PAYMENT
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, finance_status, submitted_at, created_at, updated_at)
SELECT 'CLM-2009',
  (SELECT id FROM users WHERE external_id = 'usr-103'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'OYO Rooms', 'Accommodation', 4800.00, 'INR', '2026-09-07',
  'Hotel stay for 2 nights -- Pune client project',
  'READY_FOR_PAYMENT', 'COMPLETED', 'CLEAN', 'FINANCE_CLEARED',
  '2026-09-07T08:00:00Z', '2026-09-07T07:55:00Z', '2026-09-09T10:00:00Z';

-- CLM-2010: Priya Desai - Adobe - APPROVED / FINANCE_REJECTED
INSERT INTO claims (claim_ref, employee_id, manager_id, merchant, claim_type, amount, currency, claim_date, description, status, ocr_status, verification_status, finance_status, submitted_at, created_at, updated_at)
SELECT 'CLM-2010',
  (SELECT id FROM users WHERE external_id = 'usr-104'),
  (SELECT id FROM users WHERE external_id = 'usr-mgr-001'),
  'Adobe', 'Software & Subscriptions', 5500.00, 'INR', '2026-09-01',
  'Adobe Creative Cloud annual subscription',
  'APPROVED', 'COMPLETED', 'CLEAN', 'FINANCE_REJECTED',
  '2026-09-01T14:00:00Z', '2026-09-01T13:55:00Z', '2026-09-03T11:00:00Z';

-- ---------------------------------------------------------------------------
-- 4. Verification results  (for managerClaims, all have 3 checks each)
-- ---------------------------------------------------------------------------
INSERT INTO verification_results (claim_id, check_name, passed, message, severity, checked_at)
SELECT c.id, v.check_name, v.passed, v.message, v.severity, v.checked_at::timestamptz
FROM claims c
JOIN (VALUES
  ('CLM-2001', 'Receipt processed', true, NULL, 'INFO', '2026-09-10T09:11:00Z'),
  ('CLM-2001', 'Required information detected', true, NULL, 'INFO', '2026-09-10T09:11:00Z'),
  ('CLM-2001', 'No immediate financial issue detected', true, NULL, 'INFO', '2026-09-10T09:11:00Z'),

  ('CLM-2002', 'Receipt processed', true, NULL, 'INFO', '2026-09-08T10:26:00Z'),
  ('CLM-2002', 'Required information detected', true, NULL, 'INFO', '2026-09-08T10:26:00Z'),
  ('CLM-2002', 'Possible duplicate detected', false, 'Similar claim found', 'ERROR', '2026-09-08T10:32:00Z'),

  ('CLM-2003', 'Receipt processed', true, NULL, 'INFO', '2026-09-05T17:51:00Z'),
  ('CLM-2003', 'Required information detected', true, NULL, 'INFO', '2026-09-05T17:51:00Z'),
  ('CLM-2003', 'No immediate financial issue detected', true, NULL, 'INFO', '2026-09-05T17:51:00Z'),

  ('CLM-2004', 'Receipt processed', true, NULL, 'INFO', '2026-09-02T12:56:00Z'),
  ('CLM-2004', 'Required information detected', true, NULL, 'INFO', '2026-09-02T12:56:00Z'),
  ('CLM-2004', 'No immediate financial issue detected', true, NULL, 'INFO', '2026-09-02T12:56:00Z'),

  ('CLM-2005', 'Receipt processed', true, NULL, 'INFO', '2026-08-25T09:51:00Z'),
  ('CLM-2005', 'Required information detected', true, NULL, 'INFO', '2026-08-25T09:51:00Z'),
  ('CLM-2005', 'No immediate financial issue detected', true, NULL, 'INFO', '2026-08-25T09:51:00Z'),

  ('CLM-2006', 'Receipt processed', true, NULL, 'INFO', '2026-09-01T11:26:00Z'),
  ('CLM-2006', 'Required information detected', true, NULL, 'INFO', '2026-09-01T11:26:00Z'),
  ('CLM-2006', 'No immediate financial issue detected', true, NULL, 'INFO', '2026-09-01T11:26:00Z'),

  ('CLM-2007', 'Receipt processed', true, NULL, 'INFO', '2026-09-09T16:56:00Z'),
  ('CLM-2007', 'Required information detected', true, NULL, 'INFO', '2026-09-09T16:56:00Z'),
  ('CLM-2007', 'No immediate financial issue detected', true, NULL, 'INFO', '2026-09-09T16:56:00Z'),

  ('CLM-2008', 'Receipt processed', true, NULL, 'INFO', '2026-09-03T09:56:00Z'),
  ('CLM-2008', 'Required information detected', true, NULL, 'INFO', '2026-09-03T09:56:00Z'),
  ('CLM-2008', 'No immediate financial issue detected', true, NULL, 'INFO', '2026-09-03T09:56:00Z'),

  ('CLM-2009', 'Receipt processed', true, NULL, 'INFO', '2026-09-07T07:56:00Z'),
  ('CLM-2009', 'Required information detected', true, NULL, 'INFO', '2026-09-07T07:56:00Z'),
  ('CLM-2009', 'No immediate financial issue detected', true, NULL, 'INFO', '2026-09-07T07:56:00Z'),

  ('CLM-2010', 'Receipt processed', true, NULL, 'INFO', '2026-09-01T13:56:00Z'),
  ('CLM-2010', 'Required information detected', true, NULL, 'INFO', '2026-09-01T13:56:00Z'),
  ('CLM-2010', 'No immediate financial issue detected', true, NULL, 'INFO', '2026-09-01T13:56:00Z')
) AS v(claim_ref, check_name, passed, message, severity, checked_at)
ON c.claim_ref = v.claim_ref;

-- ---------------------------------------------------------------------------
-- 5. Duplicate matches (CLM-2002 is a high-confidence duplicate of CLM-1028)
-- ---------------------------------------------------------------------------
INSERT INTO duplicate_matches (claim_id, matched_claim_id, similarity_score, assessment, signals, detected_by, detected_at)
SELECT
  (SELECT id FROM claims WHERE claim_ref = 'CLM-2002'),
  (SELECT id FROM claims WHERE claim_ref = 'CLM-1028'),
  0.95,
  'High confidence duplicate',
  '["Same merchant (Amazon)", "Similar amount (₹2,450 vs ₹2,450)", "Similar expense date (1 day apart)", "Receipt text similarity detected"]'::jsonb,
  'RULE',
  '2026-09-08T10:32:00Z'::timestamptz;

-- CLM-1015 flagged (Zoom subscription - possible duplicate)
INSERT INTO duplicate_matches (claim_id, matched_claim_id, similarity_score, assessment, signals, detected_by, detected_at)
SELECT
  (SELECT id FROM claims WHERE claim_ref = 'CLM-1015'),
  (SELECT id FROM claims WHERE claim_ref = 'CLM-2006'),
  0.78,
  'Possible duplicate',
  '["Same merchant (Zoom)", "Identical amount (₹1,299)", "Same subscription period"]'::jsonb,
  'RULE',
  '2026-08-25T14:30:00Z'::timestamptz;

-- ---------------------------------------------------------------------------
-- 6. Status history
-- ---------------------------------------------------------------------------
INSERT INTO claim_status_history (claim_id, from_status, to_status, event_label, actor_name, occurred_at)
SELECT c.id, h.from_status::claim_status, h.to_status::claim_status, h.event_label, h.actor_name, h.occurred_at::timestamptz
FROM claims c
JOIN (VALUES
  -- CLM-1031
  ('CLM-1031', NULL,        'DRAFT',     'Claim created',                              'Vickey Kumar',  '2026-09-10T09:10:00Z'),
  ('CLM-1031', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Vickey Kumar',  '2026-09-10T09:15:00Z'),

  -- CLM-1028
  ('CLM-1028', NULL,        'DRAFT',     'Claim created',                              'Vickey Kumar',  '2026-09-09T11:15:00Z'),
  ('CLM-1028', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Vickey Kumar',  '2026-09-09T11:20:00Z'),
  ('CLM-1028', 'SUBMITTED', 'UNDER_REVIEW','Manager review started',                   'Rahul Sharma',  '2026-09-09T14:00:00Z'),

  -- CLM-1024
  ('CLM-1024', NULL,        'DRAFT',     'Claim created',                              'Vickey Kumar',  '2026-09-06T17:50:00Z'),
  ('CLM-1024', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Vickey Kumar',  '2026-09-06T18:00:00Z'),
  ('CLM-1024', 'SUBMITTED', 'UNDER_REVIEW','Manager review started',                   'Rahul Sharma',  '2026-09-07T09:00:00Z'),
  ('CLM-1024', 'UNDER_REVIEW','APPROVED','Claim approved by Rahul Sharma',             'Rahul Sharma',  '2026-09-07T10:30:00Z'),

  -- CLM-1021
  ('CLM-1021', NULL,        'DRAFT',     'Claim created',                              'Vickey Kumar',  '2026-09-03T14:00:00Z'),
  ('CLM-1021', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Vickey Kumar',  '2026-09-03T14:05:00Z'),
  ('CLM-1021', 'SUBMITTED', 'UNDER_REVIEW','Manager review started',                   'Rahul Sharma',  '2026-09-03T16:00:00Z'),
  ('CLM-1021', 'UNDER_REVIEW','REJECTED','Claim rejected — missing itemised receipt',  'Rahul Sharma',  '2026-09-03T17:00:00Z'),

  -- CLM-1018
  ('CLM-1018', NULL,        'DRAFT',     'Claim created',                              'Vickey Kumar',  '2026-08-28T09:55:00Z'),
  ('CLM-1018', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Vickey Kumar',  '2026-08-28T10:00:00Z'),
  ('CLM-1018', 'SUBMITTED', 'APPROVED',  'Claim approved by Rahul Sharma',             'Rahul Sharma',  '2026-08-29T09:00:00Z'),
  ('CLM-1018', 'APPROVED',  'READY_FOR_PAYMENT','Finance approved for payment',        'Anita Joshi',   '2026-08-30T11:00:00Z'),
  ('CLM-1018', 'READY_FOR_PAYMENT','PAID','Payment processed',                         'Anita Joshi',   '2026-09-01T15:00:00Z'),

  -- CLM-1015
  ('CLM-1015', NULL,        'DRAFT',     'Claim created',                              'Vickey Kumar',  '2026-08-25T11:25:00Z'),
  ('CLM-1015', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Vickey Kumar',  '2026-08-25T11:30:00Z'),
  ('CLM-1015', 'SUBMITTED', 'FLAGGED',   'Flagged as potential duplicate',             'System',        '2026-08-25T14:30:00Z'),

  -- CLM-1012
  ('CLM-1012', NULL,        'DRAFT',     'Claim created',                              'Vickey Kumar',  '2026-08-20T15:55:00Z'),
  ('CLM-1012', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Vickey Kumar',  '2026-08-20T16:00:00Z'),
  ('CLM-1012', 'SUBMITTED', 'APPROVED',  'Claim approved by Rahul Sharma',             'Rahul Sharma',  '2026-08-21T10:00:00Z'),
  ('CLM-1012', 'APPROVED',  'READY_FOR_PAYMENT','Finance queued for payment',          'Anita Joshi',   '2026-08-22T09:00:00Z'),

  -- CLM-DRAFT-1
  ('CLM-DRAFT-1', NULL,     'DRAFT',     'Claim created as draft',                     'Vickey Kumar',  '2026-09-10T14:00:00Z'),

  -- CLM-2001
  ('CLM-2001', NULL,        'DRAFT',     'Claim created',                              'Rahul Kumar',   '2026-09-10T09:10:00Z'),
  ('CLM-2001', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Rahul Kumar',   '2026-09-10T09:15:00Z'),

  -- CLM-2002
  ('CLM-2002', NULL,        'DRAFT',     'Claim created',                              'Neha Singh',    '2026-09-08T10:25:00Z'),
  ('CLM-2002', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Neha Singh',    '2026-09-08T10:30:00Z'),
  ('CLM-2002', 'SUBMITTED', 'FLAGGED',   'Duplicate check completed — possible duplicate flagged', 'System', '2026-09-08T10:32:00Z'),

  -- CLM-2003
  ('CLM-2003', NULL,        'DRAFT',     'Claim created',                              'Amit Sharma',   '2026-09-05T17:50:00Z'),
  ('CLM-2003', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Amit Sharma',   '2026-09-05T18:00:00Z'),
  ('CLM-2003', 'SUBMITTED', 'APPROVED',  'Manager approved — Rahul Sharma',            'Rahul Sharma',  '2026-09-06T09:30:00Z'),

  -- CLM-2004
  ('CLM-2004', NULL,        'DRAFT',     'Claim created',                              'Priya Desai',   '2026-09-02T12:55:00Z'),
  ('CLM-2004', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Priya Desai',   '2026-09-02T13:00:00Z'),
  ('CLM-2004', 'SUBMITTED', 'REJECTED',  'Manager rejected — Rahul Sharma',            'Rahul Sharma',  '2026-09-02T15:15:00Z'),

  -- CLM-2005
  ('CLM-2005', NULL,        'DRAFT',     'Claim created',                              'Karan Mehta',   '2026-08-25T09:50:00Z'),
  ('CLM-2005', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Karan Mehta',   '2026-08-25T10:00:00Z'),
  ('CLM-2005', 'SUBMITTED', 'APPROVED',  'Manager approved — Rahul Sharma',            'Rahul Sharma',  '2026-08-26T09:00:00Z'),
  ('CLM-2005', 'APPROVED',  'READY_FOR_PAYMENT','Finance verified — Anita Joshi',      'Anita Joshi',   '2026-08-27T11:00:00Z'),
  ('CLM-2005', 'READY_FOR_PAYMENT','PAID','Payment processed',                         'Anita Joshi',   '2026-08-29T15:00:00Z'),

  -- CLM-2006
  ('CLM-2006', NULL,        'DRAFT',     'Claim created',                              'Rahul Sharma',  '2026-09-01T11:25:00Z'),
  ('CLM-2006', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Rahul Sharma',  '2026-09-01T11:30:00Z'),

  -- CLM-2007
  ('CLM-2007', NULL,        'DRAFT',     'Claim created',                              'Rahul Kumar',   '2026-09-09T16:55:00Z'),
  ('CLM-2007', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Rahul Kumar',   '2026-09-09T17:00:00Z'),

  -- CLM-2008
  ('CLM-2008', NULL,        'DRAFT',     'Claim created',                              'Neha Singh',    '2026-09-03T09:55:00Z'),
  ('CLM-2008', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Neha Singh',    '2026-09-03T10:00:00Z'),
  ('CLM-2008', 'SUBMITTED', 'APPROVED',  'Manager approved — Rahul Sharma',            'Rahul Sharma',  '2026-09-04T09:00:00Z'),

  -- CLM-2009
  ('CLM-2009', NULL,        'DRAFT',     'Claim created',                              'Amit Sharma',   '2026-09-07T07:55:00Z'),
  ('CLM-2009', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Amit Sharma',   '2026-09-07T08:00:00Z'),
  ('CLM-2009', 'SUBMITTED', 'APPROVED',  'Manager approved — Rahul Sharma',            'Rahul Sharma',  '2026-09-08T09:00:00Z'),
  ('CLM-2009', 'APPROVED',  'READY_FOR_PAYMENT','Finance verified — Anita Joshi',      'Anita Joshi',   '2026-09-09T10:00:00Z'),

  -- CLM-2010
  ('CLM-2010', NULL,        'DRAFT',     'Claim created',                              'Priya Desai',   '2026-09-01T13:55:00Z'),
  ('CLM-2010', 'DRAFT',     'SUBMITTED', 'Claim submitted',                            'Priya Desai',   '2026-09-01T14:00:00Z'),
  ('CLM-2010', 'SUBMITTED', 'APPROVED',  'Manager approved — Rahul Sharma',            'Rahul Sharma',  '2026-09-02T09:00:00Z')
) AS h(claim_ref, from_status, to_status, event_label, actor_name, occurred_at)
ON c.claim_ref = h.claim_ref;

-- ---------------------------------------------------------------------------
-- 7. Manager reviews
-- ---------------------------------------------------------------------------
INSERT INTO manager_reviews (claim_id, manager_id, decision, comment, reviewed_at)
SELECT c.id,
  (SELECT id FROM users WHERE external_id = r.manager_ext_id),
  r.decision, r.comment, r.reviewed_at::timestamptz
FROM claims c
JOIN (VALUES
  ('CLM-1024', 'usr-mgr-001', 'APPROVED',  NULL,                                                              '2026-09-07T10:30:00Z'),
  ('CLM-1021', 'usr-mgr-001', 'REJECTED',  'Missing itemised receipt',                                        '2026-09-03T17:00:00Z'),
  ('CLM-1018', 'usr-mgr-001', 'APPROVED',  NULL,                                                              '2026-08-29T09:00:00Z'),
  ('CLM-1012', 'usr-mgr-001', 'APPROVED',  NULL,                                                              '2026-08-21T10:00:00Z'),
  ('CLM-2003', 'usr-mgr-001', 'APPROVED',  'Valid business travel expense. Approved.',                        '2026-09-06T09:30:00Z'),
  ('CLM-2004', 'usr-mgr-001', 'REJECTED',  'Receipt does not clearly show the purchased items. Personal meal during WFH is not reimbursable.', '2026-09-02T15:15:00Z'),
  ('CLM-2005', 'usr-mgr-001', 'APPROVED',  'Critical production deployment travel. Approved.',                '2026-08-26T09:00:00Z'),
  ('CLM-2008', 'usr-mgr-001', 'APPROVED',  'Confirmed business sprint travel. Approved.',                     '2026-09-04T09:00:00Z'),
  ('CLM-2009', 'usr-mgr-001', 'APPROVED',  'Legitimate client stay. Approved.',                               '2026-09-08T09:00:00Z'),
  ('CLM-2010', 'usr-mgr-001', 'APPROVED',  'Valid tool subscription for design team.',                        '2026-09-02T09:00:00Z')
) AS r(claim_ref, manager_ext_id, decision, comment, reviewed_at)
ON c.claim_ref = r.claim_ref;

-- ---------------------------------------------------------------------------
-- 8. Finance reviews
-- ---------------------------------------------------------------------------
INSERT INTO finance_reviews (claim_id, finance_user_id, decision, cleared, comment, reviewed_at)
SELECT c.id,
  (SELECT id FROM users WHERE external_id = 'usr-fin-001'),
  r.decision::finance_decision, r.cleared, r.comment, r.reviewed_at::timestamptz
FROM claims c
JOIN (VALUES
  ('CLM-1018', 'FINANCE_CLEARED',  true,  'Verified — legitimate business travel.',                                       '2026-08-30T11:00:00Z'),
  ('CLM-1012', 'FINANCE_CLEARED',  true,  'Invoices match. Cleared for payment.',                                         '2026-08-22T09:00:00Z'),
  ('CLM-2005', 'FINANCE_CLEARED',  true,  'Verified — legitimate business travel with complete documentation.',            '2026-08-27T11:00:00Z'),
  ('CLM-2009', 'FINANCE_CLEARED',  true,  'Invoices match. Cleared for payment.',                                         '2026-09-09T10:00:00Z'),
  ('CLM-2010', 'FINANCE_REJECTED', false, 'Company already has a team Adobe license. Personal subscription not reimbursable.', '2026-09-03T11:00:00Z'),
  ('CLM-2002', 'FINANCE_EXCEPTION',false, 'Possible duplicate — requires manual review.',                                  '2026-09-08T10:35:00Z')
) AS r(claim_ref, decision, cleared, comment, reviewed_at)
ON c.claim_ref = r.claim_ref;

-- ---------------------------------------------------------------------------
-- 9. Payments
-- ---------------------------------------------------------------------------
INSERT INTO payments (claim_id, payment_reference, amount, currency, processed_by, processed_at, notes)
SELECT c.id,
  p.payment_reference, p.amount, 'INR',
  (SELECT id FROM users WHERE external_id = 'usr-fin-001'),
  p.processed_at::timestamptz, p.notes
FROM claims c
JOIN (VALUES
  ('CLM-1018', 'PAY-2026-09-01-001', 8500.00, '2026-09-01T15:00:00Z', 'Train tickets — Delhi to Mumbai'),
  ('CLM-2005', 'PAY-2026-08-29-001', 8500.00, '2026-08-29T15:00:00Z', 'Flight tickets — Mumbai to Chennai')
) AS p(claim_ref, payment_reference, amount, processed_at, notes)
ON c.claim_ref = p.claim_ref;

-- =============================================================================
-- Seed data 002 complete.
-- You now have 9 users and 18 claims with full related data.
-- =============================================================================
