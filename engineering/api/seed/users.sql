-- Local users, loaded by `just seed` (local tooling, never a migration; constitution Principle IV).
-- Safe to rerun. Each user signs in through the local Cognito mock, which is seeded with the same emails.

INSERT INTO users (email, given_name, family_name, role, state_code, is_active, created_by)
SELECT v.email, v.given_name, v.family_name, v.role, v.state_code, v.is_active, system.id
FROM (VALUES ('gustavo.torrico@focusconsulting.io', 'Gustavo', 'Torrico', 'admin', NULL, TRUE),
             ('jamie.albinson@focusconsulting.io', 'Jamie', 'Albinson', 'admin', NULL, TRUE),
             ('michael.kalish@focusconsulting.io', 'Michael', 'Kalish', 'admin', NULL, TRUE),
             ('robert.antonucci@focusconsulting.io', 'Robert', 'Antonucci', 'admin', NULL, TRUE),
             ('inactive@example.com', 'Inactive', 'User', 'admin', NULL, FALSE),
             ('backfill@example.com', 'Backfill', 'User', 'compact_admin', NULL, TRUE))
         AS v (email, given_name, family_name, role, state_code, is_active)
CROSS JOIN (SELECT id FROM users WHERE email = 'system@pa-compact.invalid') AS system
ON CONFLICT (email) DO NOTHING;
