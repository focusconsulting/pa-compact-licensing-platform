## Summary

Replaces the API's unstructured plaintext logging with structured JSON output (one object per line) and decomposes the monolithic `DB_URL` env var into five individually-injectable credential fields. Together these changes make logs machine-parseable by any centralized collector and make the app's configuration compatible with secrets managers (AWS Secrets Manager, Vault, etc.) without requiring any changes to call sites.

## Related

- GitHub Issue: N/A
- Beads: pa-compact-licensing-platform-vq6 (logging), pa-compact-licensing-platform-4ok (DB config)
- ADR-0001: `docs/architecture_decision_records/0001-structured-json-logging.md`
- ADR-0002: `docs/architecture_decision_records/0002-db-config-decomposition.md`

## Changes

### Core: Structured JSON Logging (`api/licensing_api/__main__.py`)

- Add `JsonFormatter` — a `logging.Formatter` subclass that emits one JSON object per line with fields: `timestamp` (UTC ISO-8601 ms), `level`, `logger`, `message`, plus any `extra` keys passed by the caller
- Add `_mask_sensitive` — recursively walks dicts/lists/Pydantic models and replaces values whose key matches `password|token|secret` (case-insensitive) with `****`; applied unconditionally in `JsonFormatter.format` so masking cannot be bypassed
- Wire `JsonFormatter` to the root logger via `logging.basicConfig(force=True)` and to Uvicorn via `log_config` dict — all output (app + Uvicorn access/error) is now uniform JSON
- Emit an `INFO` startup log with the full settings object (password masked) for observability without shell access

### Core: DB Config Decomposition (`api/licensing_api/config.py`, `api/.env.example`)

- Replace single `db_url: str` field with five typed fields: `db_host`, `db_port` (int), `db_name`, `db_user`, `db_password`
- Add `db_url` as a `@property` that assembles the DSN — no call-site changes needed
- Update `.env.example` to document the five new vars; remove `DB_URL`

### Tooling (`api/pyproject.toml`)

- Add `UP017` to ruff ignore list — pyright 1.1.x stubs do not expose `datetime.UTC` as a class attribute; `timezone.utc` is used instead

### Documentation

- `docs/architecture_decision_records/0001-structured-json-logging.md` — ADR documenting the JSON logging decision (3 options considered)
- `docs/architecture_decision_records/0002-db-config-decomposition.md` — ADR documenting individual vars vs single DSN (3 options considered)

## Migration Required

Any `.env` files or CI/CD pipelines currently setting `DB_URL` must switch to the five individual vars before deploying:

```bash
# Before
DB_URL='postgresql://licensing:secret123@localhost:5432/licensing'

# After
DB_HOST='localhost'
DB_PORT='5432'
DB_NAME='licensing'
DB_USER='licensing'
DB_PASSWORD='secret123'
```

## How to Test

### Automated

```bash
cd api && uv run pyright       # 0 errors
cd api && uv run ruff check .  # All checks passed
cd api && uv run pytest        # 4 passed (2 failures are pre-existing: no DB/Redis in unit test env)
```

### Manual

1. Start the stack: `docker compose up api`
2. Verify all log lines are valid JSON:
   ```bash
   docker compose logs api | python -m json.tool --no-ensure-ascii
   ```
3. Confirm the startup log contains `"db_password": "****"` and all other settings fields in plaintext
4. Hit the health endpoint and verify the Uvicorn access log line is also JSON (not coloured text)
5. Confirm connecting with `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER`/`DB_PASSWORD` vars works end-to-end

### Expected startup log output

```json
{
  "timestamp": "2026-04-03T14:32:10.090Z",
  "level": "INFO",
  "logger": "licensing_api.__main__",
  "message": "Starting up",
  "settings": {
    "db_host": "localhost",
    "db_port": 5432,
    "db_name": "licensing",
    "db_user": "licensing",
    "db_password": "****",
    "redis_url": "redis://localhost:6379",
    "api_port": 8000,
    "log_level": "INFO",
    "environment": "LOCAL_DEV"
  }
}
```

## Checklist

- [x] API type checking passes (`uv run pyright`)
- [x] API linting passes (`uv run ruff check .`)
- [x] API formatting correct (`uv run ruff format --check .`)
- [x] API tests pass (pre-existing infra failures excluded — no DB/Redis in local unit test env)
- [x] `.env.example` updated to document new vars
- [x] ADRs written for both architectural decisions
- [ ] Manual testing with running stack (Docker Compose)
- [ ] CI/CD env vars updated from `DB_URL` to individual vars (ops task)

## Notes for Reviewers

- The two pre-existing test failures (`test_ready_all_healthy` → Redis not running, `test_test_table_row_one_has_epoch_added_at` → Postgres not running) are not caused by this PR. The captured stderr in the test output already shows the new JSON logging working correctly.
- `_mask_sensitive` uses `cast(Any, obj)` before calling `.model_dump()` — this is the minimal fix to satisfy pyright, which cannot narrow `object` through `hasattr`. The runtime behaviour is identical to the original `obj.model_dump()` call.
- Uvicorn's `log_config` uses the `'()'` factory callable key (not a dotted string) because `JsonFormatter` is a local class without a importable module path.

---

<details>
<summary>📋 Implementation Plan</summary>

# Structured JSON Logging & DB Config Decomposition

## Overview

Replace ad-hoc text logging with structured JSON output and split the monolithic `DB_URL` env var into individual components so each credential can be managed independently.

## Related

- GitHub Issue: N/A
- Beads Task: N/A
- ADRs: ADR-0001 (structured JSON logging), ADR-0002 (DB config decomposition)
- **Area**: api

## Current State Analysis

- `config.py`: a single `db_url: str` field holds the full DSN (`postgresql://licensing:secret123@localhost:5432/licensing`), making it impossible to inject individual credentials from a secrets manager without string manipulation.
- `__main__.py`: `logging.basicConfig(level=settings.log_level)` produces unstructured text output; uvicorn uses its own default text formatter. No sensitive-field masking. No startup observability log.
- `.env.example` exposes `DB_URL` as a single var.

### Key Discoveries:
- `api/licensing_api/config.py:7` — `db_url` is a plain `str` field with a hard-coded default.
- `api/licensing_api/__main__.py:14` — single `logging.basicConfig` call, no custom formatter.
- `api/licensing_api/__main__.py:35` — `uvicorn.run` called without `log_config`, so uvicorn uses its own text formatter.

## Desired End State

- All log output (app + uvicorn) is newline-delimited JSON with fields: `timestamp` (UTC ISO-8601 ms), `level`, `logger`, `message`, plus any `extra` fields.
- Values whose key matches `password|token|secret` (case-insensitive) are masked as `****` before serialisation, including nested dicts and Pydantic models.
- DB connection string is assembled from five individual env vars (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`); `DB_URL` is no longer required.
- A startup `INFO` log emits the full settings object (password masked).
- `.env.example` documents the five new vars.

## What We're NOT Doing

- No log aggregation or shipping configuration (that belongs in IaC).
- No request/response body logging middleware.
- No change to log retention policy or log levels per route.
- No migration of existing `logging.getLogger` call sites outside of `__main__.py`.

## Implementation Approach

All changes land in a single commit on the `structured-logging` branch. The work is small and tightly coupled, so no phasing is required — implement everything together and verify end-to-end.

---

## Phase 1: DB Config Decomposition

### Overview
Replace the single `db_url` string field with five typed fields and a computed `@property`.

### Changes Required:

#### 1. `api/licensing_api/config.py`
**Changes**: Remove `db_url: str` field; add `db_host`, `db_port`, `db_name`, `db_user`, `db_password`; add `db_url` property.

```python
class Settings(BaseSettings):
    db_host: str = 'localhost'
    db_port: int = 5432
    db_name: str = 'licensing'
    db_user: str = 'licensing'
    db_password: str = 'invalid'

    redis_url: str = 'redis://invalid'
    api_port: int = 8000
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'
    environment: Literal['LOCAL_DEV', 'DEV', 'STAGING', 'PROD'] = 'LOCAL_DEV'

    @property
    def db_url(self) -> str:
        return f'postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}'
```

#### 2. `api/.env.example`
**Changes**: Replace `DB_URL` with the five individual vars.

### Success Criteria:

#### Automated Verification:
- [x] Type checking passes: `cd api && uv run pyright`
- [x] Linting passes: `cd api && uv run ruff check .`
- [x] Tests pass: `cd api && uv run pytest`

#### Manual Verification:
- [ ] `DB_URL` removed from `.env.example`; five new vars present ✓ (in code)
- [ ] App starts and connects to DB successfully with the new vars

---

## Phase 2: Structured JSON Logging

### Overview
Add `JsonFormatter` with sensitive-field masking, wire it to the root logger and uvicorn, and emit a startup log.

### Success Criteria:

#### Automated Verification:
- [x] Type checking passes: `cd api && uv run pyright`
- [x] Linting passes: `cd api && uv run ruff check .`
- [x] Tests pass: `cd api && uv run pytest`

#### Manual Verification:
- [ ] Startup log contains `settings` field with `db_password` masked as `****`
- [ ] Uvicorn access logs are JSON (not coloured text)
- [ ] No plaintext log lines intermixed with JSON output

---

## Testing Strategy

### Manual Testing Steps:
1. Copy `.env.example` to `.env`, start the API: `docker compose up api`
2. Confirm all lines in stdout are valid JSON: `docker compose logs api | python -m json.tool --no-ensure-ascii`
3. Check startup log for `settings` field and verify `db_password` is `****`
4. Hit the health endpoint and confirm the uvicorn access log line is JSON

## Performance Considerations

JSON serialisation adds negligible overhead per log record. `_LOG_RECORD_KEYS` is a `frozenset` computed once at import time to keep `format()` fast.

## Migration Notes

Any existing `.env` files using `DB_URL` must be updated to the five individual vars before running the new version. No database schema changes.

</details>
