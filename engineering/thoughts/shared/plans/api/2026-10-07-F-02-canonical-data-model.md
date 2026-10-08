# F-02 Canonical Data Model (Base Layer) Implementation Plan

## Overview

Build the base layer of the PA Compact Data System's relational data model: the shared tables, keys, relationships, statuses, and conventions that every vertical epic builds on. Columns and tables that belong to a single epic are left to that epic, which adds them by forward-only migration without approval (`mvp-jira-tickets.md:103`). The model follows the **adopted** Rules 3 and 4 (2026-04-06), not the drafts the backlog was written against; where they differ, this plan follows the adopted text (constitution Principle IX) and lists the difference under [Notes for the backlog owner](#notes-for-the-backlog-owner).

The goal is that once Phase 2 merges, every vertical can start its data and API work against stable tables.

## Related

- **Spec**: F-02 in [`product/backlog/mvp-ticket-breakdown.md:248-253`](../../../../../product/backlog/mvp-ticket-breakdown.md); the data-model part of epic 2, "Backend platform", in [`product/backlog/mvp-jira-tickets.md:88-119`](../../../../../product/backlog/mvp-jira-tickets.md)
- **Flows**: all seven; mainly [FLOW-06 state machines](../../../../../product/context/flows/06-state-machines.md), [FLOW-02](../../../../../product/context/flows/02-sql-eligibility-verification.md), [FLOW-03](../../../../../product/context/flows/03-payment-and-remote-state-issuance.md), [FLOW-05](../../../../../product/context/flows/05-adverse-action-cascade.md), [FLOW-07](../../../../../product/context/flows/07-domain-event-catalogue.md)
- **Compact rules** (adopted text): Rule 3 §3.3(a)(5), §3.4(a)–(d), §3.5(a), §3.6(a), §3.7(a)–(b), §3.9(b); Rule 4 §4.2(b)(5), §4.2(f), §4.3(c)–(e), §4.4(a)–(d), §4.5(b)–(f); ML §4.A.8, §4.B, §8.C
- **Decisions**: D1 (computed status), D5 (roles and per-state permissions), D9 (documents), D10 (SSN), D15 (note + resubmit). Questions built to their defaults: Q-03, Q-04, Q-08, Q-10, Q-11, Q-17, Q-20, Q-25. Tensions: TENSION-02, TENSION-03, TENSION-04
- Jira / GitHub issue / beads task: none (backlog item F-02)
- ADRs: [ADR-0003](../../../../adrs/0003-users-table-schema-and-auth-design.md) (PKs, `created_by`, TEXT + CHECK), [ADR-0004](../../../../adrs/0004-jwt-auth-claims-as-user-identity.md) (audit columns from the token); new ADR-0005 to ADR-0008 below
- **Area**: api

## Constitution Check

| Principle | How this plan meets it |
|---|---|
| I. Idiomatic Python and FastAPI | SQLModel models in `repo/<resource>.py`, one file per resource, no business logic. Each `# type: ignore` on `__tablename__` carries its reason. No new runtime dependencies. |
| III. Test coverage | Schema has no endpoints, so its tests are database-level: constraints, triggers, views, and a model-to-DDL drift check. The per-test rollback fixture keeps them isolated. Coverage stays at 100% for the new model modules. |
| IV. No mock code in production | No test or demo rows in migrations. Tests insert their own rows inside a transaction that rolls back. Migrations insert only **reference data the app needs to run**: the jurisdiction list, rule-sourced lookup values, the single `compact_settings` row, and the system user. ADR-0005 states that distinction. |
| VI. The record is the audit trail | Every entity table gets a `<table>_history` table. History and `audit_log` are append-only, enforced by trigger. Foreign keys are `ON DELETE RESTRICT`; nothing cascades a delete. `created_by`/`updated_by` are `users.id`, set from the token (ADR-0004). Provenance per field group on `practitioners` (Rule 4 §4.3(c)). Privilege and license status are computed, never stored (D1). |
| VII. Zero trust | SSN encrypted at the column level by the app (ADR-0007), with a separate keyed hash for duplicate detection. `ssn` added to the log-masking pattern. |
| IX. Plans link to specs, code links to rules | This plan links the spec and flows. Every rule-forced column cites its rule in a SQL comment and in the data dictionary. |
| XI. Prose earns its keep | Docstrings on every model class; the data dictionary in `engineering/docs/data-model.md`; no new components, so no architecture-diagram change. |
| XII. A fresh clone runs from the README | No new tools or services. A future SSN key setting goes in `.env.example` with a local value when U-03 implements encryption. |
| XIII. Dates and deadlines follow one calendar | Calendar dates are `DATE` (`*_on`); instants are `TIMESTAMPTZ` (`*_at`). One reference time zone in `compact_settings`, default `America/New_York` (ADR-0006). The day arithmetic for status lives in one place: the SQL status functions. End dates are inclusive. |
| XIV. Migrations are safe to deploy | Three forward-only migrations. All changes are additive; the one change to an existing table (`users`) adds columns and widens a CHECK, both safe while the old release runs. New tables are empty, so nothing locks a populated table. Tests apply the full chain to an empty database. |
| Security requirements | See [Security Impact Assessment](#security-impact-assessment). |

## Current State Analysis

- The schema is one table, `users` (`engineering/api/db-migrations/20260415_091700_user_table.sql:4-23`): `BIGSERIAL` id, `public_id UUID` (Cognito `sub`), `role TEXT` with `chk_users_role`, `state_code CHAR(2)`, `created_by` (deferrable self-FK), `created_at`. No `updated_at`/`updated_by` anywhere.
- `20250402_000000_initial_tables.sql` is two comment lines and no DDL.
- `30000101_000000_test_data.sql` creates a `test` table and six users, applied only when `environment == 'LOCAL_DEV'` (`licensing_api/migrations.py:24`). This breaks Principle IV; it is left alone here and moved out by a follow-up issue.
- Migrations run at startup via yoyo under a lock (`migrations.py:22`), one transaction per file. Naming: `YYYYMMDD_HHMMSS_description.sql`, `chk_<table>_<what>`, `idx_<table>_<col>`. FKs are unnamed today.
- One SQLModel model, `User` (`licensing_api/repo/user.py:11-23`), hand-synced to the DDL; the model and DDL already disagree on `created_by` nullability.
- `get_db_session` (`licensing_api/dependencies.py:15-20`) neither commits nor rolls back.
- Tests share one database with no cleanup between them (`tests/conftest.py:49-56`); `test_user.py:30-46` restores state by hand.

## Desired End State

- Three migrations create the base layer below on an empty database and on the current DEV database.
- Every table has `created_at`, `created_by`, `updated_at`, `updated_by`, kept consistent by trigger.
- Every entity table has a `<table>_history` table that cannot be updated or deleted outside the audited expungement path.
- Status functions and views return the right status for every case in the fixture matrix, as of any date, in the reference time zone.
- A SQLModel model exists for every table, and a test fails if a model and its table disagree.
- `engineering/docs/data-model.md` documents every table and column, its rule citation, its confidentiality tier, and its owning epic, plus the tables reserved for later epics.
- ADR-0005 to ADR-0008 are written.

### Key Discoveries

- Adopted Rule 3.4(a)(2) (`rule-3-compact-privilege.md:408`) only requires designating a state where the PA holds a full and unrestricted license. The draft's SQL basis tests were not adopted, so there is no `sql_basis` column.
- Adopted Rule 3.5(a) (`rule-3-compact-privilege.md:513`) pins expiry to the license expiry "in effect on the date the PA applied" and adds voluntary termination; the draft's grace rule is gone. The pinned date is captured on the privilege request at submission.
- Rule 4.3(c)(14) (`rule-4-…md:382`) has the SQL submit denials of licensure; only the resulting ineligibility periods are Commission-computed (Rule 4.2(b)(5)).
- Rule 4.4(b)(1) (`rule-4-…md:473`) accepts "a summary of the action taken **or** a copy of the order". Rule 4.4(c)–(d) (`:476-479`) makes SII its own report, from the SQL or a remote state.
- Rule 4.2(f) (`rule-4-…md:294`) requires expunged information to be removed within ten business days, which conflicts with append-only history.

## What We're NOT Doing

- **F-05 code:** `emit()`, `history.write()`, `audit.write()`, the dispatcher, handlers. This plan creates their tables only.
- **Endpoints, queries, or business logic** on any table, beyond what the `User` model already has.
- **SSN encryption code.** ADR-0007 decides the format; U-03 implements it.
- **Demo seed** (`just seed demo`), and moving the existing `30000101` test data out of migrations (follow-up issue).
- **Tables reserved for the owning epics** (named in the dictionary, not created):

  | Reserved table or columns | Owner |
  |---|---|
  | `fees`, `transactions`, `transaction_line_items`, privilege-request proof rows | Epic 8, privilege and payment |
  | `licensure_denials`, state administrator contacts, state fees on `states` | Epic 7, license records and SQL review |
  | `ingestion_batches`, `qualifying_licenses.ingestion_batch_id` | Epic 13, state data ingestion |
  | `renewal_checks`, `privileges.renewed_at` | Epic 9, status and renewal |
  | `attestations` catalogue and accepted-attestation rows | Epic 6, participation |
  | `practitioner_other_names`, address and email change log | Epic 5, accounts and profile |
  | NCCPA lookup source and `fetched_at` | Epic 14, NCCPA |
  | PA-reported adverse actions from non-participating states | Epic 9 |
  | `case_messages` | Deferred (§5.1) |

## Implementation Approach

One migration, one set of models, and one PR per phase. Phase 2 is large; if it exceeds the team's 600-line PR limit, it lands as 2a (practitioner, SSN, documents, licenses, applications) and 2b (privilege requests, privileges, adverse actions, SII), in that order.

Conventions every table follows (written down in ADR-0005):

- **Keys:** `id BIGSERIAL PRIMARY KEY`, never exposed. Entity tables also have `public_id UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE` for use in URLs and responses. Reference tables (`states`, `ref_*`) are keyed by their code, which amends ADR-0003's "BIGSERIAL on every table" for reference data only.
- **Audit columns:** `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `created_by BIGINT NOT NULL`, `updated_at TIMESTAMPTZ NOT NULL`, `updated_by BIGINT NOT NULL`. A `BEFORE INSERT OR UPDATE` trigger, `set_audit_columns()`, fills `updated_at`/`updated_by` from `created_*` on insert and sets `updated_at = now()` on update. The app always supplies `updated_by` on update.
- **Foreign keys:** named `fk_<table>_<column>`, `ON DELETE RESTRICT`, indexed. The `created_by`/`updated_by` FKs are `DEFERRABLE INITIALLY IMMEDIATE`, as in ADR-0003.
- **Value lists:** rule-fixed lists are `TEXT` + a named `CHECK` (ADR-0003). Lists that wait on a Commission answer are `ref_*` lookup tables, so an answer is a data change.
- **Dates:** calendar dates are `DATE` named `*_on`; instants are `TIMESTAMPTZ` named `*_at`.
- **History:** `<table>_history (id, entity_id, changed_at, changed_by, effective_at, previous JSONB, updated JSONB, removed JSONB)`, the shape F-05's `history.write()` will fill. History and `audit_log` get a `prevent_mutation()` trigger that blocks `UPDATE` and `DELETE` unless the transaction has set `app.expunge = 'on'` (ADR-0008).

---

## Phase 1: Conventions and Shared Roots

### Overview

Write the four ADRs, create the shared helpers and root tables, extend `users`, and add the test fixture and dictionary skeleton.

### Changes Required

#### 1. ADRs

**Files**: `engineering/adrs/0005-data-model-conventions.md`, `0006-reference-time-zone-and-dates.md`, `0007-ssn-storage.md`, `0008-expungement-and-append-only-history.md`

Front matter on each, so the compliance skill recognises them:

```markdown
---
category: architecture
status: proposed
date: 2026-10-07
---
```

| ADR | Decision |
|---|---|
| 0005 Data model conventions | The conventions listed under Implementation Approach. Computed status on read (D1), with the precedence: `inactive` (deactivated) over `expired` over `encumbered` over `active`. Reference data the app needs to run may be inserted by migrations; test and demo data may not (clarifies Principles IV and XIV). Amends ADR-0003 for reference-table keys. |
| 0006 Reference time zone and dates | One reference time zone, stored in `compact_settings.time_zone`, default `America/New_York`, raised with the Commission as a new question. "Today" is `compact_today()`. Status day arithmetic lives only in the SQL status functions; Python day arithmetic goes through one module when a later ticket needs it. Inclusive end dates. Business-day calendar deferred to the first ticket that needs it (A-02's reporting windows). |
| 0007 SSN storage | Rule 3 §3.3(a)(5) names the SSN as the unique identifier. Stored in `practitioner_ssn`, encrypted **in the app** with AES-256-GCM (`ssn_ciphertext`, `ssn_key_version`), so the key never reaches the database or its logs. A keyed HMAC-SHA-256 (`ssn_lookup_hash`, separate key) supports uniqueness and lookup without decryption. `ssn_last4` in clear. Keys come from Secrets Manager in deployed environments and from `.env` locally, through the same code path (Principle IV). A full read needs `read_ssn` and writes an `audit_log` row. Supersedes D10's pgcrypto default. |
| 0008 Expungement and append-only history | Rule 4.2(f) requires expunged information removed within ten business days. History and audit rows are append-only by trigger, except inside a transaction that sets `app.expunge = 'on'`, which only the expungement command does. That command replaces the expunged values with `{"redacted": true}` in base and history rows and writes one `audit_log` row naming the fields, the requesting state, and the legal basis, never the values. Building the command is a later ticket; the trigger and the rule land now. |

#### 2. Migration

**File**: `engineering/api/db-migrations/20261007_090000_data_model_shared_roots.sql`

- `CREATE EXTENSION IF NOT EXISTS pgcrypto` only if `gen_random_uuid()` needs it (it is built into Postgres 13+; Aurora 16 and the local `postgres:16-alpine` have it, so skip the extension).
- Functions:

```sql
-- Fills updated_* on insert and stamps updated_at on update (ADR-0005).
CREATE FUNCTION set_audit_columns() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.updated_at := COALESCE(NEW.updated_at, NEW.created_at);
        NEW.updated_by := COALESCE(NEW.updated_by, NEW.created_by);
    ELSE
        NEW.updated_at := now();
    END IF;
    RETURN NEW;
END $$;

-- History and audit rows change only through expungement (ADR-0008).
CREATE FUNCTION prevent_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF current_setting('app.expunge', true) IS DISTINCT FROM 'on' THEN
        RAISE EXCEPTION '% is append-only', TG_TABLE_NAME;
    END IF;
    RETURN COALESCE(NEW, OLD);
END $$;

-- "Today" in the compact's reference time zone (ADR-0006).
CREATE FUNCTION compact_today() RETURNS date LANGUAGE sql STABLE AS $$
    SELECT (now() AT TIME ZONE time_zone)::date FROM compact_settings WHERE id = 1
$$;
```

- `users` (existing, additive only):
  - add `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_by BIGINT` (backfill `= created_by`, then `SET NOT NULL`, FK `fk_users_updated_by` deferrable), `permissions JSONB NOT NULL DEFAULT '{}'` (`{"KS": ["write", "read_private"]}`; D5);
  - replace `chk_users_role` to add `state_admin`;
  - add the `set_audit_columns` trigger;
  - insert the **system user** (`system@pa-compact.invalid`, role `admin`, `is_active = false`, `public_id` NULL, `created_by` = its own id). Workers and jobs write as this user. Inactive and with an undeliverable address, so it can never log in.
- `compact_settings`: one row (`id SMALLINT PRIMARY KEY CHECK (id = 1)`), `time_zone TEXT NOT NULL DEFAULT 'America/New_York'`, audit columns. Insert the row. Later epics add the Commission fee and live-state settings here.
- `states`: `code CHAR(2) PRIMARY KEY`, `name`, `is_member BOOLEAN NOT NULL DEFAULT false`, `member_effective_on DATE`, `is_live BOOLEAN NOT NULL DEFAULT false`, `practice_requirements_url TEXT`, and four proof requirements (`jurisprudence_requirement`, `supervision_agreement_requirement`, `prescriptive_authority_requirement`, `other_compliance_requirement`), each `TEXT NOT NULL DEFAULT 'none'` with `CHECK (… IN ('none','attestation','proof_upload'))` (Rule 3 §3.4(c)(3)–(6)). Audit columns. Insert the 50 states, DC, and the five inhabited territories with `is_member = false`; membership is configuration (Q-03), set through S-01 or seed tooling.
- `users.state_code` gains `fk_users_state_code` to `states(code)`.
- Lookup tables, each `(code TEXT PRIMARY KEY, label TEXT NOT NULL, sort_order SMALLINT NOT NULL, is_active BOOLEAN NOT NULL DEFAULT true)` plus audit columns:
  - `ref_sex` — empty; epic 5 fills it when Q-10 is answered.
  - `ref_adverse_action_types` — inserted from ML §2.A: denial, censure, revocation, suspension, probation, monitoring, restriction.
  - `ref_npdb_categories` — empty; epic 9 fills it (Q-17).
  - `ref_denial_reasons` — adds `applies_to TEXT CHECK (applies_to IN ('eligibility','privilege'))`; inserted from the ML §4.A eligibility criteria plus `other` (Q-08 default).
- `audit_log`: `id`, `occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `actor_user_id` FK, `action TEXT NOT NULL`, `entity_type TEXT NOT NULL`, `entity_id BIGINT`, `before JSONB`, `after JSONB`, `reason TEXT`, `request_id TEXT`; `prevent_mutation` trigger; index on `(entity_type, entity_id)`.
- `domain_events`: `id`, `event_id UUID NOT NULL DEFAULT gen_random_uuid() UNIQUE`, `type TEXT NOT NULL`, `aggregate_type TEXT NOT NULL`, `aggregate_id BIGINT NOT NULL`, `payload JSONB NOT NULL`, `actor_user_id` FK, `request_id TEXT`, `occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()`. `domain_event_deliveries`: `(event_id, handler)` primary key, `attempts`, `last_error`, `handled_at`, `dead_lettered_at`. Payloads carry IDs, not PII (stated in the dictionary).
- `notifications`: `id`, `public_id`, `template TEXT NOT NULL`, `recipient_user_id` FK nullable, `recipient_email TEXT NOT NULL`, `context JSONB NOT NULL`, `idempotency_key TEXT NOT NULL UNIQUE`, `status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','sent','failed'))`, `attempts`, `last_error`, `sent_at`, audit columns.

#### 3. Models

**Files**: `engineering/api/licensing_api/repo/user.py` (add `updated_at`, `updated_by`, `permissions`; make `created_by` non-optional to match the DDL), and new `repo/state.py`, `repo/compact_settings.py`, `repo/reference.py`, `repo/audit_log.py`, `repo/domain_event.py`, `repo/notification.py`. JSONB columns use `sa_column=Column(JSONB)`. Each class has a docstring stating what the table holds and its owner.

#### 4. Log masking

**File**: `engineering/api/licensing_api/__main__.py:29` — add `ssn` to `_SENSITIVE_PATTERN`.

#### 5. Test infrastructure

**File**: `engineering/api/tests/conftest.py`

- A function-scoped async `db_session` fixture: open a connection on its own engine, `BEGIN`, bind an `AsyncSession` with `join_transaction_mode='create_savepoint'`, yield, `ROLLBACK`. It depends on the module-scoped `client` fixture so migrations have run.
- **File**: `engineering/api/tests/factories.py` — small async builders (`make_user`, `make_practitioner`, …) that insert one valid row with overridable fields. Phase 2 and 3 tests use them.
- **File**: `engineering/api/tests/test_model_schema.py` — for every SQLModel table model, compare its columns, types, and nullability with `information_schema.columns`; fail on any difference.

#### 6. Data dictionary skeleton

**File**: `engineering/docs/data-model.md` — conventions (linking ADR-0005 to ADR-0008), a Mermaid `erDiagram`, one section per table (columns, meaning, rule citation, confidentiality tier, owning epic), and the reserved-tables list from "What We're NOT Doing".

### Success Criteria

#### Automated Verification

- [x] Local services running: `cd engineering/api && just infra`
- [x] Tests pass with coverage: `cd engineering/api && just test-coverage`
- [x] Linting, formatting, and type checking pass: `cd engineering/api && just lint`
- [x] Markdown lint passes: `pre-commit run --files engineering/adrs/*.md engineering/docs/data-model.md`
- [x] Tests prove: updating a `users` row sets `updated_at`; inserting without `updated_by` copies `created_by`; `UPDATE` and `DELETE` on `audit_log` raise unless `app.expunge` is `on`; `compact_today()` returns the date in `America/New_York` around midnight UTC; the role CHECK accepts `state_admin`; the model-schema test passes.

#### Local Integration

- [x] The current local database (with the `20260415` migration and seed applied) upgrades cleanly: `cd engineering/api && just dev`, then `curl localhost:8000/api/health/ready`.
- [x] `/api/me` still works for a seeded user (existing `test_user.py` passes).

#### Manual Verification

- [x] The tech lead reviews ADR-0005 to ADR-0008 and the dictionary skeleton.

**Implementation Note**: after this phase passes automated verification, pause for the human to confirm the ADRs before Phase 2 builds on them.

**Implemented 2026-10-07; differences from the plan, which Phase 2 follows:**

- **Instants need `TimestampTZ` in the model.** SQLModel maps `datetime` to a timestamp *without* time zone, so ORM inserts of aware datetimes failed. Every instant field uses `sa_type=TimestampTZ` (`licensing_api/repo/base.py`), and `test_model_schema.py` fails on any naive datetime column. The existing `User` model had the same latent bug.
- **`users` ↔ `states` foreign-key cycle.** `users.state_code` references `states` and `states.created_by` references `users`; the model marks `fk_users_state_code` `use_alter=True` so SQLAlchemy can order inserts.
- **`licensing_api/repo/__init__.py`** imports every table model so foreign keys resolve whichever model is used first. Phase 2 models are added there.
- **`compact_date_at(instant)`** was added beside `compact_today()`, so date-boundary tests pass an instant instead of freezing the database clock.
- **Running one test file:** the `just test` recipe's first argument is the env file, so use `just test .env tests/<file>.py`.

---

## Phase 2: Core Entity Graph

### Overview

Create the tables every vertical touches, with their keys, foreign keys, statuses, rule-fixed fields, and history tables. Every table below also has the four audit columns, the `set_audit_columns` trigger, `public_id`, and a `<table>_history` table with the `prevent_mutation` trigger.

### Changes Required

#### 1. Migration

**File**: `engineering/api/db-migrations/20261007_100000_data_model_core_entities.sql` (split into `…_core_entities_a.sql` and `…_b.sql` if the PR is split)

**`practitioners`** — the uniform data set (Rule 4 §4.3(c)). Owner: platform (shared root).

| Column | Type | Notes |
|---|---|---|
| `user_id` | BIGINT NOT NULL UNIQUE, FK `users` | |
| `current_sql_state_code` | CHAR(2) FK `states`, NULL | Set when an application becomes `eligible` |
| `legal_first_name`, `legal_middle_name`, `legal_last_name`, `name_suffix` | TEXT | §4.3(c)(1) |
| `sex_code` | TEXT FK `ref_sex`, NULL | §4.3(c)(3), Q-10 |
| `date_of_birth` | DATE | §4.3(c)(4) |
| `residence_line1`, `residence_line2`, `residence_city`, `residence_region`, `residence_postal_code`, `residence_country_code` | TEXT | §4.3(c)(6), primary residence of record |
| `phone`, `correspondence_email` | TEXT | §4.3(c)(7)–(8) |
| `pa_program_name`, `pa_program_graduation_year` | TEXT, SMALLINT | §4.3(c)(9) |
| `nccpa_certification_number`, `nccpa_certification_status`, `nccpa_certification_expires_on` | TEXT, TEXT, DATE | §4.3(c)(10) |
| `npi` | TEXT, NULL | Not in the adopted uniform data set; optional and never verified |
| `<group>_entered_by`, `<group>_verified_by_state`, `<group>_verified_at` for groups `identity`, `residence`, `contact`, `education`, `certification` | BIGINT FK `users`; CHAR(2) FK `states`; TIMESTAMPTZ | Provenance (Rule 4 §4.3(c); `SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance`). `CHECK ((<g>_verified_by_state IS NULL) = (<g>_verified_at IS NULL))` per group |

**`practitioner_ssn`** — restricted tier (ADR-0007). No history table; changes are recorded in `audit_log` without the value.

| Column | Type | Notes |
|---|---|---|
| `practitioner_id` | BIGINT NOT NULL UNIQUE, FK | One SSN per practitioner |
| `ssn_ciphertext` | BYTEA NOT NULL | AES-256-GCM, nonce prepended |
| `ssn_key_version` | SMALLINT NOT NULL | For key rotation |
| `ssn_lookup_hash` | BYTEA NOT NULL UNIQUE | Keyed HMAC; detects a second account with the same SSN |
| `ssn_last4` | CHAR(4) NOT NULL, `CHECK (ssn_last4 ~ '^[0-9]{4}$')` | |

**`documents`** (D9). Owner: platform. No `public_id` change from the rest.

| Column | Type | Notes |
|---|---|---|
| `owner_type` | TEXT NOT NULL, CHECK in (`practitioner`, `participation_application`, `privilege_request`, `adverse_action`, `sii_report`) | Polymorphic; no FK, index on `(owner_type, owner_id)` |
| `owner_id` | BIGINT NOT NULL | |
| `kind` | TEXT NOT NULL | Free text until Q-07 is answered |
| `storage_key` | TEXT NOT NULL UNIQUE | S3 or RustFS object key |
| `file_name`, `content_type`, `size_bytes` | TEXT, TEXT, BIGINT | |
| `scan_status` | TEXT NOT NULL DEFAULT `pending`, CHECK in (`pending`, `clean`, `infected`, `error`) | |

**`qualifying_licenses`** — SQL-authored (Rule 4 §4.3(c)(11)). Owner: epic 7.

| Column | Type | Notes |
|---|---|---|
| `practitioner_id` | BIGINT FK, NULL | NULL until linked; an uploaded license (epic 13) may arrive first |
| `state_code` | CHAR(2) NOT NULL FK `states` | |
| `license_number` | TEXT NOT NULL | `UNIQUE (state_code, license_number)` |
| `state_reported_status` | TEXT NOT NULL, CHECK in (`active`, `expired`, `lapsed`, `inactive`, `terminated`) | FLOW-05; reinstatement sets `active` |
| `status_effective_on` | DATE NOT NULL | |
| `issued_on`, `expires_on` | DATE | |
| `is_unrestricted` | BOOLEAN NOT NULL | Rule 3 §3.4(a)(2) |
| `terminated_on` | DATE, NULL | Voluntary termination, Rule 3 §3.5(a), §3.6(a) |
| `source` | TEXT NOT NULL DEFAULT `manual`, CHECK in (`manual`, `upload`, `api`) | |
| `verified_by`, `verified_at` | BIGINT FK `users`, TIMESTAMPTZ | Paired NULL check |

**`participation_applications`** — Phase 1 of the workflow (FLOW-02, FLOW-06). Owner: epic 6.

| Column | Type | Notes |
|---|---|---|
| `practitioner_id` | BIGINT NOT NULL FK | |
| `kind` | TEXT NOT NULL DEFAULT `initial`, CHECK in (`initial`, `change_sql`) | Rule 3 §3.6(a) |
| `sql_state_code` | CHAR(2) NOT NULL FK `states` | No `sql_basis` (Rule 3 §3.4(a)(2)) |
| `qualifying_license_id` | BIGINT FK, NULL | |
| `status` | TEXT NOT NULL DEFAULT `draft`, CHECK in (`draft`, `submitted`, `info_requested`, `eligible`, `denied`, `withdrawn`, `eligibility_withdrawn`) | FLOW-06 |
| `opened_at` | TIMESTAMPTZ, NULL | Received by the SQL; starts the 60-day clock (Rule 3 §3.7(a)) |
| `request_note` | TEXT, NULL | D15 |
| `license_verified_at`, `license_verified_by` | TIMESTAMPTZ, BIGINT FK | |
| `cbc_completed_on` | DATE, NULL | Date only; never a result (Rule 4 §4.2) |
| `decided_at`, `decided_by` | TIMESTAMPTZ, BIGINT FK | |
| `denial_reason_code`, `denial_reason_detail` | TEXT FK `ref_denial_reasons`, TEXT | |
| `withdrawn_at` | TIMESTAMPTZ | |
| `eligibility_withdrawn_at`, `eligibility_withdrawal_reason` | TIMESTAMPTZ, TEXT | Rule 3 §3.9(b) |

Constraints: `opened_at` required once not `draft`; `decided_at`, `decided_by` required for `eligible`/`denied`; `eligible` requires `license_verified_at` and `cbc_completed_on` (FLOW-02 guard); `denied` requires `denial_reason_code`; partial unique index: one open application (`draft`, `submitted`, `info_requested`) per practitioner. Index `(sql_state_code, status)` for the SQL queue.

**`privilege_requests`** — Phase 2 of the workflow (FLOW-03). Owner: epic 8.

| Column | Type | Notes |
|---|---|---|
| `participation_application_id` | BIGINT NOT NULL FK | |
| `practitioner_id` | BIGINT NOT NULL FK | For state-scoped queries |
| `remote_state_code` | CHAR(2) NOT NULL FK `states` | |
| `qualifying_license_id` | BIGINT NOT NULL FK | |
| `status` | TEXT NOT NULL DEFAULT `pending_payment`, CHECK in (`pending_payment`, `submitted`, `issued`, `denied`, `withdrawn`) | `withdrawn` replaces FLOW-06's `abandoned` (Rule 3 §3.7(b)(1)) |
| `ql_expires_on_snapshot` | DATE, NULL | Required once `submitted`; becomes the privilege's expiry (Rule 3 §3.5(a)) |
| `submitted_at` | TIMESTAMPTZ | Received by the remote state (Rule 3 §3.7(b)) |
| `decided_at`, `decided_by`, `denial_reason_code`, `denial_reason_detail` | | As on applications |

Partial unique index: one open request (`pending_payment`, `submitted`) per `(practitioner_id, remote_state_code)`. Index `(remote_state_code, status)` for the issuance queue.

**`privileges`** — remote-state-authored (Rule 4 §4.3(d)). Owner: epic 8.

| Column | Type | Notes |
|---|---|---|
| `privilege_request_id` | BIGINT NOT NULL UNIQUE FK | |
| `practitioner_id`, `remote_state_code`, `qualifying_license_id` | FKs, NOT NULL | Rule 3 §3.5(a): "the qualifying license used to apply" |
| `privilege_number` | TEXT NOT NULL UNIQUE | `PA-{RS}-{n}` |
| `state_privilege_identifier` | TEXT, NULL | Rule 4 §4.3(d)(1) "other unique privilege identifier" |
| `issued_at` | TIMESTAMPTZ NOT NULL | |
| `expires_on` | DATE NOT NULL | Pinned; inclusive |
| `administrator_status` | TEXT NOT NULL DEFAULT `active`, CHECK in (`active`, `inactive`) | |
| `deactivation_reason` | TEXT, CHECK in (`qualifying_license_adverse_action`, `eligibility_withdrawn`, `qualifying_license_inactive`, `qualifying_license_terminated`, `sql_changed`, `state_deactivated`) | `sql_changed` per Rule 3 §3.6(d). `CHECK ((administrator_status = 'inactive') = (deactivation_reason IS NOT NULL))` |
| `deactivated_at`, `deactivation_note` | TIMESTAMPTZ, TEXT | |

**`adverse_actions`** (Rule 4 §4.4(a)–(b)). Owner: epic 9.

| Column | Type | Notes |
|---|---|---|
| `practitioner_id` | BIGINT NOT NULL FK | |
| `reporting_state_code` | CHAR(2) NOT NULL FK `states` | |
| `against` | TEXT NOT NULL, CHECK in (`qualifying_license`, `privilege`) | |
| `qualifying_license_id`, `privilege_id` | FKs, NULL | `CHECK` that exactly the one matching `against` is set |
| `action_type_code` | TEXT NOT NULL FK `ref_adverse_action_types` | |
| `summary` | TEXT, NULL | |
| `order_document_id` | BIGINT FK `documents`, NULL | `CHECK (summary IS NOT NULL OR order_document_id IS NOT NULL)` (§4.4(b)(1)) |
| `ordered_on`, `effective_from`, `effective_until` | DATE, DATE NOT NULL, DATE NULL | `effective_until` NULL while in force; inclusive |
| `is_emergency`, `is_public` | BOOLEAN NOT NULL, default false | |
| `reported_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | Reporting window (§4.4(b)(2)) |

Join table `adverse_action_npdb_categories (adverse_action_id, npdb_category_code)` with FKs; optional (Q-17).

**`sii_reports`** (Rule 4 §4.4(c)–(d)). Owner: epic 9. States and Commission only (ML §8.C).

| Column | Type | Notes |
|---|---|---|
| `practitioner_id`, `reporting_state_code` | FKs, NOT NULL | SQL or remote state |
| `qualifying_license_id`, `privilege_id` | FKs, NULL | |
| `description` | TEXT NOT NULL | |
| `contact_name`, `contact_email`, `contact_phone` | TEXT | §4.4(d) |
| `public_complaint_document_id` | BIGINT FK `documents`, NULL | §4.4(d)(1) |
| `determined_on` | DATE NOT NULL | Starts the five-business-day window (§4.4(d)(2)) |
| `reported_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| `closed_at`, `closed_by` | TIMESTAMPTZ, BIGINT FK | |

History tables: `practitioners_history`, `qualifying_licenses_history`, `participation_applications_history`, `privilege_requests_history`, `privileges_history`, `adverse_actions_history`, `sii_reports_history`, each with `fk_<table>_history_entity_id` and an index on `(entity_id, changed_at)`.

#### 2. Models

**Files**: `engineering/api/licensing_api/repo/practitioner.py` (with `PractitionerSsn`), `document.py`, `qualifying_license.py`, `participation_application.py`, `privilege_request.py`, `privilege.py`, `adverse_action.py`, `sii_report.py`, and `history.py` (one model per history table, generated from a shared base class). Status values are `StrEnum`s in the same modules, matching the CHECK constraints.

#### 3. Dictionary

**File**: `engineering/docs/data-model.md` — sections for every Phase 2 table: columns, rule citation, confidentiality tier (public, states and Commission, restricted), owning epic.

### Success Criteria

#### Automated Verification

- [x] Tests pass with coverage: `cd engineering/api && just test-coverage`
- [x] Linting, formatting, and type checking pass: `cd engineering/api && just lint`
- [x] Constraint tests (using `factories.py` and `db_session`) prove each rule-fixed constraint rejects a bad row:
  - an `eligible` application without `cbc_completed_on`;
  - a second open application for the same practitioner;
  - an `inactive` privilege without a reason;
  - an adverse action with neither summary nor order document, or with `against = privilege` and no `privilege_id`;
  - a `submitted` privilege request without `ql_expires_on_snapshot`;
  - a duplicate `(state_code, license_number)`;
  - deleting a practitioner with applications (RESTRICT).
- [x] History tables reject `UPDATE`/`DELETE`.
- [x] The model-schema test passes for every new model.

#### Manual Verification

- [ ] The tech lead and PM review the dictionary's Phase 2 sections (F-02 acceptance: "dictionary reviewed by tech lead + PM").

**Implementation Note**: once this phase merges, tell the vertical owners the base is ready; Phase 3 can proceed in parallel with their work.

**Implemented 2026-10-07 as 2a and 2b; differences from the plan, which Phase 3 follows:**

- **Two migrations**, `20261007_100000_data_model_core_entities_a.sql` and `20261007_110000_data_model_core_entities_b.sql`, committed separately. Phase 3's migration therefore takes `20261007_120000`.
- **Two reusable helpers** in migration 2a: `add_audit_columns_trigger(table)` and `create_history_table(table)`. Later epics call them when adding entity tables.
- **`privilege_requests.withdrawn_at`** was added, required when `status = 'withdrawn'`, matching the application table.
- **`documents` has no `uploaded_by`**: `created_by` is the uploader.
- **History models use `sa_type=JSONB`**, not `sa_column`: one Column object cannot be shared by several tables.
- **Two structural tests** guard later epics: every table with audit columns has the audit trigger, and every `*_history` table has the append-only trigger.

**Review fixes, 2026-10-08** (PR #81 review: can epics start concurrently, and do the flows fit). Made in place in the three migrations, which no shared environment had applied:

- A `licensee` may have no `state_code` (FLOW-01 self-signup was rejected).
- An `eligible` application must link a qualifying license; `claimed_license_number` and `claimed_license_expires_on` hold what the PA entered (FLOW-02's claimed-versus-on-file comparison).
- A `superseded` status, with `superseded_at`, and one `eligible` application per practitioner, so a change of SQL cannot leave two in force.
- `fees` moved from the reserved list into the base, owned by epic 7 and read by epics 8 and 9; the Commission's fees are rows with no state.
- `documents` may be uploaded before its owner exists, and can be owned by a `state` (by `owner_key`) or an `ingestion_batch`.
- `states_history`, plus `aggregate_key` on `domain_events` and `entity_key` on `audit_log`, for records keyed by text.
- `privilege_number_sequences` and `next_privilege_number()` for `PA-{state}-{n}`; a `commission_deactivated` reason.
- Every non-audit foreign key indexed, enforced by a test.
- A `route_db_session` test fixture rolls back what routes write.
- ADR-0005 names owners for the status functions, `compact_settings`, and `fees`; the dictionary's reserved list names a home and owner for state contacts, machine credentials, the pending email change, service-of-process consent, NCCPA lookups, the renewal link, and the transaction webhook key.

---

## Phase 3: Status Views and Fixture Matrix

### Overview

Compute license status, privilege status, and compact eligibility on read, as of any date, and prove them against every FLOW-06 case.

### Changes Required

#### 1. Migration

**File**: `engineering/api/db-migrations/20261007_120000_data_model_status_views.sql`

- `qualifying_license_status_on(as_of DATE)` returns one row per license: `active` when `state_reported_status = 'active'`, `as_of <= expires_on`, `terminated_on` is NULL or later than `as_of`, and no in-force adverse action against it; otherwise `expired`, `terminated`, `encumbered`, or the reported status. View `v_qualifying_license_status` = the function at `compact_today()`.
- `privilege_status_on(as_of DATE)` returns `status` and `status_reason` per privilege, with precedence `inactive` (with `deactivation_reason`), `expired` (`as_of > expires_on`), `encumbered` (an adverse action against the privilege with `effective_from <= as_of` and `effective_until` NULL or `>= as_of`), else `active`. View `v_privilege_status`.
- `compact_eligibility_on(as_of DATE)` returns per practitioner `eligible_again_on`: NULL when no adverse action against a qualifying license applies; the latest `effective_until + 2 years` when all have ended; and barred with no date while any is still in force (ML §4.A.8). View `v_compact_eligibility`.
- These three functions are the only place status day arithmetic lives (ADR-0006).

#### 2. Models

**File**: `engineering/api/licensing_api/repo/status.py` — read-only SQLModel models over the three views.

#### 3. Fixture-matrix tests

**File**: `engineering/api/tests/test_status_views.py` — one parametrised table, each row building the scenario with `factories.py` and asserting the function's result as of a given date:

| Case | Expected |
|---|---|
| Issued, before expiry | `active` |
| On the expiry date | `active` (inclusive) |
| Day after expiry | `expired` |
| License renewed after the request | still expires on the pinned date |
| License still reported active past the pinned date | `expired` (no grace under adopted Rule 3.5(a)) |
| Each `deactivation_reason` | `inactive` with that reason |
| Deactivated and past expiry | `inactive` (precedence) |
| Adverse action against the privilege, in force | `encumbered` |
| Same, on its `effective_until` date / the day after | `encumbered` / `active` |
| License adverse action in force | eligibility barred, no date |
| License adverse action ended | `eligible_again_on = effective_until + 2 years`; barred the day before, eligible on the day |
| License voluntarily terminated | license `terminated` |
| `compact_today()` at 23:30 New York on the expiry date (04:30 UTC the next day) | `active` |

#### 4. Dictionary completion

**File**: `engineering/docs/data-model.md` — the status functions and views, the precedence, and the final ownership table.

### Success Criteria

#### Automated Verification

- [ ] Tests pass with coverage: `cd engineering/api && just test-coverage`
- [ ] Linting, formatting, and type checking pass: `cd engineering/api && just lint`
- [ ] Every row of the fixture matrix passes.
- [ ] The full migration chain applies to an empty database (fresh `just infra`, then `just test`).

#### Manual Verification

- [ ] The tech lead and PM sign off the dictionary (F-02 acceptance).
- [ ] The migrations apply cleanly to DEV after merge.

---

## Testing Strategy

### Database tests (no endpoints exist for these tables yet)

- Constraint, trigger, and view tests run against real Postgres through the rolling-back `db_session` fixture and `factories.py`; no test depends on another's rows.
- `test_model_schema.py` keeps every model in step with its table.
- Endpoint tests arrive with the verticals that add routes, per Principle III.

### E2E Tests

- Not applicable: no UI or routes change.

### Manual Testing Steps

1. Run `just infra` and `just dev` on a fresh database and confirm startup applies all migrations.
2. Run `just dev` on a database that already has the `20260415` migration and local seed; confirm it upgrades.
3. In `psql`, insert a practitioner, application, request, and privilege by hand and check `v_privilege_status`.

## Security Impact Assessment

| Data | Tier | Where it lives | Protection | What could go wrong |
|---|---|---|---|---|
| SSN | Restricted | `practitioner_ssn` | App-side AES-256-GCM with a key from Secrets Manager; keyed hash for lookup; last 4 in clear; full read needs `read_ssn` and writes `audit_log`; no history table; `ssn` masked in logs | Key loss makes SSNs unrecoverable (Secrets Manager versioning, `ssn_key_version`); a hash without a secret key would be brute-forceable (the hash is keyed) |
| Date of birth, residence, phone, email, education, certification | States and Commission (private) | `practitioners`, `practitioners_history` | Aurora encryption at rest; tier enforced in API response models | History JSONB copies these values, so history carries the same tier and the same response-model rules |
| SII | States and Commission only; never the PA or public (ML §8.C) | `sii_reports` | Separate table, so a query on adverse actions cannot return SII by accident | A future join that exposes SII to a PA endpoint; the dictionary marks it, and F-03's permission annotation must cover it |
| Non-public adverse actions | States and Commission | `adverse_actions` (`is_public = false`) | Public verification reads only `is_public = true` | Public endpoints must filter; V-01 tests it |
| Criminal background check | Never stored | `cbc_completed_on` only | A DATE column cannot hold a result | A free-text field misused for results; `denial_reason_detail` is reviewed in L-05 |
| Domain event payloads | — | `domain_events` | IDs only, no PII (dictionary rule) | A producer adding PII to a payload; F-05 adds a test |

## Dates and Deadlines

- Computed here: privilege expiry (`expires_on`, inclusive), adverse-action in-force windows (inclusive), and `eligible_again_on` (`effective_until + 2 years`).
- Computed in: the three SQL status functions only, with "today" from `compact_today()` in `compact_settings.time_zone` (ADR-0006).
- Stored as `DATE`: `expires_on`, `issued_on`, `status_effective_on`, `terminated_on`, `cbc_completed_on`, `ordered_on`, `effective_from`, `effective_until`, `determined_on`, `ql_expires_on_snapshot`, `date_of_birth`, `nccpa_certification_expires_on`, `member_effective_on`.
- Boundary tests: the last day, the day after, the two-year bar's day before and day of, and the New York midnight case (Phase 3 matrix). The 60-day withdrawal clock and the business-day reporting windows are computed by L-06 and A-02, which add the day-arithmetic module and the holiday calendar.

## Migration Notes

- Three migrations, forward-only, no edits to applied files.
- **Phase 1 changes an existing table.** Adding `updated_at` with a default, adding `updated_by` (backfilled, then `NOT NULL`), adding `permissions` with a default, and replacing `chk_users_role` with a wider list are all safe while the current release runs: it neither reads nor writes the new columns, the trigger fills `updated_by` when old code inserts, and widening a CHECK accepts every existing row. `users` has a handful of rows, so the constraint validation is instant.
- Every other table is new and empty; nothing rewrites or locks a populated table.
- Reference rows (jurisdictions, rule-sourced lookups, `compact_settings`, the system user) are reference data required to run, not test data (ADR-0005).
- The local-only `30000101_000000_test_data.sql` still sorts after these files; it does not reference the new tables, so it keeps applying locally until the follow-up moves it.

## Documentation Updates

- `engineering/adrs/0005` to `0008` (new).
- `engineering/docs/data-model.md` (new): conventions, ER diagram, every table and column, rule citations, tiers, owners, reserved tables.
- Docstrings on every model class.
- No new dependencies, so the README dependency table and the licence inventory are unchanged.

## Performance Considerations

- Every FK is indexed; queue indexes on `(sql_state_code, status)` and `(remote_state_code, status)`; partial unique indexes enforce the one-open-item rules.
- The status functions scan privileges with a lateral lookup on in-force adverse actions; at pilot scale (thousands of rows) this is negligible. If a later ticket measures otherwise, it can materialise the view.

## Notes for the Backlog Owner

For @mkalish; none of these change this plan, which follows the adopted rules. They need updates in `product/` or a question to the Commission:

1. **F-02's field list follows the drafts.** Dropped: `sql_basis` (Rule 3 §3.4(a)(2)), the "R3r §3.5(c) grace" fixture (Rule 3 §3.5(a)). Added: `licensure_denials` as state-authored (Rule 4 §4.3(c)(14)), SII as its own report (Rule 4 §4.4(c)–(d)), voluntary termination and SQL change (Rule 3 §3.5(a), §3.6), and a participation fee type (Rule 3 §3.4(a)(7)), which contradicts Q-05's "no participation fee" default.
2. **Flows and signals still carry draft text:** FLOW-01:54 and FLOW-02:32 (SQL basis); FLOW-04:58 (grace); FLOW-02:116 and the uniform-data-set signal (denials "never entered by a state"); FLOW-05 says eligibility withdrawal "cancels" privileges while FLOW-06 says `inactive`; FLOW-06 says `abandoned` where Rule 3 §3.7(b)(1) says "withdrawn".
3. **Questions now obsolete or changed:** Q-11's "last-4 + NPI" option is closed by Rule 3 §3.3(a)(5); Q-16 is obsolete (Rules 3 and 4 adopted 2026-04-06); Q-08's 30-day appeal window is gone from adopted Rule 3 §3.9(a); Q-03's member count is 29 per the 2026-10-01 change index, not 20.
4. **New questions for the Commission:** the reference time zone (default America/New_York, ADR-0006); how expungement requests arrive (ADR-0008, Rule 4 §4.2(f)).
5. **Review fixes that change the flows.** FLOW-06 gains a `superseded` application status for a change of SQL. FLOW-01 and FLOW-02's claimed license is stored on the application. Fee types are `participation`, `privilege`, and `renewal`, with the Commission's fees as rows with no state.
6. **Citations:** the backlog cites `R5 §5.3` and `ATOM-GOV-R5-02`; the adopted section is Rule 4 §4.3 and `ATOM-GOV-R4-01`.

## References

- Spec: `product/backlog/mvp-ticket-breakdown.md` F-02; `product/backlog/mvp-jira-tickets.md` epic 2
- Adopted rules: `product/context/research-corpus/sources/rule-3-compact-privilege.md`, `rule-4-compact-data-system--confidentiality-information-sharing.md`
- Draft-versus-adopted change index: `product/context/evidence/CHANGES-2026-10-01-adopted-rules.md`
- Existing pattern: `engineering/api/db-migrations/20260415_091700_user_table.sql`, `engineering/api/licensing_api/repo/user.py`
- CompactConnect data model (not cloned locally): `cc_common/data_model/schema/{provider,license,privilege,adverse_action}/record.py` at github.com/csg-org/CompactConnect
