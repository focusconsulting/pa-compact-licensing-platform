-- Migration: user role tables
-- Created: 2026-04-15

CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    public_id     UUID UNIQUE,              -- Cognito 'sub' claim (always UUID v4); NULL until first login
    given_name    TEXT,                     -- Cognito 'given_name' standard attribute
    family_name   TEXT,                     -- Cognito 'family_name' standard attribute
    role          TEXT NOT NULL,
    state_code    CHAR(2),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_by    BIGINT NOT NULL REFERENCES users(id) DEFERRABLE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_users_role
        CHECK (role IN ('admin', 'state_staff', 'compact_admin', 'licensee')),
    CONSTRAINT chk_users_state_code
        CHECK (state_code IS NOT NULL OR role IN ('admin', 'compact_admin'))
);

CREATE INDEX idx_users_email     ON users(email);
CREATE INDEX idx_users_public_id ON users(public_id);
