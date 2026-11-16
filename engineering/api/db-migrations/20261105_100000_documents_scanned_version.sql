-- Migration: the scanned version of a document (SCRUM-81)
-- Created: 2026-11-05
-- Backlog: D9 (documents), F-12

-- The object version the scan result belongs to. An upload link can be used
-- again until it expires, making a new version; only this one is ever served.
ALTER TABLE documents ADD COLUMN scanned_version_id TEXT;
