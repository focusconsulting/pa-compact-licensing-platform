# ADR-0002: Decompose DB_URL into Individual Credential Variables

## Status

Accepted

## Date

2026-04-03

## Context

The API previously required a single `DB_URL` environment variable containing the full PostgreSQL DSN (`postgresql://user:password@host:port/dbname`). This pattern makes it difficult to inject individual credentials from a secrets manager (e.g., AWS Secrets Manager, Vault) without string construction outside the application, and it places the password inside a URL where it is more likely to be logged or echoed accidentally.

## Decision Drivers

- Individual credential vars are the native format for most secrets managers
- Password must not appear in a composite string that is easy to log accidentally
- `db_url` DSN is still needed internally by `asyncpg` — the application must assemble it
- Typed fields (`db_port: int`) provide earlier validation of misconfiguration

## Considered Options

### Option 1: Individual vars + computed `@property`

Replace `db_url: str` in `Settings` with five typed fields (`db_host`, `db_port`, `db_name`, `db_user`, `db_password`) and a `@property` that assembles the DSN internally.

**Pros:**

- Each credential can be injected separately by a secrets manager
- `db_password` key is caught by `_mask_sensitive` and never logged in plaintext
- `db_port` is validated as `int` by Pydantic at startup
- No change to call sites — `settings.db_url` continues to work

**Cons:**

- Five env vars to configure instead of one — slightly more verbose `.env` files

### Option 2: Keep `DB_URL`; extract password at runtime

Keep `DB_URL` but parse it with `urllib.parse.urlparse` to extract components for masking.

**Pros:**

- Single var — simpler `.env`

**Cons:**

- Parsing a URL to re-compose it is fragile
- Still requires `DB_URL` to contain the password, defeating secrets manager injection
- More code than Option 1

### Option 3: Keep `DB_URL` unchanged

**Pros:**

- No migration needed

**Cons:**

- Password embedded in a URL string — high risk of accidental logging
- Incompatible with per-field secrets manager injection

## Decision

**Chosen option:** Option 1 (individual vars + computed `@property`), because it is the lowest-complexity path to secrets-manager-compatible configuration and eliminates the password-in-URL logging risk with no call-site changes.

## Consequences

### Positive

- `db_password` is isolated as a named field, automatically masked by `_mask_sensitive` (see ADR-0001)
- Compatible with per-field injection from AWS Secrets Manager, Vault, and Kubernetes secrets
- Startup log safely emits the full settings object including `db_host`, `db_port`, `db_name`, `db_user` for observability, with only `db_password` masked

### Negative

- Existing `.env` files and CI/CD pipelines that set `DB_URL` must migrate to the five individual vars — Mitigation: `.env.example` is updated; migration is a one-time change per environment.

## Related

- GitHub Issue: N/A
- Beads Task: pa-compact-licensing-platform-4ok
- Implementation Plan: `thoughts/shared/plans/api/2026-04-03-structured-logging.md`
- ADR-0001: Structured JSON Logging (the `_mask_sensitive` function referenced here is defined there)
