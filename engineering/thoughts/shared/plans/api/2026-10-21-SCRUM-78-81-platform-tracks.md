# Epic 2 Platform Tracks (SCRUM-78 to SCRUM-81) Implementation Plan

## Overview

Build the four remaining epic 2 tracks on the [platform contract](../../../../docs/platform-contract.md): the dispatcher and privilege cascade (SCRUM-78), the API rules, generated client and demo seed (SCRUM-79), the Worker and email (SCRUM-80), and documents (SCRUM-81). One linear stack of thirteen PRs, each under the 600-line limit (Principle XV): `main ← 78 ← 79 ← 80 ← 81`.

## Related

- **Spec**: epic 2 in [`product/backlog/mvp-jira-tickets.md` §2](../../../../../product/backlog/mvp-jira-tickets.md); F-03, F-05, F-11, F-12, F-13, H-05 in [`mvp-ticket-breakdown.md`](../../../../../product/backlog/mvp-ticket-breakdown.md)
- **Flows**: [FLOW-07](../../../../../product/context/flows/07-domain-event-catalogue.md) (events and recipients), [FLOW-05](../../../../../product/context/flows/05-adverse-action-cascade.md) (cascade), [FLOW-06](../../../../../product/context/flows/06-state-machines.md) (statuses the demo seed covers), [FLOW-01](../../../../../product/context/flows/01-end-to-end-privilege-issuance.md) (document step)
- **Compact rules**: Rule 4 §4.3(e) (every change retained), Rule 4 §4.4–§4.5 (reports, confidentiality), Rule 3 §3.9 (eligibility withdrawal), Rule 5 §5.4 (one business day for emergency reports)
- **Decisions**: D2 (outbox), D3 (guardrails), D7 (email from rows), D8 (Worker and jobs), D9 (documents), D13 (local stack)
- **Jira**: SCRUM-78, SCRUM-79, SCRUM-80, SCRUM-81 (epic SCRUM-68)
- **ADRs**: [ADR-0005](../../../../adrs/0005-data-model-conventions.md), [ADR-0006](../../../../adrs/0006-reference-time-zone-and-dates.md), [ADR-0009](../../../../adrs/0009-route-authorization-and-change-context.md); new ADR-0011 to ADR-0015 below
- **Area**: api, client, infrastructure

## Constitution Check

- **I.** New dependencies each get an ADR with pros and cons per option and a row in the API or client README table: `boto3`, `jinja2`, `aiosmtplib`, `openapi-typescript`, `openapi-fetch`; Prism runs as a pinned Docker image. Raw SQL appears only for `FOR UPDATE SKIP LOCKED` claims, with a comment.
- **II.** Document downloads are scoped in the query: out-of-scope documents are `404`. Persona namespaces are checked by a test, and permissions stay the only check.
- **III.** Every module at 100% line and branch coverage against real Postgres, RustFS, and maildev. The dispatcher, sender, and scan job are tested by calling them, never by a background loop.
- **IV.** The Worker, cron, and malware scanner run as Docker Compose services on the same code path as AWS. The malware scanner is local tooling under `engineering/mocks/`. The demo seed lives in `engineering/api/seed/`, which `.dockerignore` already excludes.
- **VI.** `deactivate_privileges` writes rows, history, and events in the caller's transaction. Handlers only queue email. A test fails any route test that writes a history row without an event.
- **VII.** Download links last five minutes; upload links one. The bucket is private, encrypted, versioned. SMTP credentials come from Secrets Manager.
- **VIII.** Dispatch, send, job, and scan outcomes are structured log lines. CloudWatch metric filters on those lines drive alarms to the existing Slack topic, with one alarm for zero running Worker tasks.
- **IX.** Handlers cite FLOW-07 once in their module; document scoping cites Rule 4 §4.5.
- **XII.** Every new setting is in `.env.example`; README covers `just job`, `just seed demo`, `just generate`, and the new Compose services.
- **XIII.** `licensing_api/days.py` is the single place for day and business-day arithmetic.
- **XIV.** Additive migrations only: new columns are nullable or defaulted; new tables are empty.
- **XV.** Each PR below is sized under 600 production lines. Generated code (OpenAPI document, TypeScript client) is named with its command.

## Current State Analysis

- Producer side exists: `emit`, `history.write`, `audit_log.write`, `notify`, `handler`, `HandlerRegistry`, `system_context` (`licensing_api/repo/`, `events.py`, `context.py`). Nothing consumes `domain_events` or sends `notifications`.
- `domain_event_deliveries` has `attempts`, `last_error`, `handled_at`, `dead_lettered_at`, and no backoff column. No row exists until something creates it.
- `notifications` has `status`, `attempts`, `last_error`, `sent_at`, and no backoff column.
- `documents` exists (`repo/document.py`) with `scan_status` and a polymorphic owner, but no history table and no code.
- Routes: `/api/health/*` (public) and `/api/me` (bare `CurrentUser`). `Data`, `Paged`, `page_query`, `paginate` are unused by any route.
- No OpenAPI export, no client generation, no MSW; the client reads `/api/me` with a hand-written type (`client/src/app/page.tsx:9`).
- Local stack: Postgres, maildev, RustFS (bucket created, no versioning or CORS), cognito-local. No Worker. RustFS honours POST-policy `content-length-range` and `Content-Type`, object tags, versioning, and presigned GET (checked by hand on 2026-10-21).
- Terraform has one ECS service, one alarm (API error rate → SNS → Slack), no SES, no scheduler, no documents bucket.
- `compact_today()` exists in SQL only; there is no Python day module.

## Desired End State

- A route test that changes a record without emitting an event fails.
- `dispatch_events` delivers each event once per handler, retries with backoff, dead-letters after five attempts, and two Workers never handle the same delivery.
- `just up` shows an email in maildev seconds after a change; `just job heartbeat` runs a job; `just seed demo` fills an empty database with every application and privilege status.
- `just generate` regenerates the OpenAPI document and the TypeScript types; `just mock-api` serves the document's examples with Prism; CI fails on drift; Storybook renders the dashboard with no API.
- A PA uploads a 20 MB PDF; 21 MB is refused by the bucket; EICAR is tagged infected locally and can never be downloaded; state A gets `404` for state B's document.

### Key Discoveries

- Fan-out needs no per-event column if delivery rows are created when an event is first claimed; a `dispatched_at` column on `domain_events` keeps that query on a small partial index instead of scanning the outbox.
- Running a handler inside a savepoint lets the dispatcher keep its row lock, roll back only the handler's writes on failure, and commit the handler's work with `handled_at` atomically.
- `.dockerignore` already excludes `seed/` and `tests/`, so a Python demo seed never reaches the image.
- The client must keep reading `/api/me` while the API and client deploy separately, so `/me` moves to `Data` in the same PR that switches the client to the generated client.

## What We're NOT Doing

- GuardDuty Malware Protection and the `test` environment (epic 3). The documents bucket Terraform leaves the protection plan to epic 3, and the PR says so.
- Applying Terraform. Each infrastructure change is validated only.
- Domain metrics (`time_to_decision`, `time_to_issue`, reporting timeliness): a follow-up ticket.
- SSN rows in the demo seed: the encryption helper is U-03's (ADR-0007).
- Feature routes beyond `/commission/audit` and the document routes; each epic owns its own.
- Wiring `FilePickerField` into a feature page: none exists yet. It is wired to the upload API and shown in Storybook.
- The holiday calendar's sign-off. ADR-0011 proposes federal holidays for the Commission to confirm.
- Correcting FLOW-06. It names `abandoned` where the code has `withdrawn`, omits `superseded`, and lists five of the seven deactivation reasons. The demo seed test covers the code's enums; a product ticket fixes the flow.

## Implementation Approach

Branches follow `feature/SCRUM-<n>-<slug>`; each PR targets the branch below it.

| # | Branch | PR |
|---|---|---|
| 1 | `feature/SCRUM-78-days` | Day arithmetic and the event-required test guard |
| 2 | `feature/SCRUM-78-dispatcher` | `dispatch_events`, retry, dead-letter (ADR-0012) |
| 3 | `feature/SCRUM-78-cascade` | `deactivate_privileges`, `GET /commission/audit` |
| 4 | `feature/SCRUM-79-namespaces` | Persona namespaces, the envelope test, `SYSTEM_ADMIN` |
| 5 | `feature/SCRUM-79-openapi` | OpenAPI export, drift check, generated types, Prism mock (ADR-0013) |
| 6 | `feature/SCRUM-79-client` | Generated client in the app, `/me` moves to `Data`, Storybook on Prism |
| 7 | `feature/SCRUM-79-demo-seed` | `just seed demo` |
| 8 | `feature/SCRUM-80-worker` | Worker process, jobs, `just job`, Compose services |
| 9 | `feature/SCRUM-80-email` | `send_pending`, templates, `state_contacts` (ADR-0014) |
| 10 | `feature/SCRUM-80-handlers` | FLOW-07 email handlers, the event catalogue test, `docs/notifications.md` |
| 11 | `feature/SCRUM-80-terraform` | Worker service, scheduler, alarms, SES |
| 12 | `feature/SCRUM-81-documents` | Document upload, scan, download (ADR-0015) |
| 13 | `feature/SCRUM-81-file-picker` | `FilePickerField` uploads; documents bucket Terraform |

---

## Phase 1: Day arithmetic and the event-required guard (SCRUM-78)

### Changes Required

- **`licensing_api/days.py`** (new): `compact_date_at(instant, time_zone)`, `compact_today(session)` (reads `compact_settings.time_zone`), `add_days`, `days_between`, `add_business_days`, `is_business_day`. Business days skip weekends and US federal holidays as observed (computed, no dependency).
- **ADR-0011** (new): business days and the holiday calendar, succeeding ADR-0006 point 5; status proposed until the Commission confirms.
- **`tests/conftest.py`**: `route_db_session` registers an `after_flush` listener that fails the test when a transaction inserts a history row but no `domain_events` row.
- Tests: boundaries per Principle XIII (last day, day after, weekend and holiday spans, daylight-saving change).

### Success Criteria

- `just lint`, `just test-coverage` at 100% on `days.py`.

## Phase 2: The dispatcher (SCRUM-78)

### Changes Required

- **Migration** `20261021_090000_event_dispatch.sql`: `domain_events.dispatched_at TIMESTAMPTZ` with a partial index `WHERE dispatched_at IS NULL`; `domain_event_deliveries.next_attempt_at TIMESTAMPTZ`; the pending index includes it.
- **`licensing_api/worker.py`** (new): `dispatch_events(session_factory, registry, *, batch_size=100) -> int`.
  1. Fan out: claim undispatched events (`FOR UPDATE SKIP LOCKED`), insert a delivery row per registered handler (`ON CONFLICT DO NOTHING`), stamp `dispatched_at`, commit.
  2. Deliver, one transaction each: claim one due delivery (`SKIP LOCKED`), run the handler in a savepoint with `system_context(request_id=event.request_id)`, set `handled_at`; on an exception roll back the savepoint, add an attempt, store the error, set `next_attempt_at` by exponential backoff, dead-letter at five attempts. An unknown handler name dead-letters at once.
  3. Log `event_handled`, `event_handler_failed`, `event_dead_lettered` with `event_id`, `handler`, `attempts`.
- **ADR-0012** (new): build the dispatcher on the existing tables rather than adopt pgqueuer; pros and cons of each.
- Tests: replay is a no-op; a failing handler retries then dead-letters; two concurrent `dispatch_events` calls handle each delivery once; a handler's writes roll back with its failure; 1,000 events drain in under a minute.

## Phase 3: The privilege cascade and the audit route (SCRUM-78)

### Changes Required

- **`licensing_api/repo/privilege.py`**: `deactivate_privileges(...)` with the contract's signature. Locks the active privileges (`FOR UPDATE`), sets status, reason, time, note, writes history (`effective_at`), emits `privilege.deactivated` per privilege.
- **`licensing_api/routes/audit.py`** (new): `GET /commission/audit` → `Paged[AuditEntryOut]`, `require(Permission.COMPACT_ADMIN)`, filters `action`, `entity_type`, `entity_id`, `actor` (public ID), `occurred_from`, `occurred_to`; sorted by `occurred_at`.
- Docs: `platform-contract.md` marks the `.3` signatures implemented.

## Phase 4: Persona namespaces and the envelope rule (SCRUM-79)

### Changes Required

- **`licensing_api/routes/__init__.py`** (new): `NAMESPACES` maps each persona prefix (`/me`, `/public`, `/states/{state_code}`, `/commission`, `/admin`) to the resource routers under it; `api` mounts them under `/api`, tagged with the prefix's first segment. `/health` stays outside the namespaces. A resource router carries only its resource prefix (`user.router` none, `audit.router` `/audit`), so `/api/me` and `/api/commission/audit` keep their URLs. `__main__.py` mounts `api`.
- **`licensing_api/permissions.py`**: `Permission.SYSTEM_ADMIN`, held only by the `admin` role, for `/admin`.
- **`licensing_api/errors.py`, `request_logger.py`**: `ErrorCode.INTERNAL_ERROR`; the unhandled-exception middleware (`request_logger.py:62`) returns `ErrorResponse` instead of `{"detail": ...}`, so every error has one shape.
- **`tests/test_route_access.py`**: a `_violations(app)` helper applies each namespace's rule using `NAMESPACES` and `route_access(route)`; it runs against the real app and against a throwaway app with one bad route per rule (as `test_permissions.py:101` does), so each rule is shown to fail while its namespace is still empty.
  - Every `/api` route outside `/api/health` starts with a namespace prefix.
  - `/public` routes are `public()`; routes in every other namespace are signed in.
  - `/states/{state_code}` routes declare `state_param='state_code'`.
  - `/commission` routes need `COMPACT_ADMIN`. `READ_PRIVATE` is not enough: with no state in the path it is checked against the caller's own state (`permissions.py:98-116`), so a state staff member's own-state grant would pass.
  - `/admin` routes need `SYSTEM_ADMIN`.
- **`tests/test_responses.py`**: every `/api` route outside `/api/health` has `route.response_model` of `None` or a subclass of `Data` or `Paged`; `/api/me` is the one listed exception until phase 6. A throwaway route returning a bare model fails the check. An unhandled exception returns `{"code", "details"}`.
- Docs:
  - `roles-and-permissions.md`: `system_admin` in the `admin` row of Roles (:26) and in Permissions (:32-40), which `test_permissions.py` requires to match the code; a Namespaces section listing each prefix's rule.
  - `platform-contract.md`: `system_admin` in the `Permission` row (:75); the namespaces under "Declaring a route" (:54).
  - ADR-0009 (proposed): `admin` holds `system_admin` (:29).

### Success Criteria

#### Automated Verification

- [ ] `just lint` and `just test-coverage` pass, with 100% on `routes/__init__.py`, `permissions.py`, and `request_logger.py`.
- [ ] Each namespace rule fails its throwaway bad route in `test_route_access.py`.

#### Manual Verification

- [ ] With `just dev`, `GET /api/me` and `GET /api/commission/audit` answer as before.

## Phase 5: OpenAPI and the generated client (SCRUM-79)

### Changes Required

- **`engineering/api/scripts/export_openapi.py`** (new) and `just openapi`: imports `app` and writes `engineering/api/openapi.json` as `json.dumps(document(), indent=2, sort_keys=True)` plus a newline, where `document()` is `app.openapi()` with each example's missing required fields set to `null` (FastAPI drops `None` from examples). Importing the app needs no database: every setting has a default (`config.py:6-25`) and the engine is created in `lifespan`.
- **Response examples**: every model a route returns (`CurrentUser`, `AuditEntryOut`, `LiveResp`, `ReadyResp`) sets `json_schema_extra={'examples': [...]}`. So does `Page`. `Data[T]` and `Paged[T]` carry none; Prism builds them from what they hold.
- **`routes/__init__.py`**: the `api` router documents `422` as `ErrorResponse`, the body the API sends, replacing FastAPI's `HTTPValidationError`.
- **`tests/test_openapi.py`**: every model a success response returns, looking inside `Data` and `Paged`, has an example; an example is `null` only in a nullable field; every `422` is `ErrorResponse`; the committed `openapi.json` equals a fresh export, so drift fails `just test` locally and in `api.yml`'s existing test job.
- **`engineering/client`**:
  - `openapi-typescript` (dev); `openapi-fetch` comes with its first caller in phase 6. No mocking code or dependency.
  - `pnpm generate`: `openapi-typescript ../api/openapi.json -o src/api/schema.d.ts`, then Prettier.
  - The generated types open with a header from `openapi-typescript` and are excluded from eslint.
- **Root `justfile`**: `just generate` runs `just openapi`, then `pnpm generate`. `just mock-api` runs `stoplight/prism:5.15.10` on port 4010 against the committed document (`--platform linux/amd64`, since the image is amd64-only; `-m false`, since its multi-process start fails).
- **`client.yml`**: the PR path filter adds `engineering/api/openapi.json`; the lint job runs `pnpm generate` and fails on `git diff --exit-code src/api`. It needs no Python, since it reads the committed document.
- **ADR-0013** (new): `openapi-typescript` + `openapi-fetch` + Prism, against generated MSW handlers, orval, hey-api, and `msw-auto-mock`; pros and cons.
- **`engineering/client/README.md`**: a dependency table in the API README's format (Package, Purpose, Docs), with the new packages and Prism.

### Success Criteria

#### Automated Verification

- [ ] `just lint`, `just test-coverage`; `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm test:coverage`.
- [ ] `just generate` run twice leaves `git status` clean.
- [ ] Adding a field to `CurrentUser` without regenerating fails `test_openapi.py`.

#### Manual Verification

- [ ] `just mock-api` answers `/api/me` and `/api/commission/audit` with the examples, every required field present, and answers `401` with no bearer token.

## Phase 6: The app on the generated client (SCRUM-79)

### Changes Required

- **`client/src/lib/api.ts`**: `api`, an `openapi-fetch` client on `paths` with `baseUrl` from `NEXT_PUBLIC_API_BASE_URL`, looking up `fetch` per call so a test's stub applies; its `onRequest` middleware adds the ID token from `getCurrentSession()` and throws `Not authenticated` without one, as `authFetch` does. `authFetch` stays for non-JSON calls.
- **`routes/user.py`**: `get_me` returns `Data[CurrentUser]`; regenerate. The envelope test's `/me` exception is removed.
- **`client/src/app/page.tsx`**: drops the hand-written `CurrentUser` (:9-17) for `components['schemas']['CurrentUser']` and reads `data.data` from `api.GET('/api/me')`.
- **Client tests**: `src/tests/setup.ts` stubs `fetch` to reject before each test, so an unanswered request fails, and `src/tests/fetch.ts`'s `answerFetch(body, status)` answers one. `page.test.tsx` answers `/api/me` that way in place of mocking `authFetch`; `api.test.ts` covers the middleware by reading the stubbed calls.
- **Storybook**:
  - `main.ts`: `env` sets `NEXT_PUBLIC_API_BASE_URL` to the Prism mock (`http://localhost:4010`, `just mock-api`), or `STORYBOOK_API_BASE_URL`; `staticDirs` serves the app's `public/` for the USWDS fonts.
  - `webpack` pinned below 5.101 (dev): later versions' `DefinePlugin` taps a parser hook Next 14's bundled webpack lacks, which broke `build-storybook` on `main`. CI builds Storybook.
  - `main.ts`: a small plugin swaps the resolved `src/lib/auth.ts` for `.storybook/mocks/auth.ts`, whose `getCurrentSession()` returns a fixed session; an alias never applies, because the tsconfig paths resolver handles `src/...` first. `AuthProvider`, which `preview.tsx` wraps every story in, and the client middleware both import it, so no production code changes.
  - `home.stories.tsx`: the dashboard with the API's example user from Prism. The error state is covered by `page.test.tsx`, since Prism answers only documented responses.
- **Deploy order**: the API and client deploy to DEV separately on merge, so the dashboard shows an error between the two deploys. Acceptable in DEV; the PR says so.

### Success Criteria

#### Automated Verification

- [ ] `just lint`, `just test-coverage`; `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm test:coverage`.
- [ ] `pnpm build-storybook` succeeds.

#### Manual Verification

- [ ] `just mock-api` and `pnpm storybook` render the dashboard with the example user.
- [ ] `just up`: the dashboard shows the signed-in user.

## Phase 7: The demo seed (SCRUM-79)

### Changes Required

- **`engineering/api/seed/demo.py`**: `async def seed(session) -> list[Expected]`, deterministic, dates relative to `days.compact_today(session)`. It flushes and leaves the commit to its caller; run as a script, it opens a session from `settings`, seeds, commits, and prints a summary.
  - Refuses to run when any practitioner exists. A migrated database already holds the system user, the 56 states, and the reference rows; "empty" means no domain data.
  - Writes as `system_context(session)`. The repo has no create functions and `tests/factories.py` writes no history, so a local helper adds each row and calls `history.write(..., before=None)`. It never calls `emit`, so no email goes out.
  - States: KS, OK, MO, CO set `is_member`, `member_effective_on`, `is_live`, with history. Fees: the Commission participation fee and each live state's privilege fee.
  - Users: one `licensee` per practitioner; KS `state_staff` with `{"KS": ["read_private", "write"]}`, KS `state_admin`, OK `state_staff`.
  - Coverage, from the code's enums rather than FLOW-06 (see What We're NOT Doing):
    - one application per `ApplicationStatus` (8), with the fields each status's check constraint requires; the `superseded` practitioner also holds the `eligible` change-of-SQL application;
    - one privilege request per `PrivilegeRequestStatus` (5);
    - one privilege per `PrivilegeComputedStatus` (4), the encumbered one through an adverse action on the privilege;
    - one qualifying license per `LicenseComputedStatus` (6);
    - eligibility: not barred, barred open-ended, barred until a date (action ended within two years), bar ended (ended earlier);
    - an open and a closed SII report.
  - An in-force license adverse action leaves that practitioner's privileges `inactive` with `qualifying_license_adverse_action`, set directly, because `deactivate_privileges` emits events.
  - If the module passes 600 lines, the scenarios split into `seed/demo_*.py` modules.
- **`just seed`** (`engineering/api/justfile:26-28`): runs `uv run --env-file .env python seed/<name>.py` when it exists, else pipes `seed/<name>.sql` into `psql` as today. `just up` keeps seeding `users`.
- **`engineering/mocks/cognito/db/local_licensing.json`**: entries for the demo staff and two PAs, password `Local-Passw0rd!`.
- **`tests/test_demo_seed.py`**: runs `seed` in `db_session` (rolled back). Each `Expected` matches its row in `v_privilege_status`, `v_qualifying_license_status`, `v_compact_eligibility`, or the stored application and request status; each enum above and the four eligibility cases are covered in full; a second run raises.
- **`docs/demo.md`**: which login shows which scenario, and the sprint-review script.

### Success Criteria

#### Automated Verification

- [ ] `just lint`, `just test-coverage`; `test_demo_seed.py` passes.

#### Manual Verification

- [ ] `just infra`, `just migrate`, `just seed demo`; signing in as KS staff and as a demo PA shows the statuses `docs/demo.md` lists.

## Phase 8: The Worker and jobs (SCRUM-80)

### Changes Required

- **`licensing_api/logging_config.py`**: the JSON logging setup moves out of `__main__.py` so the Worker shares it.
- **`licensing_api/worker.py`**: `python -m licensing_api.worker` loops `dispatch_events` (and `send_pending` from phase 9), sleeps when idle, stops on SIGTERM.
- **`licensing_api/jobs/`**: `Job(name, run)`, `JOBS`, `python -m licensing_api.jobs run <name>`; `heartbeat` and `dispatch_events`. Migration: `job_runs` (job, started_at, finished_at, outcome, error).
- **Compose**: `worker` and `cron` services under the `app` profile (same image, dev target); `cron` runs supercronic with `engineering/api/jobs.crontab`. `just up` starts them after migrating. `just job <name>`.
- Tests: the job runner records success and failure; a test fails when a job is missing from the crontab or the Terraform schedule list.

## Phase 9: Sending email (SCRUM-80)

### Changes Required

- **Settings**: `smtp_*`, `email_from_address`, `client_base_url`, `commission_ops_email` (Q-14 placeholder value in `.env.example`).
- **Migration**: `notifications.next_attempt_at`; `state_contacts` (state_code, purpose `applications` | `privileges` | `discipline`, email; unique per state, purpose, email) with history.
- **`licensing_api/notifications/`**: `render(template, context, environment)` with Jinja (autoescape, `StrictUndefined`), a base layout with the environment banner outside PROD, HTML and text from one template; `sender.send_pending(...)` per the contract, retrying with backoff and marking `failed` after five attempts.
- **ADR-0014** (new): `jinja2` and `aiosmtplib`, against the standard library (`string.Template`, `smtplib` in a thread); pros and cons.
- Tests: snapshot tests for every template (`tests/snapshots/`, updated with `UPDATE_SNAPSHOTS=1`); sending through maildev's API; a repeated key sends once; two senders never send the same row.

## Phase 10: The FLOW-07 handlers (SCRUM-80)

### Changes Required

- **`licensing_api/notifications/handlers.py`**: one handler per FLOW-07 row that emails, `notifications.<what>`; recipients from the PA's on-file email, `state_contacts`, and `commission_ops_email`; idempotency key `<event_id>:<handler>:<recipient>`. SII handlers never address the PA (ML §8.C); `application.info_requested` sends a link, never the note.
- **`licensing_api/handlers.py`**: `HANDLERS`, the tuple the Worker registers.
- **`tests/test_event_catalogue.py`**: every `EventType` is referenced by at least one test outside the catalogue test.
- **`docs/notifications.md`**: event → recipients → template.

## Phase 11: Infrastructure for the Worker and email (SCRUM-80)

### Changes Required

- `ecs.tf`: Worker task definition and service (same image, `command` override, no load balancer); a run-task definition for jobs.
- `scheduler.tf` (new): EventBridge Scheduler role and one schedule per job.
- `alerting.tf`: running Worker tasks below one; metric filters and alarms for `event_dead_lettered`, `job_failed`, `notification_failed`.
- `ses.tf` (new): domain identity, DKIM, custom MAIL FROM with SPF, DMARC record, SMTP credentials in Secrets Manager.
- `.github/workflows/api.yml`: the deploy also renders and deploys the Worker task definition.
- Verified by `terraform fmt -check` and `terraform validate`.

## Phase 12: Documents (SCRUM-81)

### Changes Required

- **Migration**: `documents_history`; `documents.scanned_at`.
- **Settings**: `s3_endpoint_url`, `s3_region`, `s3_documents_bucket`, `s3_access_key_id`, `s3_secret_access_key` (unset in AWS).
- **`licensing_api/documents.py`**: limits (20 MiB; PDF, PNG, JPEG), `presign_upload` (POST policy with `content-length-range` and an exact `Content-Type`), `presign_download` (five minutes), `refresh_scan_status` (reads `GuardDutyMalwareScanStatus`).
- **Routes**: `POST /me/documents` and `POST /states/{state_code}/documents` create a `pending` row and return the upload form; `GET .../documents/{id}/download` under `/me`, `/states/{state_code}`, `/commission` return a link only for `clean` documents in scope (`409` while pending, `404` out of scope) and audit staff downloads.
- **`repo/document.py`**: `attach(session, ctx, document, owner)` for owners created later, with history.
- **Job**: `refresh_document_scans`, every minute.
- **`engineering/mocks/malware-scanner/`**: ClamAV with a small script that tags new objects as GuardDuty does; Compose service; `rustfs-init` turns on versioning and CORS for the client origin.
- **ADR-0015** (new): `boto3`, against `aioboto3` and hand-rolled SigV4; pros and cons.
- Tests: 20 MiB accepted and 20 MiB + 1 refused by the bucket; EICAR tagged `THREATS_FOUND` → `infected` → never downloadable; scope across states and the PA; audit row on staff download.

## Phase 13: The file picker and the bucket (SCRUM-81)

### Changes Required

- **`client/src/components/FilePickerField.tsx`**: checks size and type, requests the upload form, posts the file, stores the document ID; errors through i18next; story against the Prism mock.
- **Terraform** `documents.tf`: private bucket, versioning, SSE-KMS with a customer key, CORS for the client origin, TLS-only policy; task role `s3:PutObject`, `s3:GetObject`, `s3:GetObjectTagging` on it; settings into the task definitions.

---

## Testing Strategy

- API tests run against the Compose services; the dispatcher, sender, scan job, and job runner are called directly.
- Concurrency tests run two dispatchers or senders with `asyncio.gather` on separate sessions.
- Snapshot tests fix email output; day arithmetic takes explicit dates, so no clock is frozen.
- Client tests use vitest, answering `fetch` with `answerFetch`.

## Security Impact Assessment

- **Documents** (private tier, follows the owner): bytes go browser → bucket directly; the API only signs. Uploads are capped and typed by the bucket policy, downloads need `clean`, scope, and a five-minute link; staff downloads are audited. Failure: a document readable across states; covered by scope tests in each namespace.
- **Email**: templates carry links and status, never notes, SSNs, or SII to the PA; the address is copied at queue time. Failure: SII mailed to a PA; covered by recipient tests.
- **Audit route**: Commission-only; returns actor emails and entity references, no record contents.
- **Demo seed**: synthetic data only, never in the image; no SSNs.

## References

- Contract plan: [`2026-10-14-SCRUM-77-platform-contract.md`](2026-10-14-SCRUM-77-platform-contract.md)
- Platform contract: [`engineering/docs/platform-contract.md`](../../../../docs/platform-contract.md)
