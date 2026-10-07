-- Migration: core entities, part A (F-02 phase 2a)
-- Created: 2026-10-07
-- Practitioners and SSNs, documents, qualifying licenses, participation applications.
-- Conventions: engineering/adrs/0005-data-model-conventions.md
-- Dictionary:  engineering/docs/data-model.md

-- ---------------------------------------------------------------------------
-- Convention helpers, reusable by any epic that adds an entity table
-- ---------------------------------------------------------------------------

-- Adds the audit-columns trigger to a table (ADR-0005).
CREATE FUNCTION add_audit_columns_trigger(target TEXT) RETURNS void
    LANGUAGE plpgsql AS
$$
BEGIN
    EXECUTE format(
        'CREATE TRIGGER %I BEFORE INSERT OR UPDATE ON %I '
        'FOR EACH ROW EXECUTE FUNCTION set_audit_columns()',
        'trg_' || target || '_audit_columns', target);
END
$$;

-- Creates <target>_history in the shape F-05's history.write() fills, append-only (ADR-0005, ADR-0008).
CREATE FUNCTION create_history_table(target TEXT) RETURNS void
    LANGUAGE plpgsql AS
$$
DECLARE
    history TEXT := target || '_history';
BEGIN
    EXECUTE format(
        'CREATE TABLE %1$I ('
        '    id            BIGSERIAL   PRIMARY KEY,'
        '    entity_id     BIGINT      NOT NULL,'
        '    changed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),'
        '    changed_by    BIGINT      NOT NULL,'
        '    effective_at  TIMESTAMPTZ,'
        '    previous      JSONB,'
        '    updated       JSONB,'
        '    removed       JSONB,'
        '    CONSTRAINT %2$I FOREIGN KEY (entity_id) REFERENCES %3$I (id),'
        '    CONSTRAINT %4$I FOREIGN KEY (changed_by) REFERENCES users (id)'
        ')',
        history, 'fk_' || history || '_entity_id', target, 'fk_' || history || '_changed_by');
    EXECUTE format('CREATE INDEX %I ON %I (entity_id, changed_at)', 'idx_' || history || '_entity', history);
    EXECUTE format('CREATE INDEX %I ON %I (changed_by)', 'idx_' || history || '_changed_by', history);
    EXECUTE format(
        'CREATE TRIGGER %I BEFORE UPDATE OR DELETE ON %I '
        'FOR EACH ROW EXECUTE FUNCTION prevent_mutation()',
        'trg_' || history || '_append_only', history);
END
$$;

-- ---------------------------------------------------------------------------
-- practitioners: the uniform data set (Rule 4 §4.3(c)); a shared root
-- ---------------------------------------------------------------------------

CREATE TABLE practitioners (
    id                              BIGSERIAL   PRIMARY KEY,
    public_id                       UUID        NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    user_id                         BIGINT      NOT NULL UNIQUE,
    -- Set when an application becomes eligible.
    current_sql_state_code          CHAR(2),

    legal_first_name                TEXT,                 -- §4.3(c)(1)
    legal_middle_name               TEXT,
    legal_last_name                 TEXT,
    name_suffix                     TEXT,
    sex_code                        TEXT,                 -- §4.3(c)(3); values per Q-10
    date_of_birth                   DATE,                 -- §4.3(c)(4)
    residence_line1                 TEXT,                 -- §4.3(c)(6), primary residence of record
    residence_line2                 TEXT,
    residence_city                  TEXT,
    residence_region                TEXT,
    residence_postal_code           TEXT,
    residence_country_code          TEXT,
    phone                           TEXT,                 -- §4.3(c)(7)
    correspondence_email            TEXT,                 -- §4.3(c)(8)
    pa_program_name                 TEXT,                 -- §4.3(c)(9)
    pa_program_graduation_year      SMALLINT,
    nccpa_certification_number      TEXT,                 -- §4.3(c)(10)
    nccpa_certification_status      TEXT,
    nccpa_certification_expires_on  DATE,
    -- Not in the adopted uniform data set: optional and never verified.
    npi                             TEXT,

    -- Provenance per field group: who entered it, and which state verified it when
    -- (SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance).
    identity_entered_by             BIGINT,
    identity_verified_by_state      CHAR(2),
    identity_verified_at            TIMESTAMPTZ,
    residence_entered_by            BIGINT,
    residence_verified_by_state     CHAR(2),
    residence_verified_at           TIMESTAMPTZ,
    contact_entered_by              BIGINT,
    contact_verified_by_state       CHAR(2),
    contact_verified_at             TIMESTAMPTZ,
    education_entered_by            BIGINT,
    education_verified_by_state     CHAR(2),
    education_verified_at           TIMESTAMPTZ,
    certification_entered_by        BIGINT,
    certification_verified_by_state CHAR(2),
    certification_verified_at       TIMESTAMPTZ,

    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by                      BIGINT      NOT NULL,
    updated_at                      TIMESTAMPTZ NOT NULL,
    updated_by                      BIGINT      NOT NULL,

    CONSTRAINT chk_practitioners_graduation_year
        CHECK (pa_program_graduation_year IS NULL OR pa_program_graduation_year BETWEEN 1950 AND 2100),
    CONSTRAINT chk_practitioners_identity_verified
        CHECK ((identity_verified_by_state IS NULL) = (identity_verified_at IS NULL)),
    CONSTRAINT chk_practitioners_residence_verified
        CHECK ((residence_verified_by_state IS NULL) = (residence_verified_at IS NULL)),
    CONSTRAINT chk_practitioners_contact_verified
        CHECK ((contact_verified_by_state IS NULL) = (contact_verified_at IS NULL)),
    CONSTRAINT chk_practitioners_education_verified
        CHECK ((education_verified_by_state IS NULL) = (education_verified_at IS NULL)),
    CONSTRAINT chk_practitioners_certification_verified
        CHECK ((certification_verified_by_state IS NULL) = (certification_verified_at IS NULL)),

    CONSTRAINT fk_practitioners_user_id FOREIGN KEY (user_id) REFERENCES users (id),
    CONSTRAINT fk_practitioners_current_sql_state_code FOREIGN KEY (current_sql_state_code) REFERENCES states (code),
    CONSTRAINT fk_practitioners_sex_code FOREIGN KEY (sex_code) REFERENCES ref_sex (code),
    CONSTRAINT fk_practitioners_identity_entered_by FOREIGN KEY (identity_entered_by) REFERENCES users (id),
    CONSTRAINT fk_practitioners_identity_verified_by_state FOREIGN KEY (identity_verified_by_state) REFERENCES states (code),
    CONSTRAINT fk_practitioners_residence_entered_by FOREIGN KEY (residence_entered_by) REFERENCES users (id),
    CONSTRAINT fk_practitioners_residence_verified_by_state FOREIGN KEY (residence_verified_by_state) REFERENCES states (code),
    CONSTRAINT fk_practitioners_contact_entered_by FOREIGN KEY (contact_entered_by) REFERENCES users (id),
    CONSTRAINT fk_practitioners_contact_verified_by_state FOREIGN KEY (contact_verified_by_state) REFERENCES states (code),
    CONSTRAINT fk_practitioners_education_entered_by FOREIGN KEY (education_entered_by) REFERENCES users (id),
    CONSTRAINT fk_practitioners_education_verified_by_state FOREIGN KEY (education_verified_by_state) REFERENCES states (code),
    CONSTRAINT fk_practitioners_certification_entered_by FOREIGN KEY (certification_entered_by) REFERENCES users (id),
    CONSTRAINT fk_practitioners_certification_verified_by_state FOREIGN KEY (certification_verified_by_state) REFERENCES states (code),
    CONSTRAINT fk_practitioners_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_practitioners_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE INDEX idx_practitioners_current_sql_state_code ON practitioners (current_sql_state_code);
CREATE INDEX idx_practitioners_legal_last_name ON practitioners (lower(legal_last_name));

-- ---------------------------------------------------------------------------
-- practitioner_ssn: restricted tier (ADR-0007); audited, so no history table
-- ---------------------------------------------------------------------------

CREATE TABLE practitioner_ssn (
    id               BIGSERIAL   PRIMARY KEY,
    practitioner_id  BIGINT      NOT NULL UNIQUE,
    -- AES-256-GCM, nonce prepended; encrypted by the application.
    ssn_ciphertext   BYTEA       NOT NULL,
    ssn_key_version  SMALLINT    NOT NULL,
    -- Keyed HMAC-SHA-256: detects a second account with the same SSN.
    ssn_lookup_hash  BYTEA       NOT NULL UNIQUE,
    ssn_last4        CHAR(4)     NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by       BIGINT      NOT NULL,
    updated_at       TIMESTAMPTZ NOT NULL,
    updated_by       BIGINT      NOT NULL,
    CONSTRAINT chk_practitioner_ssn_last4 CHECK (ssn_last4 ~ '^[0-9]{4}$'),
    CONSTRAINT chk_practitioner_ssn_key_version CHECK (ssn_key_version > 0),
    CONSTRAINT fk_practitioner_ssn_practitioner_id FOREIGN KEY (practitioner_id) REFERENCES practitioners (id),
    CONSTRAINT fk_practitioner_ssn_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_practitioner_ssn_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

-- ---------------------------------------------------------------------------
-- documents: files in object storage with a polymorphic owner (D9)
-- ---------------------------------------------------------------------------

CREATE TABLE documents (
    id            BIGSERIAL   PRIMARY KEY,
    public_id     UUID        NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    owner_type    TEXT        NOT NULL,
    owner_id      BIGINT      NOT NULL,
    -- What the document is; free text until Q-07 settles the list.
    kind          TEXT        NOT NULL,
    storage_key   TEXT        NOT NULL UNIQUE,
    file_name     TEXT        NOT NULL,
    content_type  TEXT        NOT NULL,
    size_bytes    BIGINT      NOT NULL,
    scan_status   TEXT        NOT NULL DEFAULT 'pending',
    -- created_by is the uploader.
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    BIGINT      NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL,
    updated_by    BIGINT      NOT NULL,
    CONSTRAINT chk_documents_owner_type CHECK (owner_type IN
        ('practitioner', 'participation_application', 'privilege_request', 'adverse_action', 'sii_report')),
    CONSTRAINT chk_documents_scan_status CHECK (scan_status IN ('pending', 'clean', 'infected', 'error')),
    CONSTRAINT chk_documents_size_bytes CHECK (size_bytes >= 0),
    CONSTRAINT fk_documents_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_documents_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE INDEX idx_documents_owner ON documents (owner_type, owner_id);

-- ---------------------------------------------------------------------------
-- qualifying_licenses: SQL-authored (Rule 4 §4.3(c)(11)); owner: epic 7
-- ---------------------------------------------------------------------------

CREATE TABLE qualifying_licenses (
    id                     BIGSERIAL   PRIMARY KEY,
    public_id              UUID        NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    -- NULL until linked: an uploaded license (epic 13) may arrive before the PA applies.
    practitioner_id        BIGINT,
    state_code             CHAR(2)     NOT NULL,
    license_number         TEXT        NOT NULL,
    -- Reinstatement sets this back to active (FLOW-05).
    state_reported_status  TEXT        NOT NULL,
    status_effective_on    DATE        NOT NULL,
    issued_on              DATE,
    expires_on             DATE,
    -- Rule 3 §3.4(a)(2): only a full and unrestricted license qualifies.
    is_unrestricted        BOOLEAN     NOT NULL,
    -- Voluntary termination by the PA (Rule 3 §3.5(a), §3.6(a)).
    terminated_on          DATE,
    source                 TEXT        NOT NULL DEFAULT 'manual',
    verified_by            BIGINT,
    verified_at            TIMESTAMPTZ,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by             BIGINT      NOT NULL,
    updated_at             TIMESTAMPTZ NOT NULL,
    updated_by             BIGINT      NOT NULL,
    CONSTRAINT uq_qualifying_licenses_state_number UNIQUE (state_code, license_number),
    CONSTRAINT chk_qualifying_licenses_state_reported_status
        CHECK (state_reported_status IN ('active', 'expired', 'lapsed', 'inactive', 'terminated')),
    CONSTRAINT chk_qualifying_licenses_source CHECK (source IN ('manual', 'upload', 'api')),
    CONSTRAINT chk_qualifying_licenses_dates CHECK (issued_on IS NULL OR expires_on IS NULL OR issued_on <= expires_on),
    CONSTRAINT chk_qualifying_licenses_verified CHECK ((verified_by IS NULL) = (verified_at IS NULL)),
    CONSTRAINT fk_qualifying_licenses_practitioner_id FOREIGN KEY (practitioner_id) REFERENCES practitioners (id),
    CONSTRAINT fk_qualifying_licenses_state_code FOREIGN KEY (state_code) REFERENCES states (code),
    CONSTRAINT fk_qualifying_licenses_verified_by FOREIGN KEY (verified_by) REFERENCES users (id),
    CONSTRAINT fk_qualifying_licenses_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_qualifying_licenses_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE INDEX idx_qualifying_licenses_practitioner_id ON qualifying_licenses (practitioner_id);
CREATE INDEX idx_qualifying_licenses_verified_by ON qualifying_licenses (verified_by);

-- ---------------------------------------------------------------------------
-- participation_applications: phase 1 of the workflow (FLOW-02, FLOW-06); owner: epic 6
-- ---------------------------------------------------------------------------

CREATE TABLE participation_applications (
    id                             BIGSERIAL   PRIMARY KEY,
    public_id                      UUID        NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    practitioner_id                BIGINT      NOT NULL,
    -- change_sql: designating a new state of qualifying license (Rule 3 §3.6(a)).
    kind                           TEXT        NOT NULL DEFAULT 'initial',
    -- No SQL basis column: adopted Rule 3 §3.4(a)(2) dropped the draft's basis tests.
    sql_state_code                 CHAR(2)     NOT NULL,
    qualifying_license_id          BIGINT,
    status                         TEXT        NOT NULL DEFAULT 'draft',
    -- Received by the SQL; starts the 60-day completeness clock (Rule 3 §3.7(a)).
    opened_at                      TIMESTAMPTZ,
    request_note                   TEXT,                 -- D15
    license_verified_at            TIMESTAMPTZ,
    license_verified_by            BIGINT,
    -- The date only; a result is never stored (Rule 4 §4.2).
    cbc_completed_on               DATE,
    decided_at                     TIMESTAMPTZ,
    decided_by                     BIGINT,
    denial_reason_code             TEXT,
    denial_reason_detail           TEXT,
    withdrawn_at                   TIMESTAMPTZ,
    eligibility_withdrawn_at       TIMESTAMPTZ,          -- Rule 3 §3.9(b)
    eligibility_withdrawal_reason  TEXT,
    created_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by                     BIGINT      NOT NULL,
    updated_at                     TIMESTAMPTZ NOT NULL,
    updated_by                     BIGINT      NOT NULL,
    CONSTRAINT chk_participation_applications_kind CHECK (kind IN ('initial', 'change_sql')),
    CONSTRAINT chk_participation_applications_status CHECK (status IN
        ('draft', 'submitted', 'info_requested', 'eligible', 'denied', 'withdrawn', 'eligibility_withdrawn')),
    CONSTRAINT chk_participation_applications_opened
        CHECK (status = 'draft' OR opened_at IS NOT NULL),
    CONSTRAINT chk_participation_applications_decided
        CHECK (status NOT IN ('eligible', 'denied', 'eligibility_withdrawn')
               OR (decided_at IS NOT NULL AND decided_by IS NOT NULL)),
    -- FLOW-02: a decision of eligible needs the license verified and the background check completed.
    CONSTRAINT chk_participation_applications_eligible_requirements
        CHECK (status NOT IN ('eligible', 'eligibility_withdrawn')
               OR (license_verified_at IS NOT NULL AND cbc_completed_on IS NOT NULL)),
    CONSTRAINT chk_participation_applications_denial_reason
        CHECK (status <> 'denied' OR denial_reason_code IS NOT NULL),
    CONSTRAINT chk_participation_applications_withdrawn
        CHECK (status <> 'withdrawn' OR withdrawn_at IS NOT NULL),
    CONSTRAINT chk_participation_applications_eligibility_withdrawn
        CHECK (status <> 'eligibility_withdrawn'
               OR (eligibility_withdrawn_at IS NOT NULL AND eligibility_withdrawal_reason IS NOT NULL)),
    CONSTRAINT chk_participation_applications_license_verified
        CHECK ((license_verified_at IS NULL) = (license_verified_by IS NULL)),
    CONSTRAINT fk_participation_applications_practitioner_id FOREIGN KEY (practitioner_id) REFERENCES practitioners (id),
    CONSTRAINT fk_participation_applications_sql_state_code FOREIGN KEY (sql_state_code) REFERENCES states (code),
    CONSTRAINT fk_participation_applications_qualifying_license_id FOREIGN KEY (qualifying_license_id) REFERENCES qualifying_licenses (id),
    CONSTRAINT fk_participation_applications_license_verified_by FOREIGN KEY (license_verified_by) REFERENCES users (id),
    CONSTRAINT fk_participation_applications_decided_by FOREIGN KEY (decided_by) REFERENCES users (id),
    CONSTRAINT fk_participation_applications_denial_reason_code FOREIGN KEY (denial_reason_code) REFERENCES ref_denial_reasons (code),
    CONSTRAINT fk_participation_applications_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_participation_applications_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

-- One open application per practitioner.
CREATE UNIQUE INDEX uq_participation_applications_one_open
    ON participation_applications (practitioner_id)
    WHERE status IN ('draft', 'submitted', 'info_requested');
-- The SQL's review queue.
CREATE INDEX idx_participation_applications_sql_queue ON participation_applications (sql_state_code, status);
CREATE INDEX idx_participation_applications_practitioner_id ON participation_applications (practitioner_id);
CREATE INDEX idx_participation_applications_qualifying_license_id ON participation_applications (qualifying_license_id);

-- ---------------------------------------------------------------------------
-- Audit-column triggers and history tables
-- ---------------------------------------------------------------------------

SELECT add_audit_columns_trigger(t)
FROM unnest(ARRAY ['practitioners', 'practitioner_ssn', 'documents', 'qualifying_licenses',
                   'participation_applications']) AS t;

SELECT create_history_table(t)
FROM unnest(ARRAY ['practitioners', 'qualifying_licenses', 'participation_applications']) AS t;
