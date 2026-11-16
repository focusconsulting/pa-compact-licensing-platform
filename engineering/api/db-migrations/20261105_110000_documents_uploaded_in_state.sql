-- Migration: the state a document was uploaded for (SCRUM-81)
-- Created: 2026-11-05
-- Backlog: D9 (documents), F-12

-- Set from the route's state when state staff upload; NULL for a PA's upload.
-- Scopes a document no record owns yet to that state, rather than to the
-- uploader's home state, which can differ (a grant in another state) or change.
ALTER TABLE documents ADD COLUMN uploaded_in_state TEXT REFERENCES states (code);

CREATE INDEX idx_documents_uploaded_in_state ON documents (uploaded_in_state);
