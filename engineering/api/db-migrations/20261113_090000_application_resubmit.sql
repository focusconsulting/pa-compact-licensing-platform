-- Migration: the PA's reply to an information request, and accepting statements again to resubmit (SCRUM-111)
-- Created: 2026-11-13
-- Backlog: L-03; Rule 3 §3.7(a)(1)

-- What the PA wrote back to the state's request_note. History keeps each version sent.
ALTER TABLE participation_applications
    ADD COLUMN response_note TEXT CHECK (char_length(response_note) <= 4000);

-- A resubmission accepts each statement again, so the same version can be accepted more than once.
ALTER TABLE participation_application_attestations
    DROP CONSTRAINT participation_application_attestations_pkey,
    ADD PRIMARY KEY (participation_application_id, attestation_code, attestation_version, accepted_at);
