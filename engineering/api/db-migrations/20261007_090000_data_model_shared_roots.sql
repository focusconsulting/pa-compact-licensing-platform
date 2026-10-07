-- Migration: data model shared roots and conventions (F-02 phase 1)
-- Created: 2026-10-07
-- Conventions: engineering/adrs/0005-data-model-conventions.md
-- Dictionary:  engineering/docs/data-model.md

-- ---------------------------------------------------------------------------
-- Convention functions
-- ---------------------------------------------------------------------------

-- Fills updated_* from created_* on insert and stamps updated_at on update.
-- The app always supplies updated_by on update (ADR-0004).
CREATE FUNCTION set_audit_columns() RETURNS trigger
    LANGUAGE plpgsql AS
$$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.updated_at := COALESCE(NEW.updated_at, NEW.created_at);
        NEW.updated_by := COALESCE(NEW.updated_by, NEW.created_by);
    ELSE
        NEW.updated_at := now();
    END IF;
    RETURN NEW;
END
$$;

-- History and audit rows change only inside an expungement transaction (ADR-0008).
CREATE FUNCTION prevent_mutation() RETURNS trigger
    LANGUAGE plpgsql AS
$$
BEGIN
    IF current_setting('app.expunge', true) IS DISTINCT FROM 'on' THEN
        RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
    END IF;
    RETURN COALESCE(NEW, OLD);
END
$$;

-- ---------------------------------------------------------------------------
-- users: additive changes only (Principle XIV)
-- ---------------------------------------------------------------------------

ALTER TABLE users
    ADD COLUMN updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN updated_by  BIGINT,
    -- Per-state permissions, e.g. {"KS": ["write", "read_private"]} (D5).
    ADD COLUMN permissions JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE users SET updated_by = created_by, updated_at = created_at;

ALTER TABLE users
    ALTER COLUMN updated_by SET NOT NULL,
    ADD CONSTRAINT fk_users_updated_by
        FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    DROP CONSTRAINT chk_users_role,
    ADD CONSTRAINT chk_users_role
        CHECK (role IN ('admin', 'state_staff', 'state_admin', 'compact_admin', 'licensee')),
    ADD CONSTRAINT chk_users_permissions_object
        CHECK (jsonb_typeof(permissions) = 'object');

CREATE TRIGGER trg_users_audit_columns
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_audit_columns();

-- Workers and scheduled jobs write as this user. It is inactive and its address
-- cannot receive mail, so it can never log in (ADR-0005). A self-referencing row
-- satisfies its own foreign keys because they are checked at the end of the statement.
INSERT INTO users (id, email, given_name, family_name, role, state_code, is_active, created_by, updated_by)
SELECT next_id, 'system@pa-compact.invalid', 'System', 'User', 'admin', NULL, FALSE, next_id, next_id
FROM (SELECT nextval('users_id_seq') AS next_id) AS seq;

-- ---------------------------------------------------------------------------
-- compact_settings: one row of compact-wide configuration
-- ---------------------------------------------------------------------------

CREATE TABLE compact_settings (
    id          SMALLINT PRIMARY KEY DEFAULT 1,
    -- The reference time zone for "today" and every day count (ADR-0006).
    time_zone   TEXT        NOT NULL DEFAULT 'America/New_York',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  BIGINT      NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL,
    updated_by  BIGINT      NOT NULL,

    CONSTRAINT chk_compact_settings_single_row CHECK (id = 1),
    CONSTRAINT fk_compact_settings_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_compact_settings_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE TRIGGER trg_compact_settings_audit_columns
    BEFORE INSERT OR UPDATE ON compact_settings
    FOR EACH ROW EXECUTE FUNCTION set_audit_columns();

INSERT INTO compact_settings (id, created_by)
SELECT 1, id FROM users WHERE email = 'system@pa-compact.invalid';

-- The calendar day an instant falls on in the reference time zone (ADR-0006).
CREATE FUNCTION compact_date_at(instant TIMESTAMPTZ) RETURNS DATE
    LANGUAGE sql STABLE AS
$$
SELECT (instant AT TIME ZONE time_zone)::date FROM compact_settings WHERE id = 1
$$;

-- "Today" for every status computation (ADR-0006).
CREATE FUNCTION compact_today() RETURNS DATE
    LANGUAGE sql STABLE AS
$$
SELECT compact_date_at(now())
$$;

-- ---------------------------------------------------------------------------
-- states: every US jurisdiction; membership and go-live are configuration (Q-03)
-- ---------------------------------------------------------------------------

CREATE TABLE states (
    code                                CHAR(2)     PRIMARY KEY,
    name                                TEXT        NOT NULL UNIQUE,
    is_member                           BOOLEAN     NOT NULL DEFAULT FALSE,
    member_effective_on                 DATE,
    is_live                             BOOLEAN     NOT NULL DEFAULT FALSE,
    practice_requirements_url           TEXT,
    -- Proofs a remote state may require before issuance (Rule 3 §3.4(c)(3)-(6)).
    jurisprudence_requirement           TEXT        NOT NULL DEFAULT 'none',
    supervision_agreement_requirement   TEXT        NOT NULL DEFAULT 'none',
    prescriptive_authority_requirement  TEXT        NOT NULL DEFAULT 'none',
    other_compliance_requirement        TEXT        NOT NULL DEFAULT 'none',
    created_at                          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by                          BIGINT      NOT NULL,
    updated_at                          TIMESTAMPTZ NOT NULL,
    updated_by                          BIGINT      NOT NULL,

    CONSTRAINT chk_states_jurisprudence_requirement
        CHECK (jurisprudence_requirement IN ('none', 'attestation', 'proof_upload')),
    CONSTRAINT chk_states_supervision_agreement_requirement
        CHECK (supervision_agreement_requirement IN ('none', 'attestation', 'proof_upload')),
    CONSTRAINT chk_states_prescriptive_authority_requirement
        CHECK (prescriptive_authority_requirement IN ('none', 'attestation', 'proof_upload')),
    CONSTRAINT chk_states_other_compliance_requirement
        CHECK (other_compliance_requirement IN ('none', 'attestation', 'proof_upload')),
    CONSTRAINT chk_states_live_requires_member CHECK (NOT is_live OR is_member),
    CONSTRAINT fk_states_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_states_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE TRIGGER trg_states_audit_columns
    BEFORE INSERT OR UPDATE ON states
    FOR EACH ROW EXECUTE FUNCTION set_audit_columns();

INSERT INTO states (code, name, created_by)
SELECT j.code, j.name, u.id
FROM (VALUES ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'),
             ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'),
             ('DC', 'District of Columbia'), ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'),
             ('ID', 'Idaho'), ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'),
             ('KS', 'Kansas'), ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'),
             ('MD', 'Maryland'), ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'),
             ('MS', 'Mississippi'), ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'),
             ('NV', 'Nevada'), ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'),
             ('NY', 'New York'), ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'),
             ('OK', 'Oklahoma'), ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'),
             ('SC', 'South Carolina'), ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'),
             ('UT', 'Utah'), ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'),
             ('WV', 'West Virginia'), ('WI', 'Wisconsin'), ('WY', 'Wyoming'),
             ('AS', 'American Samoa'), ('GU', 'Guam'), ('MP', 'Northern Mariana Islands'),
             ('PR', 'Puerto Rico'), ('VI', 'U.S. Virgin Islands')) AS j (code, name)
CROSS JOIN users u
WHERE u.email = 'system@pa-compact.invalid';

ALTER TABLE users
    ADD CONSTRAINT fk_users_state_code FOREIGN KEY (state_code) REFERENCES states (code);

-- ---------------------------------------------------------------------------
-- Lookup tables: lists that wait on a Commission answer, so an answer is a data change
-- ---------------------------------------------------------------------------

-- Values arrive with epic 5 once Q-10 is answered.
CREATE TABLE ref_sex (
    code        TEXT        PRIMARY KEY,
    label       TEXT        NOT NULL,
    sort_order  SMALLINT    NOT NULL,
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  BIGINT      NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL,
    updated_by  BIGINT      NOT NULL,
    CONSTRAINT fk_ref_sex_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_ref_sex_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

-- Seeded from the examples in the Adverse Action definition, ML §2.A.
CREATE TABLE ref_adverse_action_types (
    code        TEXT        PRIMARY KEY,
    label       TEXT        NOT NULL,
    sort_order  SMALLINT    NOT NULL,
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  BIGINT      NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL,
    updated_by  BIGINT      NOT NULL,
    CONSTRAINT fk_ref_adverse_action_types_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_ref_adverse_action_types_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

-- Values arrive with epic 9 once Q-17 is answered.
CREATE TABLE ref_npdb_categories (
    code        TEXT        PRIMARY KEY,
    label       TEXT        NOT NULL,
    sort_order  SMALLINT    NOT NULL,
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  BIGINT      NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL,
    updated_by  BIGINT      NOT NULL,
    CONSTRAINT fk_ref_npdb_categories_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_ref_npdb_categories_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

-- Eligibility reasons follow ML §4.A(1)-(8); the Q-08 default. Privilege reasons
-- follow the remote-state requirements of Rule 3 §3.4(c)-(d).
CREATE TABLE ref_denial_reasons (
    code        TEXT        PRIMARY KEY,
    label       TEXT        NOT NULL,
    applies_to  TEXT        NOT NULL,
    sort_order  SMALLINT    NOT NULL,
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  BIGINT      NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL,
    updated_by  BIGINT      NOT NULL,
    CONSTRAINT chk_ref_denial_reasons_applies_to CHECK (applies_to IN ('eligibility', 'privilege')),
    CONSTRAINT fk_ref_denial_reasons_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_ref_denial_reasons_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE TRIGGER trg_ref_sex_audit_columns
    BEFORE INSERT OR UPDATE ON ref_sex
    FOR EACH ROW EXECUTE FUNCTION set_audit_columns();
CREATE TRIGGER trg_ref_adverse_action_types_audit_columns
    BEFORE INSERT OR UPDATE ON ref_adverse_action_types
    FOR EACH ROW EXECUTE FUNCTION set_audit_columns();
CREATE TRIGGER trg_ref_npdb_categories_audit_columns
    BEFORE INSERT OR UPDATE ON ref_npdb_categories
    FOR EACH ROW EXECUTE FUNCTION set_audit_columns();
CREATE TRIGGER trg_ref_denial_reasons_audit_columns
    BEFORE INSERT OR UPDATE ON ref_denial_reasons
    FOR EACH ROW EXECUTE FUNCTION set_audit_columns();

INSERT INTO ref_adverse_action_types (code, label, sort_order, created_by)
SELECT t.code, t.label, t.sort_order, u.id
FROM (VALUES ('license_denial', 'License denial', 1),
             ('censure', 'Censure', 2),
             ('revocation', 'Revocation', 3),
             ('suspension', 'Suspension', 4),
             ('probation', 'Probation', 5),
             ('monitoring', 'Monitoring of the licensee', 6),
             ('practice_restriction', 'Restriction on the licensee''s practice', 7),
             ('other', 'Other', 99)) AS t (code, label, sort_order)
CROSS JOIN users u
WHERE u.email = 'system@pa-compact.invalid';

INSERT INTO ref_denial_reasons (code, label, applies_to, sort_order, created_by)
SELECT r.code, r.label, r.applies_to, r.sort_order, u.id
FROM (VALUES ('program_not_accredited', 'Did not graduate from an accredited PA program', 'eligibility', 1),
             ('nccpa_not_current', 'Does not hold current NCCPA certification', 'eligibility', 2),
             ('conviction', 'Has a felony or misdemeanor conviction', 'eligibility', 3),
             ('controlled_substance_action', 'Controlled substance license, permit, or registration suspended or revoked', 'eligibility', 4),
             ('no_unique_identifier', 'Does not have the required unique identifier', 'eligibility', 5),
             ('no_qualifying_license', 'Does not hold a qualifying license', 'eligibility', 6),
             ('license_revoked_or_restricted', 'License revoked, limited, or restricted due to an adverse action', 'eligibility', 7),
             ('within_two_years_of_restriction', 'Fewer than two years since a restriction ended', 'eligibility', 8),
             ('eligibility_other', 'Other', 'eligibility', 99),
             ('jurisprudence_not_met', 'Jurisprudence requirement not met', 'privilege', 1),
             ('remote_state_requirements_not_met', 'Remote state requirements not met', 'privilege', 2),
             ('privilege_other', 'Other', 'privilege', 99)) AS r (code, label, applies_to, sort_order)
CROSS JOIN users u
WHERE u.email = 'system@pa-compact.invalid';

-- ---------------------------------------------------------------------------
-- audit_log: who did what, append-only (Principle VI)
-- ---------------------------------------------------------------------------

CREATE TABLE audit_log (
    id             BIGSERIAL   PRIMARY KEY,
    occurred_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_user_id  BIGINT,
    action         TEXT        NOT NULL,
    entity_type    TEXT        NOT NULL,
    entity_id      BIGINT,
    before         JSONB,
    after          JSONB,
    reason         TEXT,
    request_id     TEXT,
    CONSTRAINT fk_audit_log_actor_user_id FOREIGN KEY (actor_user_id) REFERENCES users (id)
);

CREATE INDEX idx_audit_log_entity ON audit_log (entity_type, entity_id);
CREATE INDEX idx_audit_log_actor_user_id ON audit_log (actor_user_id);

CREATE TRIGGER trg_audit_log_append_only
    BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_mutation();

-- ---------------------------------------------------------------------------
-- domain_events: the transactional outbox (D2); F-05 adds the code
-- ---------------------------------------------------------------------------

CREATE TABLE domain_events (
    id              BIGSERIAL   PRIMARY KEY,
    event_id        UUID        NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    type            TEXT        NOT NULL,
    aggregate_type  TEXT        NOT NULL,
    aggregate_id    BIGINT      NOT NULL,
    -- IDs only; no PII (data dictionary).
    payload         JSONB       NOT NULL DEFAULT '{}'::jsonb,
    actor_user_id   BIGINT,
    request_id      TEXT,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_domain_events_actor_user_id FOREIGN KEY (actor_user_id) REFERENCES users (id)
);

CREATE INDEX idx_domain_events_aggregate ON domain_events (aggregate_type, aggregate_id);
CREATE INDEX idx_domain_events_actor_user_id ON domain_events (actor_user_id);

-- One row per (event, handler); handlers are idempotent on this key (FLOW-07).
CREATE TABLE domain_event_deliveries (
    event_id          UUID        NOT NULL,
    handler           TEXT        NOT NULL,
    attempts          INTEGER     NOT NULL DEFAULT 0,
    last_error        TEXT,
    handled_at        TIMESTAMPTZ,
    dead_lettered_at  TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (event_id, handler),
    CONSTRAINT fk_domain_event_deliveries_event_id FOREIGN KEY (event_id) REFERENCES domain_events (event_id)
);

CREATE INDEX idx_domain_event_deliveries_pending
    ON domain_event_deliveries (created_at)
    WHERE handled_at IS NULL AND dead_lettered_at IS NULL;

-- ---------------------------------------------------------------------------
-- notifications: rows the worker sends (D7); F-11 adds the code
-- ---------------------------------------------------------------------------

CREATE TABLE notifications (
    id                 BIGSERIAL   PRIMARY KEY,
    public_id          UUID        NOT NULL DEFAULT gen_random_uuid() UNIQUE,
    template           TEXT        NOT NULL,
    recipient_user_id  BIGINT,
    recipient_email    TEXT        NOT NULL,
    context            JSONB       NOT NULL DEFAULT '{}'::jsonb,
    idempotency_key    TEXT        NOT NULL UNIQUE,
    status             TEXT        NOT NULL DEFAULT 'pending',
    attempts           INTEGER     NOT NULL DEFAULT 0,
    last_error         TEXT,
    sent_at            TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by         BIGINT      NOT NULL,
    updated_at         TIMESTAMPTZ NOT NULL,
    updated_by         BIGINT      NOT NULL,
    CONSTRAINT chk_notifications_status CHECK (status IN ('pending', 'sent', 'failed')),
    CONSTRAINT chk_notifications_sent_at CHECK ((status = 'sent') = (sent_at IS NOT NULL)),
    CONSTRAINT fk_notifications_recipient_user_id FOREIGN KEY (recipient_user_id) REFERENCES users (id),
    CONSTRAINT fk_notifications_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_notifications_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE INDEX idx_notifications_pending ON notifications (created_at) WHERE status = 'pending';
CREATE INDEX idx_notifications_recipient_user_id ON notifications (recipient_user_id);

CREATE TRIGGER trg_notifications_audit_columns
    BEFORE INSERT OR UPDATE ON notifications
    FOR EACH ROW EXECUTE FUNCTION set_audit_columns();
