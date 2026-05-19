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

```
DB_HOST='localhost'
DB_PORT='5432'
DB_NAME='licensing'
DB_USER='licensing'
DB_PASSWORD='secret123'
```

### Success Criteria:

#### Automated Verification:
- [ ] Type checking passes: `cd api && uv run pyright`
- [ ] Linting passes: `cd api && uv run ruff check .`
- [ ] Tests pass: `cd api && uv run pytest`
- [ ] Settings loads correctly: `cd api && uv run python -c "from licensing_api.config import settings; print(settings.db_url)"`

#### Manual Verification:
- [ ] `DB_URL` removed from `.env.example`; five new vars present
- [ ] App starts and connects to DB successfully with the new vars

---

## Phase 2: Structured JSON Logging

### Overview
Add `JsonFormatter` with sensitive-field masking, wire it to the root logger and uvicorn, and emit a startup log.

### Changes Required:

#### 1. `api/licensing_api/__main__.py`
**Changes**: Add `_mask_sensitive`, `JsonFormatter`, `_LOG_CONFIG`; replace `logging.basicConfig`; add startup `logger.info`.

Key additions:

```python
import json, re
from datetime import datetime, timezone

_SENSITIVE_PATTERN = re.compile(r'password|token|secret', re.IGNORECASE)
_MASK = '****'
_LOG_RECORD_KEYS = frozenset(logging.LogRecord('', 0, '', 0, '', (), None).__dict__.keys())


def _mask_sensitive(obj: object) -> object:
    if hasattr(obj, 'model_dump'):
        return _mask_sensitive(obj.model_dump())
    if isinstance(obj, dict):
        return {k: _MASK if _SENSITIVE_PATTERN.search(k) else _mask_sensitive(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_mask_sensitive(item) for item in obj]
    return obj


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, object] = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc)
                .isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        for key, val in record.__dict__.items():
            if key not in _LOG_RECORD_KEYS and not key.startswith('_'):
                log_entry[key] = val
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        return json.dumps(_mask_sensitive(log_entry))


_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter())
logging.basicConfig(level=settings.log_level, handlers=[_handler], force=True)

_LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'json': {'()': JsonFormatter}},
    'handlers': {'default': {'class': 'logging.StreamHandler', 'formatter': 'json'}},
    'loggers': {
        'uvicorn': {'handlers': ['default'], 'propagate': False},
        'uvicorn.error': {'handlers': ['default'], 'propagate': False},
        'uvicorn.access': {'handlers': ['default'], 'propagate': False},
    },
}

logger = logging.getLogger(__name__)
```

Lifespan startup log:
```python
logger.info('Starting up', extra={'settings': settings})
```

Uvicorn run with log config:
```python
uvicorn.run(app, host='0.0.0.0', port=settings.api_port,
            log_level=settings.log_level.lower(), log_config=_LOG_CONFIG)
```

### Success Criteria:

#### Automated Verification:
- [ ] Type checking passes: `cd api && uv run pyright`
- [ ] Linting passes: `cd api && uv run ruff check .`
- [ ] Tests pass: `cd api && uv run pytest`
- [ ] Log output is valid JSON: `cd api && uv run python -m licensing_api 2>&1 | head -5 | python -m json.tool`

#### Manual Verification:
- [ ] Startup log contains `settings` field with `db_password` masked as `****`
- [ ] Uvicorn access logs are JSON (not coloured text)
- [ ] No plaintext log lines intermixed with JSON output

---

## Testing Strategy

### Unit Tests:
- `_mask_sensitive` with nested dicts, lists, and Pydantic models
- `_mask_sensitive` with keys matching `password`, `token`, `secret` (case variants)
- `JsonFormatter.format` produces valid JSON with expected fields
- `JsonFormatter.format` with `exc_info` includes `exception` field

### Integration Tests:
- App starts with new DB vars and connects successfully

### Manual Testing Steps:
1. Copy `.env.example` to `.env`, start the API: `docker compose up api`
2. Confirm all lines in stdout are valid JSON: `docker compose logs api | python -m json.tool --no-ensure-ascii`
3. Check startup log for `settings` field and verify `db_password` is `****`
4. Hit the health endpoint and confirm the uvicorn access log line is JSON

## Performance Considerations

JSON serialisation adds negligible overhead per log record. `_LOG_RECORD_KEYS` is a `frozenset` computed once at import time to keep `format()` fast.

## Migration Notes

Any existing `.env` files using `DB_URL` must be updated to the five individual vars before running the new version. No database schema changes.

## References

- Similar implementation: `api/licensing_api/__main__.py`
- Config: `api/licensing_api/config.py`
