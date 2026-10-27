-- Migration: state contacts (SCRUM-80)
-- Created: 2026-10-27
-- Backlog: F-11 (which event emails whom); recipients by purpose, per FLOW-07

-- The mailboxes a state wants its notifications sent to, by purpose:
-- applications (as state of qualifying license), privileges (as remote state),
-- and discipline (adverse actions and SII).
CREATE TABLE state_contacts (
    id          BIGSERIAL   PRIMARY KEY,
    state_code  TEXT        NOT NULL,
    purpose     TEXT        NOT NULL,
    email       TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  BIGINT      NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL,
    updated_by  BIGINT      NOT NULL,
    CONSTRAINT chk_state_contacts_purpose CHECK (purpose IN ('applications', 'privileges', 'discipline')),
    CONSTRAINT uq_state_contacts_state_code_purpose_email UNIQUE (state_code, purpose, email),
    CONSTRAINT fk_state_contacts_state_code FOREIGN KEY (state_code) REFERENCES states (code),
    CONSTRAINT fk_state_contacts_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_state_contacts_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

SELECT add_audit_columns_trigger('state_contacts');
SELECT create_history_table('state_contacts');
