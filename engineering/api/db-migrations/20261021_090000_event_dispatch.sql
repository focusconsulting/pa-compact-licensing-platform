-- Migration: outbox dispatch (SCRUM-78)
-- Created: 2026-10-21
-- Decision: engineering/adrs/0012-outbox-dispatcher.md

-- Set when the dispatcher has created a delivery row for each handler of the
-- event. A handler registered later never receives earlier events.
ALTER TABLE domain_events
    ADD COLUMN dispatched_at TIMESTAMPTZ;

CREATE INDEX idx_domain_events_undispatched ON domain_events (id) WHERE dispatched_at IS NULL;

-- A failed delivery waits until this time before its next attempt.
-- now() is evaluated once by ALTER TABLE, so existing rows are not rewritten.
ALTER TABLE domain_event_deliveries
    ADD COLUMN next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now();

DROP INDEX idx_domain_event_deliveries_pending;

CREATE INDEX idx_domain_event_deliveries_pending
    ON domain_event_deliveries (next_attempt_at)
    WHERE handled_at IS NULL AND dead_lettered_at IS NULL;
