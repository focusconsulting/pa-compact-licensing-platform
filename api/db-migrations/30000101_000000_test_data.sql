-- Test data migration — LOCAL_DEV only

-- If you modify this file, you probably want to run `just infra` to reset your local db state.
-- The migration runner only runs this on LOCAL_DEV.
-- This file is named with a timestamp 50 years in the future so it always runs last.

-- Add local development seed data here
CREATE TABLE test
(
    id       SERIAL PRIMARY KEY,
    added_at TIMESTAMPTZ NOT NULL
);

INSERT INTO test (added_at)
VALUES ('1970-01-01T00:00:00.000Z');

SET CONSTRAINTS users_created_by_fkey DEFERRED;

INSERT INTO users (email, given_name, family_name, role, state_code, is_active, created_by)
VALUES ('gustavo.torrico@focusconsulting.io', 'Gustavo', 'Torrico', 'admin', NULL, TRUE, 1),
       ('jamie.albinson@focusconsulting.io', 'Jamie', 'Albinson', 'admin', NULL, TRUE, 1),
       ('michael.kalish@focusconsulting.io', 'Michael', 'Kalish', 'admin', NULL, TRUE, 1),
       ('robert.antonucci@focusconsulting.io', 'Robert', 'Antonucci', 'admin', NULL, TRUE, 1),
       ('inactive@example.com', 'Inactive', 'User', 'admin', NULL, FALSE, 1),
       ('backfill@example.com', 'Backfill', 'User', 'compact_admin', NULL, TRUE, 1)
;

SET CONSTRAINTS users_created_by_fkey IMMEDIATE;
