-- Test data migration — LOCAL_DEV only
-- This file is named with a timestamp 50 years in the future so it always runs last.
-- The migration runner skips this file in all environments except LOCAL_DEV.

-- Add local development seed data here
CREATE TABLE test
(
    id       SERIAL PRIMARY KEY,
    added_at TIMESTAMPTZ NOT NULL
);

INSERT INTO test (added_at)
VALUES ('1970-01-01T00:00:00.000Z');
