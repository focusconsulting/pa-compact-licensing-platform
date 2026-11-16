-- Migration: the sworn statement on a participation application (SCRUM-111)
-- Created: 2026-11-12
-- Backlog: L-03; Rule 3 §3.4(a)(1); Q-06

-- Set by submit and again by each resubmission, so only a draft goes without one.
ALTER TABLE participation_applications
    ADD COLUMN sworn_name TEXT,
    ADD COLUMN sworn_at   TIMESTAMPTZ,
    ADD CONSTRAINT chk_participation_applications_sworn CHECK (
        status = 'draft' OR (sworn_name IS NOT NULL AND sworn_at IS NOT NULL)
    );
