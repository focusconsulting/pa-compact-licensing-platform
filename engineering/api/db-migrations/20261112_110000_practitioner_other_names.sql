-- Migration: other names a PA has used (SCRUM-107)
-- Created: 2026-11-12
-- Backlog: U-03; Rule 4 §4.3(c)(2)

-- Covered by the practitioner's identity stamp. A name the PA no longer lists is
-- marked removed, not deleted, so its history keeps pointing at it.
CREATE TABLE practitioner_other_names (
    id               BIGSERIAL   PRIMARY KEY,
    practitioner_id  BIGINT      NOT NULL,
    first_name       TEXT,
    middle_name      TEXT,
    last_name        TEXT        NOT NULL,
    name_suffix      TEXT,
    removed_at       TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by       BIGINT      NOT NULL,
    updated_at       TIMESTAMPTZ NOT NULL,
    updated_by       BIGINT      NOT NULL,
    CONSTRAINT chk_practitioner_other_names_last_name CHECK (last_name <> ''),
    CONSTRAINT fk_practitioner_other_names_practitioner_id FOREIGN KEY (practitioner_id) REFERENCES practitioners (id),
    CONSTRAINT fk_practitioner_other_names_created_by FOREIGN KEY (created_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE,
    CONSTRAINT fk_practitioner_other_names_updated_by FOREIGN KEY (updated_by) REFERENCES users (id) DEFERRABLE INITIALLY IMMEDIATE
);

CREATE INDEX idx_practitioner_other_names_practitioner_id ON practitioner_other_names (practitioner_id);

SELECT add_audit_columns_trigger('practitioner_other_names');
SELECT create_history_table('practitioner_other_names');
