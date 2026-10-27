-- Migration: notification retry (SCRUM-80)
-- Created: 2026-10-27
-- Backlog: D7 (email is sent by the Worker from notifications rows)

-- A failed send waits until this time before its next attempt.
-- now() is evaluated once by ALTER TABLE, so existing rows are not rewritten.
ALTER TABLE notifications
    ADD COLUMN next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now();

DROP INDEX idx_notifications_pending;

CREATE INDEX idx_notifications_pending ON notifications (next_attempt_at) WHERE status = 'pending';
