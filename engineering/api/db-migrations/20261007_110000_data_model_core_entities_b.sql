-- Migration: core entities, part B (F-02 phase 2b)
-- Created: 2026-10-07
-- Privilege requests, privileges, adverse actions, SII reports.
-- Conventions: engineering/adrs/0005-data-model-conventions.md
-- Dictionary:  engineering/docs/data-model.md

-- ---------------------------------------------------------------------------
-- privilege_requests: phase 2 of the workflow (FLOW-03, FLOW-06); owner: epic 8
-- ---------------------------------------------------------------------------

CREATE TABLE privilege_requests (
    id                            BIGSERIAL   PRIMARY KEY,
    public_id                     UUID        NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    participation_application_id  BIGINT      NOT NULL,
    practitioner_id               BIGINT      NOT NULL,
    remote_state_code             CHAR(2)     NOT NULL,
    qualifying_license_id         BIGINT      NOT NULL,
    -- 'withdrawn' rather than FLOW-06's 'abandoned': Rule 3 §3.7(b)(1) says
    -- "deemed incomplete and to have been withdrawn".
    status                        TEXT        NOT NULL DEFAULT 'pending_payment',
    -- The license expiry in effect when the PA applied; becomes the privilege's
    -- expiry (Rule 3 §3.5(a)).
    ql_expires_on_snapshot        DATE,
    -- Received by the remote state (Rule 3 §3.7(b)).
    submitted_at                  TIMESTAMPTZ,
    decided_at                    TIMESTAMPTZ,
    decided_by                    BIGINT,
    denial_reason_code            TEXT,
    denial_reason_detail          TEXT,
    withdrawn_at                  TIMESTAMPTZ,
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by                    BIGINT      NOT NULL,
    updated_at                    TIMESTAMPTZ NOT NULL,
    updated_by                    BIGINT      NOT NULL,
    CONSTRAINT chk_privilege_requests_status
        CHECK (status IN ('pending_payment', 'submitted', 'issued', 'denied', 'withdrawn')),
    CONSTRAINT chk_privilege_requests_submitted
        CHECK (status NOT IN ('submitted', 'issued', 'denied')
               OR (submitted_at IS NOT NULL AND ql_expires_on_snapshot IS NOT NULL)),
    CONSTRAINT chk_privilege_requests_decided
        CHECK (status NOT IN ('issued', 'denied') OR (decided_at IS NOT NULL AND decided_by IS NOT NULL)),
    CONSTRAINT chk_privilege_requests_denial_reason
        CHECK (status <> 'denied' OR denial_reason_code IS NOT NULL),
    CONSTRAINT chk_privilege_requests_withdrawn
        CHECK (status <> 'withdrawn' OR withdrawn_at IS NOT NULL),
    CONSTRAINT fk_privilege_requests_participation_application_id FOREIGN KEY (participation_application_id) REFERENCES participation_applications (id),
    CONSTRAINT fk_privilege_requests_practitioner_id FOREIGN KEY (practitioner_id) REFERENCES practitioners (id),
    CONSTRAINT fk_privilege_requests_remote_state_code FOREIGN KEY (remote_state_code) REFERENCES states (code),
    CONSTRAINT fk_privilege_requests_qualifying_license_id FOREIGN KEY (qualifying_license_id) REFERENCES qualifying_licenses (id),
    CONSTRAINT fk_privilege_requests_decided_by FOREIGN KEY (decided_by) REFERENCES users (id),
    CONSTRAINT fk_privilege_requests_denial_reason_code FOREIGN KEY (denial_reason_code) REFERENCES ref_denial_reasons (code),
    CONSTRAINT fk_privilege_requests_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_privilege_requests_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

-- One open request per practitioner and remote state.
CREATE UNIQUE INDEX uq_privilege_requests_one_open
    ON privilege_requests (practitioner_id, remote_state_code)
    WHERE status IN ('pending_payment', 'submitted');
-- The remote state's issuance queue.
CREATE INDEX idx_privilege_requests_rs_queue ON privilege_requests (remote_state_code, status);
CREATE INDEX idx_privilege_requests_participation_application_id ON privilege_requests (participation_application_id);
CREATE INDEX idx_privilege_requests_qualifying_license_id ON privilege_requests (qualifying_license_id);
CREATE INDEX idx_privilege_requests_decided_by ON privilege_requests (decided_by);
CREATE INDEX idx_privilege_requests_denial_reason_code ON privilege_requests (denial_reason_code);

-- ---------------------------------------------------------------------------
-- privileges: authored by the remote state (Rule 4 §4.3(d)); owner: epic 8
-- ---------------------------------------------------------------------------

CREATE TABLE privileges (
    id                          BIGSERIAL   PRIMARY KEY,
    public_id                   UUID        NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    privilege_request_id        BIGINT      NOT NULL UNIQUE,
    practitioner_id             BIGINT      NOT NULL,
    remote_state_code           CHAR(2)     NOT NULL,
    -- "the qualifying license used to apply for the privilege" (Rule 3 §3.5(a)).
    qualifying_license_id       BIGINT      NOT NULL,
    -- PA-{state}-{n}.
    privilege_number            TEXT        NOT NULL UNIQUE,
    -- "other unique privilege identifier issued by the Remote State" (Rule 4 §4.3(d)(1)).
    state_privilege_identifier  TEXT,
    issued_at                   TIMESTAMPTZ NOT NULL,
    -- Pinned at the request and inclusive; status is computed, never stored (D1).
    expires_on                  DATE        NOT NULL,
    administrator_status        TEXT        NOT NULL DEFAULT 'active',
    deactivation_reason         TEXT,
    deactivated_at              TIMESTAMPTZ,
    deactivation_note           TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by                  BIGINT      NOT NULL,
    updated_at                  TIMESTAMPTZ NOT NULL,
    updated_by                  BIGINT      NOT NULL,
    CONSTRAINT chk_privileges_administrator_status CHECK (administrator_status IN ('active', 'inactive')),
    -- sql_changed: Rule 3 §3.6(d), "any existing compact privilege(s) held shall terminate".
    -- An expired or lapsed license is qualifying_license_inactive (FLOW-05).
    -- commission_deactivated: the Commission's override (D-01, epic 10).
    CONSTRAINT chk_privileges_deactivation_reason CHECK (deactivation_reason IN
        ('qualifying_license_adverse_action', 'eligibility_withdrawn', 'qualifying_license_inactive',
         'qualifying_license_terminated', 'sql_changed', 'state_deactivated', 'commission_deactivated')),
    CONSTRAINT chk_privileges_inactive_has_reason
        CHECK ((administrator_status = 'inactive') = (deactivation_reason IS NOT NULL)),
    CONSTRAINT chk_privileges_inactive_has_time
        CHECK ((administrator_status = 'inactive') = (deactivated_at IS NOT NULL)),
    CONSTRAINT fk_privileges_privilege_request_id FOREIGN KEY (privilege_request_id) REFERENCES privilege_requests (id),
    CONSTRAINT fk_privileges_practitioner_id FOREIGN KEY (practitioner_id) REFERENCES practitioners (id),
    CONSTRAINT fk_privileges_remote_state_code FOREIGN KEY (remote_state_code) REFERENCES states (code),
    CONSTRAINT fk_privileges_qualifying_license_id FOREIGN KEY (qualifying_license_id) REFERENCES qualifying_licenses (id),
    CONSTRAINT fk_privileges_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_privileges_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE INDEX idx_privileges_practitioner_id ON privileges (practitioner_id);
CREATE INDEX idx_privileges_remote_state_code ON privileges (remote_state_code);
CREATE INDEX idx_privileges_qualifying_license_id ON privileges (qualifying_license_id);

-- The last privilege number issued in each remote state (FLOW-03: PA-{state}-{n}).
CREATE TABLE privilege_number_sequences (
    state_code   CHAR(2)     PRIMARY KEY,
    last_number  INTEGER     NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by   BIGINT      NOT NULL,
    updated_at   TIMESTAMPTZ NOT NULL,
    updated_by   BIGINT      NOT NULL,
    CONSTRAINT chk_privilege_number_sequences_last_number CHECK (last_number > 0),
    CONSTRAINT fk_privilege_number_sequences_state_code FOREIGN KEY (state_code) REFERENCES states (code),
    CONSTRAINT fk_privilege_number_sequences_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_privilege_number_sequences_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

-- Returns the next privilege number for a remote state, e.g. PA-KS-000123. The
-- upsert locks that state's row, so concurrent issuances in one state never share
-- a number and issuances in different states never wait on each other.
CREATE FUNCTION next_privilege_number(remote_state_code CHAR(2), actor_user_id BIGINT) RETURNS TEXT
    LANGUAGE sql AS
$$
INSERT INTO privilege_number_sequences AS seq (state_code, last_number, created_by)
VALUES (remote_state_code, 1, actor_user_id)
ON CONFLICT (state_code) DO UPDATE
    SET last_number = seq.last_number + 1, updated_by = actor_user_id
RETURNING 'PA-' || seq.state_code || '-'
    || lpad(seq.last_number::text, greatest(6, length(seq.last_number::text)), '0')
$$;

-- ---------------------------------------------------------------------------
-- adverse_actions (Rule 4 §4.4(a)-(b)); owner: epic 9
-- ---------------------------------------------------------------------------

CREATE TABLE adverse_actions (
    id                     BIGSERIAL   PRIMARY KEY,
    public_id              UUID        NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    practitioner_id        BIGINT      NOT NULL,
    reporting_state_code   CHAR(2)     NOT NULL,
    against                TEXT        NOT NULL,
    qualifying_license_id  BIGINT,
    privilege_id           BIGINT,
    action_type_code       TEXT        NOT NULL,
    -- "a summary of the action taken or a copy of the order" (Rule 4 §4.4(b)(1)).
    summary                TEXT,
    order_document_id      BIGINT,
    ordered_on             DATE        NOT NULL,
    effective_from         DATE        NOT NULL,
    -- NULL while the action is in force; inclusive.
    effective_until        DATE,
    is_emergency           BOOLEAN     NOT NULL DEFAULT FALSE,
    -- Non-public actions never reach public verification (Rule 4 §4.5(c)-(d)).
    is_public              BOOLEAN     NOT NULL DEFAULT FALSE,
    -- Measures the reporting window (Rule 4 §4.4(b)(2)).
    reported_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by             BIGINT      NOT NULL,
    updated_at             TIMESTAMPTZ NOT NULL,
    updated_by             BIGINT      NOT NULL,
    CONSTRAINT chk_adverse_actions_against CHECK (against IN ('qualifying_license', 'privilege')),
    CONSTRAINT chk_adverse_actions_target CHECK (
        (against = 'qualifying_license' AND qualifying_license_id IS NOT NULL AND privilege_id IS NULL)
        OR (against = 'privilege' AND privilege_id IS NOT NULL AND qualifying_license_id IS NULL)),
    CONSTRAINT chk_adverse_actions_summary_or_order
        CHECK (summary IS NOT NULL OR order_document_id IS NOT NULL),
    CONSTRAINT chk_adverse_actions_effective_dates
        CHECK (effective_until IS NULL OR effective_until >= effective_from),
    CONSTRAINT fk_adverse_actions_practitioner_id FOREIGN KEY (practitioner_id) REFERENCES practitioners (id),
    CONSTRAINT fk_adverse_actions_reporting_state_code FOREIGN KEY (reporting_state_code) REFERENCES states (code),
    CONSTRAINT fk_adverse_actions_qualifying_license_id FOREIGN KEY (qualifying_license_id) REFERENCES qualifying_licenses (id),
    CONSTRAINT fk_adverse_actions_privilege_id FOREIGN KEY (privilege_id) REFERENCES privileges (id),
    CONSTRAINT fk_adverse_actions_action_type_code FOREIGN KEY (action_type_code) REFERENCES ref_adverse_action_types (code),
    CONSTRAINT fk_adverse_actions_order_document_id FOREIGN KEY (order_document_id) REFERENCES documents (id),
    CONSTRAINT fk_adverse_actions_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_adverse_actions_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE INDEX idx_adverse_actions_practitioner_id ON adverse_actions (practitioner_id);
CREATE INDEX idx_adverse_actions_qualifying_license_id ON adverse_actions (qualifying_license_id);
CREATE INDEX idx_adverse_actions_privilege_id ON adverse_actions (privilege_id);
CREATE INDEX idx_adverse_actions_reporting_state_code ON adverse_actions (reporting_state_code);
CREATE INDEX idx_adverse_actions_action_type_code ON adverse_actions (action_type_code);
CREATE INDEX idx_adverse_actions_order_document_id ON adverse_actions (order_document_id);

-- Optional NPDB categories (Q-17); not in the adopted rule text.
CREATE TABLE adverse_action_npdb_categories (
    adverse_action_id   BIGINT      NOT NULL,
    npdb_category_code  TEXT        NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          BIGINT      NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL,
    updated_by          BIGINT      NOT NULL,
    PRIMARY KEY (adverse_action_id, npdb_category_code),
    CONSTRAINT fk_adverse_action_npdb_categories_adverse_action_id FOREIGN KEY (adverse_action_id) REFERENCES adverse_actions (id),
    CONSTRAINT fk_adverse_action_npdb_categories_npdb_category_code FOREIGN KEY (npdb_category_code) REFERENCES ref_npdb_categories (code),
    CONSTRAINT fk_adverse_action_npdb_categories_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_adverse_action_npdb_categories_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE INDEX idx_adverse_action_npdb_categories_npdb_category_code
    ON adverse_action_npdb_categories (npdb_category_code);

-- ---------------------------------------------------------------------------
-- sii_reports (Rule 4 §4.4(c)-(d)); states and Commission only (ML §8.C); owner: epic 9
-- ---------------------------------------------------------------------------

CREATE TABLE sii_reports (
    id                            BIGSERIAL   PRIMARY KEY,
    public_id                     UUID        NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    practitioner_id               BIGINT      NOT NULL,
    -- The state of qualifying license or a remote state.
    reporting_state_code          CHAR(2)     NOT NULL,
    qualifying_license_id         BIGINT,
    privilege_id                  BIGINT,
    description                   TEXT        NOT NULL,
    contact_name                  TEXT        NOT NULL,
    contact_email                 TEXT,
    contact_phone                 TEXT,
    -- "a copy of any public complaint" (Rule 4 §4.4(d)(1)).
    public_complaint_document_id  BIGINT,
    -- Starts the five-business-day window (Rule 4 §4.4(d)(2)).
    determined_on                 DATE        NOT NULL,
    reported_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at                     TIMESTAMPTZ,
    closed_by                     BIGINT,
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by                    BIGINT      NOT NULL,
    updated_at                    TIMESTAMPTZ NOT NULL,
    updated_by                    BIGINT      NOT NULL,
    CONSTRAINT chk_sii_reports_contact CHECK (contact_email IS NOT NULL OR contact_phone IS NOT NULL),
    CONSTRAINT chk_sii_reports_closed CHECK ((closed_at IS NULL) = (closed_by IS NULL)),
    CONSTRAINT fk_sii_reports_practitioner_id FOREIGN KEY (practitioner_id) REFERENCES practitioners (id),
    CONSTRAINT fk_sii_reports_reporting_state_code FOREIGN KEY (reporting_state_code) REFERENCES states (code),
    CONSTRAINT fk_sii_reports_qualifying_license_id FOREIGN KEY (qualifying_license_id) REFERENCES qualifying_licenses (id),
    CONSTRAINT fk_sii_reports_privilege_id FOREIGN KEY (privilege_id) REFERENCES privileges (id),
    CONSTRAINT fk_sii_reports_public_complaint_document_id FOREIGN KEY (public_complaint_document_id) REFERENCES documents (id),
    CONSTRAINT fk_sii_reports_closed_by FOREIGN KEY (closed_by) REFERENCES users (id),
    CONSTRAINT fk_sii_reports_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_sii_reports_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE INDEX idx_sii_reports_practitioner_id ON sii_reports (practitioner_id);
CREATE INDEX idx_sii_reports_reporting_state_code ON sii_reports (reporting_state_code);
CREATE INDEX idx_sii_reports_qualifying_license_id ON sii_reports (qualifying_license_id);
CREATE INDEX idx_sii_reports_privilege_id ON sii_reports (privilege_id);
CREATE INDEX idx_sii_reports_public_complaint_document_id ON sii_reports (public_complaint_document_id);
CREATE INDEX idx_sii_reports_closed_by ON sii_reports (closed_by);

-- ---------------------------------------------------------------------------
-- Audit-column triggers and history tables
-- ---------------------------------------------------------------------------

SELECT add_audit_columns_trigger(t)
FROM unnest(ARRAY ['privilege_requests', 'privileges', 'privilege_number_sequences', 'adverse_actions',
                   'adverse_action_npdb_categories', 'sii_reports']) AS t;

SELECT create_history_table(t)
FROM unnest(ARRAY ['privilege_requests', 'privileges', 'adverse_actions', 'sii_reports']) AS t;
