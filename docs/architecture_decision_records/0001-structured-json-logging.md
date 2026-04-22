# ADR-0001: Structured JSON Logging for the API

## Status

Accepted

## Date

2026-04-03

## Context

The API previously used Python's default `logging.basicConfig` with no formatter, producing unstructured plaintext output. Uvicorn used its own coloured text formatter. This made log aggregation, filtering, and alerting difficult in deployed environments (DEV, STAGING, PROD), where logs are ingested by a centralized collector.

Additionally, there was no guarantee that sensitive values (passwords, tokens, secrets) passed as `extra` fields would not appear in plaintext in log output.

## Decision Drivers

- Logs must be machine-parseable for aggregation and alerting in all non-local environments
- Application logs and Uvicorn access/error logs must have a uniform format
- Sensitive field values must never appear in plaintext in log output
- Solution must require zero external dependencies beyond the standard library

## Considered Options

### Option 1: Custom `JsonFormatter` in `__main__.py`

Implement a `logging.Formatter` subclass that serialises each `LogRecord` to a JSON object. Wire it to the root logger and to Uvicorn via its `log_config` dict. Add a `_mask_sensitive` helper that recursively masks dict/list/Pydantic values whose key matches `password|token|secret`.

**Pros:**

- No additional dependencies
- Full control over output schema
- Uvicorn and app logs share one formatter
- Sensitive-field masking is automatic

**Cons:**

- Custom code to maintain
- Must stay in sync with Uvicorn's `log_config` API across upgrades

### Option 2: Third-party structured logging library (e.g., `structlog`)

Replace `logging` with `structlog` for all application code.

**Pros:**

- Feature-rich (context vars, processors pipeline)
- Well-maintained

**Cons:**

- Adds a dependency
- Uvicorn still needs a custom bridge to emit JSON; doesn't simplify that problem
- More migration surface across existing call sites

### Option 3: Log formatting at the infrastructure layer only

Keep plaintext logs; let the log collector parse/transform them.

**Pros:**

- Zero code changes

**Cons:**

- Brittle — relies on regex parsing of free-form text
- Sensitive values still risk appearing in plaintext
- Inconsistent format makes local debugging harder too

## Decision

**Chosen option:** Option 1 (custom `JsonFormatter`), because it satisfies all drivers with no new dependencies and keeps the formatter co-located with the app entrypoint where it is easy to find and modify.

The `_mask_sensitive` function is applied unconditionally inside `JsonFormatter.format`, so masking cannot be accidentally bypassed by a future caller.

## Consequences

### Positive

- All log lines (app + Uvicorn) are valid JSON, one object per line
- Centralized log collectors can ingest without transformation
- Sensitive values (`password`, `token`, `secret` key prefixes/suffixes) are always masked as `****`
- Startup log emits the full settings object so the running configuration is observable without shell access

### Negative

- Custom `JsonFormatter` must be kept in sync with Uvicorn's `log_config` schema — Mitigation: covered by integration tests that start the app and verify log format.
- Logs are harder to read in a terminal without a JSON pretty-printer — Mitigation: developers can pipe to `jq` or `python -m json.tool`; `LOG_LEVEL=DEBUG` already indicates a dev context.

## Related

- GitHub Issue: N/A
- Beads Task: pa-compact-licensing-platform-vq6
- Implementation Plan: `thoughts/shared/plans/api/2026-04-03-structured-logging.md`

## Notes

Uvicorn's `log_config` dict follows the standard `logging.config.dictConfig` schema. The `'()'` key in `formatters` is the factory callable form, required when passing a class instance rather than a dotted string path.
