-- Migration: the attestations catalogue, and what a PA accepted on an application (SCRUM-110)
-- Created: 2026-11-12
-- Backlog: L-03; Rule 3 §3.3(a), §3.4(a), §3.4(c)

-- A wording change is a new version, so an acceptance always names the text the PA read.
CREATE TABLE attestations (
    code        TEXT        NOT NULL,
    version     INTEGER     NOT NULL,
    applies_to  TEXT        NOT NULL,
    -- One remote state's own attestation; NULL applies to every state.
    state_code  CHAR(2),
    sort_order  SMALLINT    NOT NULL,
    text        TEXT        NOT NULL,
    -- The rule or model-legislation clause the attestation carries out.
    source      TEXT        NOT NULL,
    retired_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  BIGINT      NOT NULL,
    updated_at  TIMESTAMPTZ NOT NULL,
    updated_by  BIGINT      NOT NULL,
    PRIMARY KEY (code, version),
    CONSTRAINT chk_attestations_applies_to CHECK (applies_to IN ('participation', 'privilege')),
    CONSTRAINT chk_attestations_version CHECK (version >= 1),
    CONSTRAINT chk_attestations_state_is_remote CHECK (state_code IS NULL OR applies_to = 'privilege'),
    CONSTRAINT chk_attestations_source CHECK (source <> ''),
    CONSTRAINT fk_attestations_state_code FOREIGN KEY (state_code) REFERENCES states (code),
    CONSTRAINT fk_attestations_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_attestations_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE INDEX idx_attestations_state_code ON attestations (state_code);

CREATE TRIGGER trg_attestations_audit_columns
    BEFORE INSERT OR UPDATE ON attestations
    FOR EACH ROW EXECUTE FUNCTION set_audit_columns();

-- Only retired_at may change: an edited text would change what past applicants accepted.
CREATE FUNCTION prevent_attestation_rewrite() RETURNS trigger
    LANGUAGE plpgsql AS
$$
BEGIN
    IF (NEW.code, NEW.version, NEW.applies_to, NEW.state_code, NEW.sort_order, NEW.text, NEW.source)
        IS DISTINCT FROM
       (OLD.code, OLD.version, OLD.applies_to, OLD.state_code, OLD.sort_order, OLD.text, OLD.source) THEN
        RAISE EXCEPTION 'attestation %/% is fixed once written; add a new version', OLD.code, OLD.version;
    END IF;
    RETURN NEW;
END
$$;

CREATE TRIGGER trg_attestations_fixed
    BEFORE UPDATE ON attestations
    FOR EACH ROW EXECUTE FUNCTION prevent_attestation_rewrite();

-- Append-only: accepting a newer version adds a row, so the submitted record keeps every acceptance.
CREATE TABLE participation_application_attestations (
    participation_application_id  BIGINT      NOT NULL,
    attestation_code              TEXT        NOT NULL,
    attestation_version           INTEGER     NOT NULL,
    accepted_at                   TIMESTAMPTZ NOT NULL,
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by                    BIGINT      NOT NULL,
    updated_at                    TIMESTAMPTZ NOT NULL,
    updated_by                    BIGINT      NOT NULL,
    PRIMARY KEY (participation_application_id, attestation_code, attestation_version),
    CONSTRAINT fk_participation_application_attestations_application FOREIGN KEY (participation_application_id) REFERENCES participation_applications (id),
    CONSTRAINT fk_participation_application_attestations_attestation FOREIGN KEY (attestation_code, attestation_version) REFERENCES attestations (code, version),
    CONSTRAINT fk_participation_application_attestations_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_participation_application_attestations_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE INDEX idx_participation_application_attestations_attestation
    ON participation_application_attestations (attestation_code, attestation_version);

CREATE TRIGGER trg_participation_application_attestations_audit_columns
    BEFORE INSERT ON participation_application_attestations
    FOR EACH ROW EXECUTE FUNCTION set_audit_columns();
CREATE TRIGGER trg_participation_application_attestations_append_only
    BEFORE UPDATE OR DELETE ON participation_application_attestations
    FOR EACH ROW EXECUTE FUNCTION prevent_mutation();

-- Drafted from Rule 3 and the model legislation; Commission legal signs off (Q-06).
-- A state's jurisprudence attestation is added when the state configures one (SCRUM-190).
INSERT INTO attestations (code, version, applies_to, sort_order, text, source, created_by)
SELECT a.code, 1, a.applies_to, a.sort_order, a.text, a.source, u.id
FROM (VALUES
    ('arc_pa_graduate', 'participation', 1,
     'I graduated from a PA program accredited by the Accreditation Review Commission on Education for the Physician Assistant, Inc.',
     'Rule 3 §3.3(a)(1); ML §4.A(1)'),
    ('nccpa_current', 'participation', 2,
     'I hold a current certification from the National Commission on Certification of Physician Assistants (NCCPA).',
     'Rule 3 §3.3(a)(2); ML §4.A(2)'),
    ('no_convictions', 'participation', 3,
     'I have never been found guilty by a court of a felony or misdemeanor offense, including through a plea of guilty or no contest.',
     'Rule 3 §3.3(a)(3); ML §4.A(3)'),
    ('no_controlled_substance_action', 'participation', 4,
     'I have never had a controlled substance license, permit, or registration suspended or revoked by a state or by the United States Drug Enforcement Administration.',
     'Rule 3 §3.3(a)(4); ML §4.A(4)'),
    ('no_current_restriction', 'participation', 5,
     'No license I hold has been revoked, limited, or restricted because of an adverse action.',
     'Rule 3 §3.3(a)(7); ML §4.A(7)'),
    ('two_year_bar', 'participation', 6,
     'If a license or compact privilege of mine was limited or restricted because of an adverse action, at least two years have passed since it was no longer limited or restricted.',
     'Rule 3 §3.3(a)(7)(i); ML §4.A(8)'),
    ('no_pending_investigation', 'participation', 7,
     'I am not aware of any pending investigation of my license in my state of qualifying license.',
     'Rule 3 §3.4(a)(5)'),
    ('service_of_process', 'participation', 8,
     'I consent to service of process by mail at my primary residence address, and I will report a change of that address to the Commission within 30 days.',
     'Rule 3 §3.4(a)(3); ML §5.A(2)'),
    ('background_check', 'participation', 9,
     'I will submit to a criminal background check, including fingerprints or other biometric information, through the process my state of qualifying license designates, within 60 days of this application.',
     'Rule 3 §3.4(a)(4)'),
    ('truthfulness', 'participation', 10,
     'I swear that the information in this application is true and accurate.',
     'Rule 3 §3.4(a)(1)'),
    ('supervision_compliance', 'privilege', 1,
     'I will comply with each remote state''s laws and regulations on supervision by or collaboration with a physician.',
     'Rule 3 §3.3(a)(11)'),
    ('prescribing_compliance', 'privilege', 2,
     'I will comply with each remote state''s laws and regulations on the authority to prescribe controlled substances, in each remote state where I seek that authority.',
     'Rule 3 §3.3(a)(12); ML §4.D')
) AS a (code, applies_to, sort_order, text, source)
CROSS JOIN users u
WHERE u.email = 'system@pa-compact.invalid';
