# Engineering Constitution

This document is the engineering DNA of the PA Compact Data System.
Every technical plan, ADR, and pull request is evaluated against it.
Where a principle allows exceptions, they require an ADR in
[`engineering/adrs/`](adrs/); otherwise, conflicts
require amending this document.

## Core Principles

### I. Idiomatic Python and FastAPI

Keep the API coherent: Python, FastAPI, Pydantic, and SQLAlchemy
knowledge alone should be sufficient to read, modify, and debug any part
of it.

Use what the stack already provides before reaching for libraries:
FastAPI dependencies for request context (database session, auth
claims, settings), Pydantic models for every request and response body,
SQLModel/SQLAlchemy async sessions for queries, `pydantic-settings` for
configuration. All I/O is `async`; concurrent independent calls use
`asyncio.gather`.

Queries go through the ORM. Schema changes are plain SQL migrations in
[`engineering/api/db-migrations/`](api/db-migrations/), applied by `yoyo` at startup
([Principle XIV](#xiv-migrations-are-safe-to-deploy)). Raw SQL
in application code requires a comment saying why the ORM doesn't fit.

The API has one file per resource in each layer:

- [`routes/`](api/licensing_api/routes/) holds the HTTP handlers and their request and response
  Pydantic models. Every endpoint that returns a body returns a
  Pydantic model, and every route decorator sets `name` and
  `description`, so the OpenAPI document is complete.
- [`repo/`](api/licensing_api/repo/) holds async query functions. They accept plain values and
  return model instances; they don't take request objects or raise HTTP
  errors.
- Errors are raised as `AppError` with an `ErrorCode`
  ([`errors.py`](api/licensing_api/errors.py)), and every error
  response has the shape `{"code": ..., "details": [...]}`. No route
  builds its own error body.

Use built-in generic types (`list`, `dict`) and `X | None`, never
`typing.List` or `Optional[X]`. Use the Pydantic v2 API
(`model_dump()`, not `.dict()`).

Code hygiene, in both the API and the client:

- **Errors are handled, never swallowed.** Catch the specific exception
  you expect, never a bare `except:`. A caught exception is handled,
  converted to an `AppError`, or logged and re-raised; it is never
  silently dropped.
- **No mutable module-level state.** Module-level constants and the
  settings object are fine; anything that changes at runtime lives in
  app state or a dependency.
- **No wildcard imports.**
- **No debug output.** No `print`, `console.log`, or commented-out code
  is merged; diagnostics go through the logger.
- **Type-checker suppressions say why.** Every `# type: ignore`,
  `# pyright: ignore`, or `@ts-expect-error` carries a comment giving
  the reason.
- **Names follow the language.** PEP 8 in Python (`snake_case`
  modules, functions, and variables; `PascalCase` classes;
  `SCREAMING_SNAKE_CASE` constants; `test_*.py` test files), and the
  ESLint configuration in TypeScript.

New dependencies, alternate frameworks/ORMs/auth libraries, or wrappers
around FastAPI or SQLAlchemy primitives require an ADR explaining why
what's already in the stack doesn't fit. A new dependency is also added
to the ["Key frameworks and dependencies"](api/README.md#key-frameworks-and-dependencies)
table in [`engineering/api/README.md`](api/README.md) with a link to its documentation.

### II. The API is the only authority

The Next.js client renders and collects; the API decides. Every
eligibility guard, state transition, fee calculation, and authorization
check runs in the API, and the client's checks are convenience only.
Fees, expiration dates, and statuses shown to a user are the values the
API computed, never values the client derived.

Authorization is checked on every route, server-side, from the caller's
Cognito-verified claims and their database role. State staff access is
scoped by the state's relationship to the PA: the state of qualifying
license for an application, the remote state for a privilege request
or privilege. A domain record (a practitioner, application, privilege
request, privilege, adverse action, or document) outside the caller's
scope returns `404`, not `403`, so its existence is not disclosed.
Failures about the caller themselves, such as an unknown or inactive
user, keep their `401`/`403` codes.

### III. Test coverage

100% line and branch coverage on
[`engineering/api/licensing_api/`](api/licensing_api/) and
[`engineering/client/src/`](client/src/), measured by
`coverage run --branch` and `vitest --coverage` in CI
([`api.yml`](../.github/workflows/api.yml),
[`client.yml`](../.github/workflows/client.yml)). The
[RFP](../product/context/research-corpus/sources/pa-compact-commission-data-system-rfp.md)'s QASP floor of 90% is the
contractual minimum, not the target.

API tests run against real Postgres and Redis (Docker Compose locally
and in CI), not mocks. External services are mocked at their boundary:
Cognito, Authorize.net, SES. Prefer tests that exercise an endpoint
end to end through the API over unit tests of its internals. Shared
fixtures live in [`conftest.py`](api/tests/conftest.py).

A failing test is fixed, not deleted, skipped, or loosened, unless the
test itself is wrong; the PR says why.

`# pragma: no cover` and `/* v8 ignore */` require justification in
the PR description.

### IV. No mock code in production

This principle governs the application as it runs — locally, in CI,
and deployed. Tests may still mock at a client boundary inside test
code ([Principle III](#iii-test-coverage)).

Production code contains only production behavior. Mocks, stubs, fakes,
fixtures, seed data, and test-only helpers live in test code
([`engineering/api/tests/`](api/tests/), `*.test.tsx`,
[`engineering/client/src/tests/`](client/src/tests/)), Storybook stories,
or local tooling outside the application, never in
[`engineering/api/licensing_api/`](api/licensing_api/) or in code the
client ships.

- **No fake switches.** No code path that swaps in fake behavior based
  on an environment variable, the `environment` setting
  ([`config.py`](api/licensing_api/config.py)), or a feature
  flag. The code that runs locally is the code that runs in production.
- **Fakes run outside the process.** When the app runs locally or in
  CI, an external service is replaced by a mock server in
  [Docker Compose](api/docker-compose.yaml) (as maildev
  replaces SES). The application reaches it through the same client
  and code path it uses in production; only configuration such as the
  endpoint URL differs.
- **Test data never ships.** Seed data and fixtures are loaded by test
  or local tooling and are excluded from the production image.
- **No placeholders.** Hardcoded sample responses, stubbed-out
  implementations, and "replace with the real thing later" code are not
  merged.

Exceptions require an ADR.

### V. E2E and accessibility testing

Every user flow in [`product/context/flows/`](../product/context/flows/) ships with Playwright tests
covering it end to end across pages and personas (PA, SQL staff,
remote-state staff, Commission) — golden path and at least one error
path. Every page those tests visit is checked for WCAG 2.1 AA with an
automated accessibility scan; a violation fails the build.

`test.describe`, `test`, and `test.step` titles must be readable by a
non-technical reviewer; the product manager reviews E2E coverage as
part of story acceptance.

Exempt: Storybook.

### VI. The record is the audit trail

The compact rules make the data system the system of record
([Rule 4 §4.3(e)](../product/context/research-corpus/sources/rule-4-compact-data-system--confidentiality-information-sharing.md)): every change is retained. The architecture follows from that.

- **One transaction per write.** A write validates, then writes the
  rows, a history row, an audit row, and a `domain_events` row in one
  transaction, then returns. Nothing sends email, calls another
  service, or cascades to other records inside a request.
- **Side effects run in the Worker.** The Worker drains `domain_events`
  and fans out to handlers. Handlers are idempotent on
  `(event_id, handler)`; replaying an event is a no-op. Every event
  type is listed in
  [`product/context/flows/07-domain-event-catalogue.md`](../product/context/flows/07-domain-event-catalogue.md)
  and has at least one test.
- **Provenance on every field.** Each uniform data set field records
  who entered it, who verified it, and when.
- **Status that a rule derives is computed, not stored.** Privilege
  status is computed on read from administrator status, expiration,
  and adverse actions; jobs write history, not status.
- **No hard deletes** of practitioner, application, privilege,
  adverse-action, or transaction data.
- **Audit columns come from the token.** `created_by` and `updated_by`
  are set from `AuthClaims.sub` with a sub-query in the same statement,
  not by looking up the user's `id` first
  ([ADR-0004](adrs/0004-jwt-auth-claims-as-user-identity.md)).

Deviations require an ADR.

### VII. Zero trust

**Secrets management.** No secrets in the repo, no secrets in `.env`
files in deployed environments. All secrets via AWS Secrets Manager /
Parameter Store, injected at runtime. `gitleaks` runs on every commit
([`.pre-commit-config.yaml`](../.pre-commit-config.yaml)).

**Least privilege.** Application roles, per-state staff permissions,
and AWS IAM roles are opt-in. Every role/permission grants the minimum
needed. No superuser shortcuts in application code; Commission users
pass state checks only where a route says so.

**Input validation.** Every boundary validates: request bodies, path
and query params, file uploads, webhooks, external service responses.
Pydantic models are the gate and reject unknown fields. Webhooks verify
their signature over the raw body before parsing or acting on it. "It came from a trusted
source" is not a justification to skip.

**Encryption.** TLS on every connection, including the hops inside the
VPC: CloudFront to the load balancer, the load balancer to the API, and
the API to Postgres and Redis. A hop without TLS requires an ADR. RDS,
ElastiCache, and S3 are encrypted at rest. SSNs are additionally
encrypted at the column level.

### VIII. Maximum observability

Every feature ships with structured logs and metrics that make its
behavior visible in production. Logs are JSON with sensitive keys
masked ([ADR-0001](adrs/0001-structured-json-logging.md)) and include a request ID for correlation; external
calls log duration and outcome. Traces go through OpenTelemetry to the
ADOT collector.

When new signals are added, the monitoring system is updated to surface
them — dashboards, CloudWatch alarms routed to the team's Slack
channel, or both. Domain metrics the Commission reports on
(time to decision, time to issue, adverse-action reporting timeliness)
are emitted as metrics, not reconstructed from logs.

### IX. Plans link to specs, code links to rules

Every technical plan in
[`engineering/thoughts/shared/plans/`](thoughts/shared/plans/) links to
the story or spec in [`product/`](../product/) it implements and to the
flows in [`product/context/flows/`](../product/context/flows/) it touches. ADRs generated from a plan carry
the same link forward.

Behavior a compact rule forces cites the rule once, at the point it is
encoded, using the keys in
[`product/context/reference/glossary.md`](../product/context/reference/glossary.md#rule-citation-keys-used-in-the-backlog)
(e.g. [`ML §4.B`](../product/context/research-corpus/sources/pa-compact-model-legislation.md), [`Rule 3 §3.4(d)`](../product/context/research-corpus/sources/rule-3-compact-privilege.md)). Adopted rule text governs over
draft text.

This traceability lets validation skills walk from any AI-generated
artifact back to the originating spec and rule.

### X. Leverage USWDS exclusively

UI is built from [USWDS](https://designsystem.digital.gov/) components
([`@trussworks/react-uswds`](https://trussworks.github.io/react-uswds/),
[`@uswds/uswds`](https://designsystem.digital.gov/components/overview/)).
Composing them into page-level components is fine, and overriding
USWDS tokens for branding is fine. Every user-facing string goes
through `i18next` ([`client/src/i18n/`](client/src/i18n/)).

Bespoke components or third-party UI libraries (form widgets, date
pickers, etc.) require an ADR. Every component has a Storybook story.

### XI. Prose earns its keep

Comments, docstrings, and prose documents carry only what the artifact
itself cannot say: why, constraints, invariants, gotchas, regression
records. Text that restates names, signatures, or visible control flow;
section banners; history narration; and a second telling of an
explanation that already has a home are defects, reviewed like any
other.

External authorities (compact rules, SOW clauses, upstream issues) are
cited once, at the point where their value or rule is transcribed —
not re-cited per line.

The contract sets a documentation floor
([SOW §5.2](../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md#52-quality-standards),
"complete and current at each sprint"). The rule above governs what
that documentation says, not whether it exists:

- **Inline documentation.** Every public function, method, and class
  in the API has a docstring, and every exported component, hook, and
  function in the client has a JSDoc comment. It states purpose,
  constraints, and invariants; it does not restate the signature.
- **Major functionality.** Each feature's behavior, events, and
  permissions are documented under `engineering/docs/`, and
  updated in the same PR as the code that changes them.
- **Architecture diagram.** C4 context and container diagrams live in
  `engineering/docs/` as Mermaid, and a PR that adds or
  removes a component, service, or integration updates them.
- **Dependencies and licenses.** Every dependency is listed with its
  license in an inventory generated from the lockfiles. Third-party
  materials, open source included, need the Commission's written
  consent before they are delivered
  ([SOW §7.5](../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md#75-intellectual-property-and-open-source)),
  so a PR that adds one names it for that consent.

Exceptions require justification in the PR description.

### XII. A fresh clone runs from the README

A new engineer, or an agent, gets from `git clone` to passing tests by
following the root [`README.md`](../README.md), with nothing learned by word of mouth.

- **Pinned tools.** Tool versions are pinned in
  [`.tool-versions`](../.tool-versions) (asdf) and pnpm in the client's
  `packageManager` ([`package.json`](client/package.json)). CI installs the
  same versions; it does not hardcode its own.
- **Complete examples.** Every setting the API or client reads appears
  in its `.env.example` ([API](api/.env.example),
  [client](client/.env.example)) with a value that works locally. Copying it to
  `.env` (API) or `.env.local` (client) is enough to run the app and
  its tests against Docker Compose, with no cloud credentials and no
  access to a shared environment.
- **No secrets in examples.** Example files hold local-only values;
  the client's holds only public `NEXT_PUBLIC_*` settings.
- **One home for setup.** Setup steps live in the root
  [`README.md`](../README.md#getting-started);
  component READMEs link to them rather than repeat them. A change that
  adds a tool, a service, or a setting updates the README, the example
  file, and Docker Compose in the same PR.
- **Every documented command works.** Commands in `README.md` files and
  [`CLAUDE.md`](../CLAUDE.md) are run as part of reviewing a change that touches them.

### XIII. Dates and deadlines follow one calendar

The compact rules run on calendar dates and day counts: a privilege
expires on its qualifying license's expiration date, an incomplete
application is withdrawn after 60 days, expiry notices go out at 60,
30, and 7 days, and an adverse action is reported within five business
days ([Rule 4 §4.4](../product/context/research-corpus/sources/rule-4-compact-data-system--confidentiality-information-sharing.md)).
An off-by-one here is a compliance defect.

- **Dates are dates.** Calendar dates (expiration, issue, order,
  effective, and birth dates) are stored as `DATE` and never converted
  between time zones.
- **Instants are UTC.** Moments (submitted, decided, paid, reported)
  are stored as `timestamptz` and sent as ISO 8601 in UTC. The client
  converts to local time for display only.
- **One reference time zone.** Which calendar day an instant falls on
  ("today", "60 days after submission", whether a privilege has
  expired) is decided in one reference time zone, recorded in an ADR
  and read from one setting. No code uses the server's local time
  zone.
- **One place for day arithmetic.** Day counts and business-day counts
  go through a single module; business days follow one holiday
  calendar, recorded in the same ADR. No inline `timedelta(days=60)`
  in feature code.
- **End dates are inclusive.** A date-bound status holds through its
  end date (a privilege is active on its expiration date) unless a rule
  says otherwise
  ([FLOW-06](../product/context/flows/06-state-machines.md)).
- **Boundaries are tested.** Tests freeze time and cover the last day,
  the day after, deadlines that span weekends and holidays, and
  daylight-saving changes.

### XIV. Migrations are safe to deploy

Migrations run at API startup
([`migrations.py`](api/licensing_api/migrations.py)) while the previous
release is still serving traffic during a rolling deploy.

- **Forward-only.** There are no down migrations. An applied migration
  file is never edited; a mistake is fixed by a new migration.
- **Compatible with the running release.** Every migration works with
  both the new code and the release before it. Renames, type changes,
  and removals use expand and contract across releases: add the new
  shape, backfill, switch the code, and remove the old shape in a later
  release.
- **No long locks.** A migration that rewrites a populated table or
  builds an index on one is named in the technical plan with how it
  avoids blocking writes.
- **Tested from empty.** The test suite applies every migration to an
  empty database, so the full chain always runs.
- **Schema only.** Migrations carry no seed or test data
  ([Principle IV](#iv-no-mock-code-in-production)).

## Technology Stack

**Backend Framework**: FastAPI (ASGI)

- uvicorn locally, gunicorn with uvicorn workers in containers
- Cognito ID tokens verified with `python-jose` against the pool's JWKS
- `domain_events` Worker as a separate process on the same image

**Database**: PostgreSQL (Aurora PostgreSQL 16)

- SQLModel / SQLAlchemy async with `asyncpg`
- Migrations: plain SQL under
  [`engineering/api/db-migrations/`](api/db-migrations/), applied by
  `yoyo` under a lock at startup
  ([`migrations.py`](api/licensing_api/migrations.py)); schema only, no
  seed data ([Principle IV](#iv-no-mock-code-in-production))
- Local and CI: Docker Compose (real Postgres, not mocks)

**Cache**: Redis (ElastiCache) — only where it adds measured value

**Frontend**: Next.js (App Router), React, TypeScript (`strict`)

- Built as a static export (`output: "export"` in
  [`next.config.js`](client/next.config.js)) and served from S3 through
  CloudFront; there is no Node server in deployed environments, so no
  server-side rendering, API routes, or middleware
- Deployed separately from the API
  ([`client.yml`](../.github/workflows/client.yml)), so an API change
  must not break the client version that is live
- Cognito sign-in in the browser via `amazon-cognito-identity-js`
- USWDS via `@trussworks/react-uswds`
- Forms: `react-hook-form`
- Strings: `i18next` / `react-i18next`
- Component catalogue: Storybook

**Payments**: Authorize.net Accept UI lightbox; card data never reaches
our systems. Locally and in CI, a mock server outside the app stands in
for Authorize.net ([Principle IV](#iv-no-mock-code-in-production)).

**Email**: SES; maildev locally

**Language & Runtime**: Python and Node, versions pinned in
[`.tool-versions`](../.tool-versions) and installed with asdf
([Principle XII](#xii-a-fresh-clone-runs-from-the-readme))

**Local services**: [Docker Compose](api/docker-compose.yaml) in
`engineering/api/` runs Postgres and Redis (`just infra`); local
settings come from [`.env.example`](api/.env.example)

**Package Managers**: `uv` (Python), `pnpm` (Node)

**Configuration**: `pydantic-settings` for env-driven values only
([`config.py`](api/licensing_api/config.py))

**Quality**:

- `ruff` (lint + format), `pyright`
- `pytest` + `pytest-asyncio`, `coverage` (branch)
- `eslint`, `tsc --noEmit`, `vitest` + Testing Library
- `pre-commit` ([config](../.pre-commit-config.yaml)): ruff, gitleaks,
  markdownlint, file hygiene
- Codecov for coverage reporting ([`codecov.yml`](../codecov.yml))

**E2E**: Playwright (TS) with automated WCAG 2.1 AA scanning

**Infrastructure**: Terraform under
[`engineering/infrastructure/iac/`](infrastructure/iac/)

- CloudFront in front of both: the client from S3, `/api` from the
  API on ECS Fargate behind an internal ALB
- Aurora PostgreSQL, ElastiCache, Cognito, Secrets Manager / SSM, ECR
- CloudWatch alarms → SNS → Slack
- All infrastructure changes go through Terraform; no console changes
  that Terraform doesn't own

**Task Runner**: `just` — each component's `justfile` is its entry
point ([API](api/justfile))

## Security Requirements

The data system holds PII and disciplinary information for a
multi-state government commission. Security is a release blocker, not
an afterthought. Agents and engineers treat PII and confidential
disciplinary data as the highest-priority concern when designing or
modifying any feature. The QASP ([RFP](../product/context/research-corpus/sources/pa-compact-commission-data-system-rfp.md), [SOW](../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md))
requires OWASP ASVS conformance.

**Data residency.** All software, data, and backups reside on servers
in the United States and are never replicated, mirrored, or transited
outside it ([SOW §2](../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md#2-scope-of-work)).

**PII scope.** Practitioner identity in the uniform data set — names,
SSN, date of birth, sex, NPI, addresses, phone, email, education,
certification — license data, uploaded documents, and payment
records. Treat all of it as sensitive.

**Data the system must never hold.**

- Criminal background check results or criminal history record
  information. The system stores the check's completion date only;
  schemas reject anything more, and denial reasons are free of it.
- Card numbers or bank details. Payment entry happens on
  Authorize.net's hosted form.

**Confidentiality tiers.** Every field belongs to one tier, and the
tier is enforced in the API's response models, not the client:

- **Public**: what public verification shows.
- **States and Commission**: significant investigative information,
  non-public adverse actions, full PA records. Never shown to the PA
  (for investigative information) or the public.
- **Restricted**: the full SSN. Shown as last four digits; a full
  reveal requires the `readSSN` permission and is audit-logged.

Staff reads of private data are audit-logged, not just writes.

**Security impact assessment.** New features that touch PII or
confidential disciplinary data require a security impact assessment as
part of the technical plan, covering: what data is involved, its tier,
where it flows, how it's protected at each step, and what could go
wrong.

Version: 0.1.0 | Created: 10/05/2026 | Last amended: 10/06/2026
