---
category: architecture
status: proposed
date: 2026-10-07
---

# ADR-0005: Data Model Conventions

## Status

Proposed

## Date

2026-10-07

## Context

F-02 adds the data system's base layer: about twenty tables that every vertical epic builds on and then extends with its own forward-only migrations. ADR-0003 set conventions for the `users` table only. The engineering constitution requires a record that retains every change (Principle VI), dates handled as dates (Principle XIII), and safe migrations (Principle XIV). Without written conventions, each epic would invent its own and the model would drift.

## Decision

Every table follows these rules. The data dictionary (`engineering/docs/data-model.md`) documents each table against them.

1. **Keys.** `id BIGSERIAL PRIMARY KEY`, never exposed outside the API. Tables whose rows are referenced in URLs or responses also have `public_id UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE`. Reference tables (`states`, `ref_*`) are keyed by their code instead; this amends ADR-0003's "BIGSERIAL on every table" for reference data only.
2. **Audit columns.** `created_at`, `created_by`, `updated_at`, `updated_by`, all `NOT NULL`, with `created_by` and `updated_by` referencing `users(id)`. The `set_audit_columns()` trigger copies `created_*` into `updated_*` on insert and stamps `updated_at` on update; the caller sets `updated_by` from the token (ADR-0004). Writes made by workers and jobs use the **system user** (`system@pa-compact.invalid`), which is inactive and cannot sign in.
3. **Foreign keys.** Named `fk_<table>_<column>`, indexed, and `ON DELETE RESTRICT` (the default): nothing cascades a delete. `created_by` and `updated_by` foreign keys are `DEFERRABLE INITIALLY IMMEDIATE`, as in ADR-0003.
4. **Value lists.** Lists the compact rules fix are `TEXT` with a named `CHECK` (ADR-0003). Lists that wait on a Commission answer are `ref_*` lookup tables, so an answer is a data change, not a migration.
5. **Dates.** Calendar dates are `DATE` and named `*_on`; instants are `TIMESTAMPTZ` and named `*_at`. Models declare instants with `TimestampTZ` (`licensing_api/repo/base.py`), because SQLModel's default for `datetime` is a timestamp without time zone. ADR-0006 covers the reference time zone.
6. **History.** Every entity table has a `<table>_history` table: `entity_id`, `changed_at`, `changed_by`, `effective_at`, and `previous`, `updated`, `removed` as JSONB. History and `audit_log` are append-only by trigger (ADR-0008).
7. **Status.** A status a rule derives is computed on read, never stored (backlog decision D1). Privilege status has the precedence `inactive` (deactivated), then `expired`, then `encumbered`, then `active`.
8. **Reference data versus test data.** A migration may insert rows the application needs to run: the jurisdiction list, rule-sourced lookup values, the `compact_settings` row, and the system user. It may not insert test or demo data (Principles IV and XIV); tests create their own rows and roll them back.
9. **Models.** One SQLModel model per table, in `licensing_api/repo/`, registered in `licensing_api/repo/__init__.py`. `tests/test_model_schema.py` fails if a model and its table disagree on columns, types, or nullability, or if a table has no model.

## Consequences

- Every table carries four audit columns and, for entities, a history table. That is more columns and tables, in exchange for a record the rules require.
- Workers and jobs need the system user's id to write. It is found by email, not by a fixed id.
- Constitution Principle XIV's "no seed data" should read "no test or demo data", to match point 8.
- An epic adding a table follows these rules and adds a model; the schema test enforces the model.
