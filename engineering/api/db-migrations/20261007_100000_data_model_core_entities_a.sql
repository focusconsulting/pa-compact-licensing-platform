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
CREATE INDEX idx_practitioners_sex_code ON practitioners (sex_code);
CREATE INDEX idx_practitioners_identity_entered_by ON practitioners (identity_entered_by);
CREATE INDEX idx_practitioners_identity_verified_by_state ON practitioners (identity_verified_by_state);
CREATE INDEX idx_practitioners_residence_entered_by ON practitioners (residence_entered_by);
CREATE INDEX idx_practitioners_residence_verified_by_state ON practitioners (residence_verified_by_state);
CREATE INDEX idx_practitioners_contact_entered_by ON practitioners (contact_entered_by);
CREATE INDEX idx_practitioners_contact_verified_by_state ON practitioners (contact_verified_by_state);
CREATE INDEX idx_practitioners_education_entered_by ON practitioners (education_entered_by);
CREATE INDEX idx_practitioners_education_verified_by_state ON practitioners (education_verified_by_state);
CREATE INDEX idx_practitioners_certification_entered_by ON practitioners (certification_entered_by);
CREATE INDEX idx_practitioners_certification_verified_by_state ON practitioners (certification_verified_by_state);
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
    -- All NULL while a file is uploaded ahead of the record that will own it, such
    -- as an adverse action whose only evidence is the order (FLOW-05). A state owner
    -- is keyed by its code (owner_key); every other owner by its id (owner_id).
    owner_type    TEXT,
    owner_id      BIGINT,
    owner_key     TEXT,
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
        ('practitioner', 'participation_application', 'privilege_request', 'adverse_action', 'sii_report',
         'state', 'ingestion_batch')),
    CONSTRAINT chk_documents_owner CHECK (
        (owner_type IS NULL AND owner_id IS NULL AND owner_key IS NULL)
        OR (owner_type = 'state' AND owner_key IS NOT NULL AND owner_id IS NULL)
        -- owner_type IS NOT NULL: with a NULL type the <> comparison is NULL, and CHECK passes NULL.
        OR (owner_type IS NOT NULL AND owner_type <> 'state' AND owner_id IS NOT NULL AND owner_key IS NULL)),
    CONSTRAINT chk_documents_scan_status CHECK (scan_status IN ('pending', 'clean', 'infected', 'error')),
    CONSTRAINT chk_documents_size_bytes CHECK (size_bytes >= 0),
    CONSTRAINT fk_documents_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_documents_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE INDEX idx_documents_owner ON documents (owner_type, owner_id, owner_key);

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
    -- What the PA says their license is, before the SQL links an on-file record;
    -- the SQL's case view compares the two (FLOW-02).
    claimed_license_number         TEXT,
    claimed_license_expires_on     DATE,
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
    -- Replaced by a later change_sql application that became eligible (Rule 3 §3.6).
    superseded_at                  TIMESTAMPTZ,
    created_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by                     BIGINT      NOT NULL,
    updated_at                     TIMESTAMPTZ NOT NULL,
    updated_by                     BIGINT      NOT NULL,
    CONSTRAINT chk_participation_applications_kind CHECK (kind IN ('initial', 'change_sql')),
    CONSTRAINT chk_participation_applications_status CHECK (status IN
        ('draft', 'submitted', 'info_requested', 'eligible', 'denied', 'withdrawn', 'eligibility_withdrawn',
         'superseded')),
    CONSTRAINT chk_participation_applications_opened
        CHECK (status = 'draft' OR opened_at IS NOT NULL),
    CONSTRAINT chk_participation_applications_decided
        CHECK (status NOT IN ('eligible', 'denied', 'eligibility_withdrawn', 'superseded')
               OR (decided_at IS NOT NULL AND decided_by IS NOT NULL)),
    -- FLOW-02: a decision of eligible needs a linked, verified license and the background
    -- check completed. Privilege requests build on the linked license (FLOW-03).
    CONSTRAINT chk_participation_applications_eligible_requirements
        CHECK (status NOT IN ('eligible', 'eligibility_withdrawn', 'superseded')
               OR (qualifying_license_id IS NOT NULL
                   AND license_verified_at IS NOT NULL
                   AND cbc_completed_on IS NOT NULL)),
    CONSTRAINT chk_participation_applications_superseded
        CHECK (status <> 'superseded' OR superseded_at IS NOT NULL),
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
-- One eligible application per practitioner: a change_sql application that becomes
-- eligible supersedes the old one in the same transaction.
CREATE UNIQUE INDEX uq_participation_applications_one_eligible
    ON participation_applications (practitioner_id)
    WHERE status = 'eligible';
-- The SQL's review queue.
CREATE INDEX idx_participation_applications_sql_queue ON participation_applications (sql_state_code, status);
CREATE INDEX idx_participation_applications_practitioner_id ON participation_applications (practitioner_id);
CREATE INDEX idx_participation_applications_qualifying_license_id ON participation_applications (qualifying_license_id);
CREATE INDEX idx_participation_applications_license_verified_by ON participation_applications (license_verified_by);
CREATE INDEX idx_participation_applications_decided_by ON participation_applications (decided_by);
CREATE INDEX idx_participation_applications_denial_reason_code ON participation_applications (denial_reason_code);

-- ---------------------------------------------------------------------------
-- fees: versioned fee schedule; owner: epic 7 (S-01 writes it), read by epics 8 and 9
-- ---------------------------------------------------------------------------
-- state_code NULL is the Commission's own fee of that type. A new amount is a new
-- row with a later effective_from; the amount in force is the latest one on or
-- before the day in question.

CREATE TABLE fees (
    id              BIGSERIAL   PRIMARY KEY,
    public_id       UUID        NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    state_code      CHAR(2),
    -- participation: the SQL and Commission fees to apply (Rule 3 §3.4(a)(7));
    -- privilege: the remote state and Commission fees per privilege (§3.4(c)(4));
    -- renewal: per renewed privilege (A-05).
    fee_type        TEXT        NOT NULL,
    amount_cents    INTEGER     NOT NULL,
    effective_from  DATE        NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      BIGINT      NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL,
    updated_by      BIGINT      NOT NULL,
    CONSTRAINT uq_fees_schedule UNIQUE NULLS NOT DISTINCT (state_code, fee_type, effective_from),
    CONSTRAINT chk_fees_fee_type CHECK (fee_type IN ('participation', 'privilege', 'renewal')),
    CONSTRAINT chk_fees_amount_cents CHECK (amount_cents >= 0),
    CONSTRAINT fk_fees_state_code FOREIGN KEY (state_code) REFERENCES states (code),
    CONSTRAINT fk_fees_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_fees_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

-- ---------------------------------------------------------------------------
-- Audit-column triggers and history tables
-- ---------------------------------------------------------------------------

SELECT add_audit_columns_trigger(t)
FROM unnest(ARRAY ['practitioners', 'practitioner_ssn', 'documents', 'qualifying_licenses',
                   'participation_applications', 'fees']) AS t;

SELECT create_history_table(t)
FROM unnest(ARRAY ['practitioners', 'qualifying_licenses', 'participation_applications', 'fees']) AS t;
