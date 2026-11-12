-- Migration: the sworn statement on a participation application (SCRUM-111)
-- Created: 2026-11-12
-- Backlog: L-03; Rule 3 §3.4(a)(1); Q-06

-- Set by submit and again by each resubmission. No CHECK: rows made before this
-- migration have none, so the submit route requires it instead.
ALTER TABLE participation_applications
    ADD COLUMN sworn_name TEXT,
    ADD COLUMN sworn_at   TIMESTAMPTZ,
    ADD COLUMN sworn_ip   TEXT;
