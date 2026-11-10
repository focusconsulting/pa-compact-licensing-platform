-- Migration: document scans and history (SCRUM-81)
-- Created: 2026-11-05
-- Backlog: D9 (documents), F-12

-- When the malware scan's result was recorded, and when the Worker last looked
-- for one; both NULL until then.
ALTER TABLE documents
    ADD COLUMN scanned_at      TIMESTAMPTZ,
    ADD COLUMN scan_checked_at TIMESTAMPTZ;

-- The Worker's queue of documents waiting for a scan result.
CREATE INDEX idx_documents_pending_scan ON documents (scan_checked_at NULLS FIRST)
    WHERE scan_status = 'pending';

SELECT create_history_table('documents');
