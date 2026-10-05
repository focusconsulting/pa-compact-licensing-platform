# PA Compact Data System — MVP epics and tickets

<!-- markdownlint-disable MD036 -->

Fourteen epics. Each has exactly two Jira tickets:

- **Product ticket** — clarifies requirements with the Commission and produces basic lo-fi wireframes. Output: decisions logged in the assumptions log, wireframes attached to the engineering ticket. Runs one sprint ahead.
- **Engineering ticket** — the implementation, end to end (API, migrations, UI, tests, docs). The engineer breaks it into beads as they see fit; the ticket is done when every "done when" line holds.

Two engineering tickets are in flight at most times, one per engineer, each owned start to finish; in Sprints 4–6 the schedule gives an engineer a second, smaller one (epics 13 and 14) (see "How an engineering ticket is owned"). Derived from `mvp-ticket-breakdown.md` v5, which holds the reasoning, rule citations, the deferred list, and the unscheduled SOW candidates. v5 is the 2026-10-05 pass against the SOW redline response v2 (`product/context/PA Compact Data System SOW - Focus Consulting.md`); epics 13 and 14 and the changes marked "SOW v2" below come from it. The SOW's §2.1 list is now a set of candidates prioritised with the Commission's Product Manager, so epics 13 and 14 and the renewal part of epic 9 are the first things to trade if the Commission prioritises differently. `product/context/reference/compactconnect-crosswalk.md` is the product analysis against CompactConnect: journey by journey and screen by screen, what we follow, what we adapt, and where the PA rules force a different product; product tickets take their wireframe reference from it.

Sprints are two weeks, numbered 1–8. Phase 1 = Sprints 1–2, Phase 2 = Sprints 3–6, Phase 3 = Sprints 7–8.

**Definition of done, every engineering ticket:** 90% test coverage enforced · 0 lint errors or warnings · pa11y and axe clean on new screens · OpenAPI regenerated from code and the TypeScript client rebuilt on any API change · migrations forward-only · history and audit rows on every mutation · a domain event for every state change, listed in the event catalogue · runs against the local stack with no AWS credentials · docs updated in the same PR.

**Acceptance (SOW v2, §2.3, §4.2, §5.2, §8.5.2):** the "done when" lines of a ticket are its acceptance criteria and are confirmed with the Commission's Product Manager by the product ticket before the engineering ticket starts. Each sprint's software is delivered to the Commission's Product Manager and Technical Lead, who inspect it against the QASP within 5 business days. Anything they find non-compliant is corrected in the next sprint at no additional cost, so a red CI gate is never waived.

**Every screen:** wireframe from the product ticket → hi-fi comp via Claude Design with the project prompt → built from the component library → Storybook story per state.

---

## How an engineering ticket is owned

The team is async and each engineer works with a large degree of autonomy. These rules exist so an engineer can design, build, and ship an epic without waiting on anyone who is not on the critical path.

**One owner, start to finish.** The engineering ticket's owner does the hi-fi design from the wireframe, the migrations, the API, the UI, the tests, the docs, the ADRs the ticket names, the event-catalogue and notification-catalogue rows, the seed additions, the Storybook stories, the runbook entry, and the deploy to `test` (cut the `-rc` tag yourself). The owner demos it at the sprint review. Break the ticket into beads under one epic-level bead however you like; nobody else will touch them.

**Start when your blockers have landed, not when everything is ready.** "Blocked by" lists engineering tickets only. A wireframe that has not arrived does not block the data and API half of a ticket. Every "Clarify" line has a default in `mvp-ticket-breakdown.md` §6. The Commission has 5 business days to answer (SOW §8.5.2). The SOW no longer lets Focus proceed on assumptions when an answer is late: tell the PM the day a window lapses so it is notified and logged (§8.5.1). You may still build to the default so the data and API half keeps moving, but it is at risk of rework until answered, so keep the defaulted choice behind one seam (a config row, an enum, one function).

**Provides / consumes.** Each epic lists what it hands to other epics and what it takes from them. If something you consume has not landed, build the smallest stub you need in your own area, behind the agreed shape, and swap it when the real thing merges. The demo seed (epic 2) exists so that every vertical has realistic rows for the entities it does not create itself.

**You decide alone:** route paths and request and response shapes inside your namespace; columns and indexes on the tables your epic owns (forward-only migration, no approval); the internals of your components; copy, within the terminology table; job schedules; test approach; how many PRs your ticket becomes. **You decide with product** (the product ticket, or the Commission's Product Manager through our PM): anything on a Clarify line; anything that changes what the PA or the public can see; anything that reads a rule differently from the flow it cites. **You decide with the tech lead:** a new AWS service or runtime dependency; a change to a shared root table (`states`, `users`, `practitioners`, `practitioner_ssn`, `documents`, `notifications`, `domain_events`, `audit_log`); a change to a platform convention (envelopes, the auth dependency, the event and history helpers, the design tokens).

**Conventions are tests, not review comments.** A missing permission annotation, a non-envelope response, an event without a test, a private field in a public schema, a coverage drop, a lint warning, or a contrast failure fails CI. If CI is green and every "done when" line holds, the ticket is done.

**Review.** PRs stay under 600 lines. Automated review runs on every PR. A platform PR (epic 2, or anything touching the shared roots or conventions) needs the tech lead's review. A vertical PR needs one human skim within one business day; after that, or after two business days of silence with a note on the PR, the owner merges. The Commission's Technical Lead also reviews code and QASP compliance (SOW §6.1.1); by default that review happens at sprint acceptance and does not gate a merge (breakdown Q-29). A new dependency is added to the third-party materials register in the same PR (SOW §7.5; epic 1).

**Ownership by journey, not by layer.** Hand-offs between engineers happen at the platform seams (seed data, events, shared primitives), never in the middle of a user flow. The tech lead owns the platform and the state and Commission journey; the fullstack engineer owns the PA journey, the public site, and the design system. The schedule is arranged that way.

---

## Schedule

| Sprint | Tech lead (platform · state and Commission journey) | Fullstack (PA journey · public · design system) | Product tickets running |
|---|---|---|---|
| 1 | 1 Repo foundation | 3 Environments and infra security | Backend platform · Design system · Auth and accounts · Sprint 1 questions to the Commission |
| 2 | 2 Backend platform, incl. the demo seed | 4 Design system and app shell | Auth and accounts · Participation (PA side) · License records and SQL review · State data ingestion (representative states named, mock data begins) |
| 3 | 7 License records and SQL review (config + records) | 5 Auth and accounts | Participation (PA side) · Privilege and payment · State data ingestion (ingestion specification and mock data) · candidate-state sessions begin |
| 4 | 7 License records and SQL review (review + withdrawal) · 13 State data ingestion begins | 6 Participation (PA side) | Privilege and payment · Records, dashboard, reports · **usability round 1** |
| 5 | 10 Records, dashboard, and reports · 13 State data ingestion | 8 Privilege, payment, and issuance | Status, adverse actions, expiry, renewal · Public verification · NCCPA integration · **usability round 2** |
| 6 | 9 Status, adverse actions, expiry, and renewal · 10 close-out | 11 Public verification · 14 NCCPA integration · 12 accessibility sweep begins | Pilot readiness · candidate-state sessions end |
| 7 | 12 security validation · UAT fixes | 12 accessibility audit · UAT fixes | **usability round 3** · pilot readiness playbook draft |
| 8 | 12 live operations test · UAT fixes | 12 docs and transition · UAT fixes | playbook delivered · MVP completion certified · Final Review Period begins |

Milestones: `test` exists end of Sprint 1 · `prod` exists, empty, monitored, and the demo seed loads into `test` end of Sprint 2 · first release tag Sprint 3 · SQL verdict end to end in `test` Sprint 4 · privilege issued end to end in prod on test data Sprint 5 · every scheduled SOW capability in `test` Sprint 6 · UAT (the SOW's beta test) Sprint 7 · live operations test passed and MVP completion certified Sprint 8, which starts the Commission's 14-day Final Review Period (SOW §2.3).

The SOW v2 pass added about 8 engineer-days to Phase 2 (epics 13 and 14, renewal, and four smaller additions). Sprints 5 and 6 are now full for the tech lead; the slack that remains is in Sprints 3–4 and with the fullstack engineer in Sprint 6.

---

## 1. Repo foundation, local stack, and CI gates

### Product ticket

**Clarify:** licence and GitHub org (default: public from day one, Apache-2.0, Commission copyright, Commission org, Focus admins during the engagement); standing written consent to the open-source dependency list and a rule for additions (SOW v2, §7.5 requires the Commission's prior written consent to third-party materials). No wireframes.

### Engineering ticket

**Sprint:** 1 · **Blocked by:** nothing · **Provides:** the local stack and `just` targets every ticket runs on; the CI gates · **Consumes:** nothing

**Scope**

- Fix what's wrong today: `AGENTS.md` describes a Flask stack and an `api/`, `client/`, `iac/` layout that don't exist; ECS passes `DB_USERNAME` while the app reads `DB_USER`; `CORS_ORIGINS` unset; client `CurrentUser.id` vs API `user_id`; i18n never initialised; Dependabot paths stale; plaintext DB password in the dev tfvars; jumpbox secret read unconditionally; `ALLOW_USER_PASSWORD_AUTH` on the Cognito client; ElastiCache provisioned but unused (remove it). Replace the MIT/Focus `LICENSE` once the product ticket decides.
- Local stack: `docker compose up` gives Postgres, maildev, RustFS, and cognito-local (or a local JWT issuer, whichever logs in fastest); `just up`, `just seed`, `just job <name>`; env switches for email, storage, identity, payments, and worker mode; README "run the whole system in 5 minutes".
- Quality gates: Codecov enforced at 90% for API and client (migrations, generated client, IaC excluded); ESLint/Prettier/Stylelint to the GSA 18F Front-End Guide at 0 warnings; pa11y-ci over Storybook and a Playwright page list; axe in Vitest; Playwright e2e skeleton against the local stack in CI; `just check` / `pnpm check`.
- Security scanning: CodeQL (Python, TypeScript), `pip-audit`, `pnpm audit --prod`, Trivy on the image, Checkov on Terraform, gitleaks, secret scanning and push protection, CycloneDX SBOM per build feeding the licence inventory, nightly ZAP baseline against DEV with an authenticated context, SARIF to GitHub Security, `SECURITY.md`, false-positive register.
- Third-party materials register (SOW v2, §7.5): generated from the SBOM, listing every open-source component and its licence. It is what the Commission gives written consent to; a PR that adds a dependency adds it to the register.

**Done when**

- Fresh clone → `just up` → register a PA, log in, receive the welcome email in maildev, upload a file, complete a fake payment, with no AWS credentials.
- `/api/me` works on DEV; DEV applies cleanly without Redis.
- A coverage drop, a lint warning, a contrast violation, or a high/critical scan finding fails the PR. e2e smoke runs in under 5 minutes.
- Everything runs on the free tier of a public repo; if the repo must stay private, the GitHub Advanced Security cost is documented.

---

## 2. Backend platform: data model, events, API guardrails, notifications, documents, worker

### Product ticket

**Clarify:** SSN collection (full, encrypted, last-4 shown, reveal audited — or last-4 + NPI); uniform data set specifics (sex values, other-names handling, education program list source, phone required); adverse-action notification breadth (related states only vs every participating state). No wireframes.

### Engineering ticket

**Sprints:** 1–2 · **Blocked by:** Repo foundation · **Provides:** the shared root tables, the history/audit/event helpers, the auth dependency and envelopes, `notify()`, presigned documents, the worker, the demo seed · **Consumes:** the local stack from epic 1

The platform every vertical builds on. It does **not** define the endpoints — each vertical owns its own routes and models. It defines the shapes those routes must conform to. Land it in this order, each part mergeable on its own: data model + events + seed (unblocks every vertical's data and API work), then API guardrails (unblocks the client generation epic 4 consumes), then notifications, documents, and the worker.

**Scope**

- Canonical data model, PA-only, with status computed on read: states (member, effective date, live, fees, per-state proof requirements — jurisprudence, supervision agreement, prescriptive authority, other compliance, each none / attestation / upload — practice-requirements URL, distribution lists), practitioners (the uniform data set, with provenance per field group: `entered_by`, `verified_by_state`, `verified_at`, so the SQL's confirmation in epic 7 is recorded as its Rule 4 §5.3(c) submission), encrypted SSN in its own table with last-4 elsewhere, qualifying licenses, participation applications (with request note), privilege requests, privileges (pinned expiration), adverse actions (with SII flag and contact), documents, fees (including `fee_type=renewal`), renewal checks and `renewed_at` on privileges (epic 9), a `source` on each license (manual, upload, API) and ingestion batches (epic 13), the looked-up NCCPA value with its source and fetch time beside the PA-entered one (epic 14), a verified stamp per remote-state proof (epic 8), administrator contacts and a practice-requirements document per state (epic 7), transactions and state-tagged line items, notifications, domain events, history tables, audit log. `users` gains the `state_admin` role and per-state permissions. Status views for licenses and privileges. Data dictionary in `docs/`. ADRs for computed status and SSN handling.
- Table ownership after this lands: the shared roots stay with the platform; every other table belongs to the vertical named in the data dictionary (`participation_applications` and `attestations` → epic 6; `qualifying_licenses` → epic 7; `privilege_requests`, `privileges`, `fees`, `transactions` → epic 8; `adverse_actions` → epic 9). Owners amend their tables and the status views with forward-only migrations without asking; the fixture matrix here is the regression test they keep green.
- Seed and demo data: `just seed demo` — deterministic member states, attestations, practitioners, licenses, applications in every status, privilege requests, privileges, transactions, adverse actions, and SII covering every state in FLOW-06; `docs/demo.md` script for sprint reviews. This is what lets epics 9, 10, and 11 start before epic 8 lands; each vertical adds the rows its own screens need.
- Domain events and transactional outbox: `emit()` only inside a transaction; history and audit helpers; idempotent handler registry with retry and dead-letter; `WORKER_MODE=inline` for dev and test; event catalogue with a test that every event type has a test. ADR.
- API guardrails (not a contract): persona namespaces (`/me`, `/public`, `/states/{st}`, `/commission`, `/admin`) and the rule for which roles reach which; the auth dependency every route uses and how it reads the token and permissions; one success envelope, one error envelope `{code, details[]}`, and one pagination/sort convention; a permission annotation required on every route, checked by a test; OpenAPI generated from code with a drift check in CI; TypeScript client and MSW handlers regenerated by one command. A vertical adds its routes and gets all of this for free. ADR.
- Notifications: `notify(template, recipient, ctx, idempotency_key)` writes a row, the worker sends it; SES with DKIM/SPF/DMARC in Terraform; Jinja HTML and text base layout with an environment banner outside prod; catalogue of event → recipient → template; per-state distribution lists; maildev locally.
- Document storage: private KMS bucket with versioning; presigned upload with size and type limits; presigned download after a permission check scoped like everything else; GuardDuty malware scan gates download; RustFS locally; `FilePickerField` wired.
- Worker service and scheduled jobs: the outbox dispatcher as its own ECS service on the API image (`SELECT … FOR UPDATE SKIP LOCKED`); jobs registry runnable with `just job <name>`; EventBridge Scheduler → ECS run-task; run log; alarms on failure, dead-letter, and zero running tasks. ADR.

**Done when**

- Migrations apply on an empty DB and on current DEV; every table has created/updated by/at; the status views pass a fixture matrix (active, expired, encumbered, each deactivation reason, within the 2-year bar, the grace rule for an expired-but-active license).
- A mutation without an event fails a test; a throwing handler is retried then dead-lettered with an alarm; replaying an event is a no-op; two worker tasks never double-handle an event.
- A route without a permission annotation fails a test; a route returning a non-envelope shape fails a test; CI fails on OpenAPI drift; one command regenerates the client and mocks; Storybook renders a page against MSW with no API running.
- A duplicate notification idempotency key sends once; templates are snapshot-tested; SES sandbox verified on DEV.
- A 20 MB upload succeeds, 21 MB is rejected, EICAR is blocked in the test environment, and state A cannot fetch state B's case document.
- A job failure raises a Slack alarm; the dispatcher drains 1,000 backlogged events in under a minute locally.
- `just seed demo` on an empty database produces the fixture set, the status views agree with it, and the same seed loads into `test`.

---

## 3. Environments, deploy pipeline, and infrastructure security

### Product ticket

**Clarify:** Commission-owned AWS account from Sprint 1 with Focus operating inside it, or transfer at the end (SOW v2, §5.3: accounts are intended to be Commission-owned; Focus may create them as an interim measure and transfers them by contract close); RTO/RPO targets; retention; whether the United States-only requirement (SOW v2, §2) extends to CDN edge caches and to the email and payment processors. On-call belongs to the follow-on operations SOW. No wireframes.

### Engineering ticket

**Sprints:** 1–2 · **Blocked by:** Repo foundation · **Provides:** `test` and `prod`, tag-driven promotion any engineer can trigger, WAF and headers, the documents bucket's malware scan · **Consumes:** the image and migrations from epic 1

**Scope**

- `test` and `prod` tfvars and backends alongside `dev`; Terraform plan on PR (commented), apply on merge for `dev`; tag-driven promotion — `v*-rc` to `test`, `v*` to `prod` with environment protection and approval; `just deploy <env>`; immutable ECR tags with lifecycle, no `:latest`; bootstrap runbook. `test` is the live demo environment for every sprint review and must exist by the end of Sprint 1.
- Security baseline: WAF on CloudFront with managed rules and rate limits on public and auth routes; response-headers policy (CSP, HSTS, X-Frame-Options, Referrer-Policy); HTTPS CloudFront → ALB; RDS deletion protection, final snapshot, backups (7 days test, 35 prod); KMS customer key; CloudTrail and GuardDuty with S3 Malware Protection on the documents bucket; OWASP ASVS 5.0 mapping document (SOW v2 changed the QASP standard from 3.0). United States only (SOW v2, §2): every region, backup, and log destination in the US; CloudFront geo-restricted to the US.

**Done when**

- A fresh AWS account reaches a running `test` stack from the runbook alone; one tag deploys to prod.
- `prod` exists, empty and monitored, by the end of Sprint 2.
- Checkov clean; A grade on securityheaders.com; `docs/security/asvs-mapping.md` exists against ASVS 5.0; a policy test fails on a non-US region.

---

## 4. Design system and app shell

### Product ticket

**Clarify:** brand assets (logo, palette, typography, any style guide) and who approves the look; terminology sign-off (State of Qualifying License, Compact Privilege, Remote State) and the title-agnostic requirement.
**Wireframes:** navigation and information architecture for each of the three portals (PA, state, Commission) and the public landing. Nothing else — the wireframe kit itself is an output of the engineering ticket.

### Engineering ticket

**Sprint:** 2 · **Blocked by:** Repo foundation · **Provides:** tokens, the component library, the wireframe kit, the Claude Design prompt, the app shell and primitives every screen is built from · **Consumes:** the client-generation command from epic 2 when it lands; until then, hand-written MSW handlers for `/api/me`

**Scope**

- Design system: brand assets → USWDS theme tokens (primary colours, type scale, radius, spacing); Storybook component library documenting every allowed component and primitive with usage rules; the Claude Design system prompt (`docs/design/claude-design-prompt.md`: tokens, component whitelist, layout rules, terminology table, plain-language and accessibility rules, "generate from this wireframe" instructions); lo-fi wireframe kit with page templates for wizard, queue, case view, dashboard, settings form; one exemplar screen per portal approved by the Commission's Product Manager.
- App shell: USWDS `GovBanner`, header and logo, per-persona side nav driven by `/api/me`, footer and identifier, skip link; theme overrides from the tokens; primitives (PageHeading, StatusTag for every enum, EmptyState, ConfirmModal, DataTable, StepIndicator, AlertBanner, CaseLayout for review screens, QueueList with CompactConnect's "Viewing: {filters} ×" chip and age column, HistoryTimeline — the one timeline used for application status, privilege history, and the staff view — CardActionMenu, LicenseCard, PrivilegeCard); i18n namespaces; title-agnostic copy; Storybook deployed to a static path on DEV.

**Done when**

- `docs/design/` holds tokens, library, prompt, kit, and exemplars, and the shell implements the tokens.
- All three persona navs render from mocked permissions; Lighthouse accessibility 100.

---

## 5. Authentication, roles, and accounts

### Product ticket

**Clarify:** which profile fields a PA may edit after the SQL has verified them, and whether the SQL is emailed when one changes (default: no email; the change sits on the record with history and the SQL follows up if concerned, per the Aug 25 2025 committee reading); the wording of the service-of-process consent and the address-change duty; pilot states and a named staff contact per state (for provisioning); confirm an administrator reset is acceptable for a lost authenticator at pilot (CompactConnect offers self-service recovery; deferred); what "Verify military affiliation" (SOW v2, PA list) is for and who performs it — not built until answered (breakdown §5.2, Q-23).
**Wireframes:** public landing with three entries (PA / state and Commission / verify a privilege); register; TOTP enrolment; login; forgot and reset; lost-authenticator help page; PA profile form and read-only summary; staff profile page.

### Engineering ticket

**Sprint:** 3 · **Blocked by:** Backend platform; Design system and app shell · **Provides:** `require(...)`, the permission matrix, both Cognito pools, the practitioner record and profile, the staff CLI · **Consumes:** the auth dependency and `notify()` from epic 2; the shell and primitives from epic 4

**Scope**

- Roles and permissions: `licensee`, `state_staff`, `state_admin`, `compact_admin`, `admin`; per-state `read_private`, `read_ssn`, `write`, `admin`; the `require(...)` dependency from the API guardrails reads permissions from the DB per request; "is my state the SQL for this PA" and "is my state a remote state for this PA" resolved separately; licensee routes scoped to the token subject; TOTP MFA enforced in both Cognito pools and asserted from the token by the API; `/api/me` returns effective permissions. ADRs for authN and authZ.
- Staff provisioning CLI: `just staff create|permit|deactivate` (Cognito admin-create, invite email, TOTP on first login), runnable by `admin`/`compact_admin` for any state and by a `state_admin` for their own state only; `just user reset-mfa <email>` for any user after an out-of-band identity check (self-service authenticator recovery is deferred). No staff-management UI at pilot.
- PA registration and login: second Cognito pool with self-signup, email verification, and required TOTP; self-signup is a per-environment Terraform flag, off in `prod` except during the live operations test; the landing and the five auth screens; registration and reset never reveal whether an email is already registered (CompactConnect's neutral copy); sessions end after 10 minutes idle with a 30-second warning; first login creates the practitioner record; WAF rate limit.
- PA profile: the uniform data set (legal and other names, sex, DOB, NPI, address, phone, email with code-verified change — code to the new address within 15 minutes, notice to the old one — NCCPA number/status/expiry as the PA enters them (epic 14 adds the looked-up value beside them), education program and year); consent to service of process by mail and the 30-day address-change duty in copy; every address and email change is a history row; a change to a field the SQL has already verified keeps the SQL's `verified_at` and emits `practitioner.profile_changed`, and the record shows both; staff profile page.

**Done when**

- Table-driven role × endpoint test passes; a permission change is effective on the next request; a token without the MFA claim gets 401; a deactivated user gets 403; a `state_admin` CLI call outside their state is refused.
- Playwright: register → verify → enrol TOTP → log in → empty dashboard. Staff cannot use the PA entry and vice versa.
- Registering an existing email returns the same response as a new one; a request after 10 idle minutes is refused; `just user reset-mfa` forces TOTP re-enrolment on next login; self-signup is refused on `prod` while the flag is off.
- Address and email history is visible on the practitioner record.

---

## 6. Compact participation application (PA side)

### Product ticket

**Clarify:** attestation wording for participation and privilege (drafted from the model legislation and Rule 3; Commission legal signs off); sworn-statement form (default checkbox + typed name + timestamp + IP); which documents are required vs optional at application (rules allow proof of SQL basis and NCCPA evidence; default all optional); whether any participation fee exists at pilot (if yes, a checkout step is added).
**Wireframes:** every wizard step (intro, confirm profile, SQL designation and basis, license details, documents, attestations, background-check acknowledgement, review and sworn statement, submitted) plus the "information requested — resubmit" variant; PA dashboard with application timeline, privilege cards, privilege detail with history, and empty states.

### Engineering ticket

**Sprint:** 4 · **Blocked by:** Auth and accounts · **Provides:** `participation_applications`, `attestations`, `application.*` events, the PA dashboard the later epics' cards land on · **Consumes:** the practitioner record from epic 5; `states` and the seed from epic 2; documents from epic 2; the wizard and timeline primitives from epic 4

Phase 1 of the two-phase flow (FLOW-01, FLOW-02): the PA applies to the Commission and designates a State of Qualifying License (SQL).

**Scope**

- Attestations catalogue: versioned attestation texts with `applies_to` (participation or privilege), seeded from the model legislation and Rule 3 (truthfulness, ARC-PA graduate, current NCCPA, no convictions, no controlled-substance action, no current restriction, 2-year bar, not under investigation in the SQL only, remote-state supervision and prescribing compliance, jurisprudence per state, service of process). Applications store `{id, version, accepted_at}`; a stale version is rejected.
- Application wizard: intro → confirm profile → designate SQL and basis (primary residence, ≥25% of practice, employer, tax residence, or service member/spouse) → license details (or pick a state-entered record) → documents → attestations → background-check acknowledgement → review and sworn statement → submit. Server-side draft on every Continue; Cancel returns to the dashboard; refresh or deep link lands on the first incomplete step; `opened_at` on submit; PA can withdraw. When the SQL requests information, the wizard reopens with the SQL's note at the top and a Resubmit action.
- PA dashboard: SQL block with "Verified by {state} on {date}" once epic 7 has verified, and the license card; application timeline (submitted → under review → information requested, with the note → eligible or denied, with reason and appeal note); privilege cards (state, number, status, issued, expires, "expiry tied to your qualifying license") with a history timeline that shows "Expiring in N days" with a caution icon under 90 days; one primary action ("Apply for participation" / "Apply for privileges") with a "Why is this unavailable?" list when it is not (application in review, information requested, not yet eligible, two-year bar, eligibility withdrawn); empty states.

**Done when**

- A draft survives logout; submit is atomic and requires a live SQL; withdraw works; resubmit returns the application to `submitted` and keeps the note in history.
- Any document marked required blocks submit with a clear message.
- Dashboard reflects the database on load; timelines come from history rows, not stored events.

---

## 7. Qualifying license records and SQL eligibility review (state side)

### Product ticket

**Clarify:** how a state's data arrives now that the SOW lists state upload by file and API (epic 13): the PA enters and the SQL verifies, staff pre-load by hand, or the state uploads (default: PA enters, SQL verifies, and an uploaded license is the on-file record the SQL compares against; open in `TENSION-04-state-upload-versus-multi-party-record`); counsel to confirm that the SQL's in-system verification is its "verify and submit" of the uniform data set under Rule 4 §5.3(c) for a state that sends no feed; the background check is entirely outside the system and only the completion date is recorded; denial reason list (must exclude criminal history) and the appeal text (30 days, with the SQL); fee decisions from the March 2026 finance and rules meetings; each pilot state's practice requirements (a URL or a document to upload), its licensing administrator contacts, and which remote-state proofs it requires as attestation vs upload.
**Wireframes:** compact settings list and state settings form; member-state contacts directory; license entry form and license card; SQL queue with age and 60-day countdown; SQL case view with the four-item checklist (basis, license, background check, attestations), request-information control, and one decision control; withdraw-eligibility confirmation. **This screen has no CompactConnect equivalent — wireframe it first; usability round 2 tests it.**

### Engineering ticket

**Sprints:** 3–4 · **Blocked by:** Auth and accounts (configuration and license records can start in Sprint 3); Participation (PA side) for the review itself · **Provides:** state and compact configuration, `GET /public/states`, `qualifying_licenses`, the first queue and case view (the pattern epic 8 copies), eligible applications for epic 8 to build on · **Consumes:** `require(...)` and the staff CLI from epic 5; applications from epic 6 (the seed's until it lands); CaseLayout and QueueList from epic 4

The SQL's four duties from Rule 3: evaluate eligibility, run the background check, confirm the SQL basis, and issue the verdict through the data system.

**Scope**

- Compact and state configuration: seed all member states with effective dates; `compact_admin` makes a state live (one-way, with a confirm dialog); a `state_admin` lands on their own state's form; per state — privilege fee (versioned), each remote-state proof (jurisprudence, supervision agreement, prescriptive authority, other compliance) as none / attestation / upload, practice requirements as a URL or one uploaded document (SOW v2: "Upload state practice requirements"), ops and adverse-action and report distribution lists, licensing administrator contacts (SOW v2), and a read-only directory of every member state's contacts for state and Commission users (SOW v2); Commission fee (default $0 until Rule 6 sets one) and report recipients; `GET /public/states`. A `state_admin` edits their own state; `compact_admin` any.
- Qualifying license records: state `write` users create or update a license for a practitioner (find-or-create by name + DOB + last-4 or NPI): number, state-reported status, issue and expiry dates, unrestricted flag; computed status; history classifies each change (renewal, deactivation, other); the PA sees it on their dashboard.
- Eligibility review: queue and case view as wireframed; the case view shows the PA's claimed license beside the on-file record with differences highlighted and the record's source (entered by staff, or ingested by epic 13), and any adverse action or open SII the state already holds on this PA next to the "not under investigation" attestation; actions — verify license (links or creates the record) and confirm identity, which stamps `verified_by_state` and `verified_at` on the identity field groups (this is the SQL's Rule 4 §5.3(c) submission), record background-check completion date only, attach a verification document (retained on the record), request information (note + status flip + email link, never the note body), decide eligible or deny with a reason. The decision is the rule's "notice to the Commission through the data system": emails to the PA and Commission ops, dashboard update. Denial email carries the appeal text.
- Abandonment and withdrawal: a job that withdraws applications still open 60 days after `opened_at` and abandons privilege requests unpaid for 60 days; an SQL action to withdraw eligibility that cancels every privilege atomically and emails the PA (with appeal note) and each remote state.

**Done when**

- Only SQL-state `write` users can act; a decision requires license verified and background check completed; the verdict is immutable except by withdrawal; everything is audited; state A sees nothing of state B's applications.
- Verification stamps provenance on every identity field group and the PA's dashboard shows "Verified by {state} on {date}"; an attached verification document appears on the practitioner record.
- Fee history is retained; a non-live state cannot be selected; a state admin cannot edit another state; the contacts directory is not reachable by a PA or the public.
- A license whose expiry moves later shows as a renewal in history; status flips to inactive the day after expiry with no job.
- Cascade on withdrawal is atomic; a withdrawn PA cannot start a privilege application; both 60-day clocks have boundary tests.

---

## 8. Privilege application, payment, and remote-state issuance

### Product ticket

**Clarify:** who opens the Authorize.net merchant account (Commission is merchant of record) and when sandbox (needed by Sprint 3) and live credentials arrive; confirm the Accept UI lightbox form and its documented accessibility exception; confirm card only, no bank payment; card-fee pass-through yes/no; state privilege fee amounts; confirm the 72-hour clock (paid request received by the remote state → issuance) as a dashboard target, not an SLA — SOW v2 removed the sentence that said so and now has the PA receive confirmation of "timely" issuance, so this needs the Commission's answer, not just the RFP Q&A; note that SOW v2 §7.4 puts all processor costs on the Commission.
**Wireframes:** select remote states; per-state panel (fee, proofs as checkbox or upload, practice-requirements link); fee summary; attestations and acknowledgements; pay (lightbox) and done; remote-state queue with age against 72 hours; remote-state case view with a "verified" control per proof, a sticky "Issue privilege", and deny-with-reason.

### Engineering ticket

**Sprint:** 5 · **Blocked by:** License records and SQL review · **Provides:** `PaymentProvider`, `transactions`, `privilege_requests`, `privileges`, privilege numbers, `privilege.*` and `payment.*` events, the remote-state queue · **Consumes:** eligible applications and state configuration from epic 7; attestations, documents, and the dashboard from epic 6; the seed's eligible applications until epic 7's review merges

Phase 2 of the flow (FLOW-03). The end-to-end milestone: a privilege issued in prod on test data by the end of this sprint.

**Scope**

- Payments: `PaymentProvider` protocol (`create_checkout`, `handle_webhook`, `get_status`); `FakeProvider` locally (cents `.00` approves, `.99` declines, posts the real webhook shape); Authorize.net adapter using the Accept UI lightbox so card data never touches our servers; transactions and line items tagged by state and Commission fee so fees can be remitted per state; HMAC-SHA512 webhook verification; idempotent on provider reference; receipt email; `GET /me/transactions`; credentials in Secrets Manager. Card only; fees are non-refundable, so no void or refund path. ADR.
- Privilege application: entry only if participation is eligible and no 2-year bar applies; pick live remote states (non-live states do not appear; the SQL and states with an active privilege are disabled; up to 20 per checkout); per-state panel as wireframed; server-computed fee summary; privilege attestations; "expires on <license expiry>" and "fees non-refundable" acknowledgements; checkout; one privilege request per state.
- Remote-state issuance: queue and case view as wireframed, including SQL verdict and date, license, attestations and uploaded proofs, payment, and PA contact; the remote state marks each proof it requires as verified before issuing (SOW v2: "Verify completion of jurisprudence exam requirements"; the same control serves the other three proofs); actions — issue (number `PA-{ST}-{n}` from a per-state sequence, `issued_at`, `expiration_date` = the license expiry snapshot taken at request time) or deny with reason; emails to the PA, SQL ops, and Commission ops; time-to-issue metric.

**Done when**

- Switching `PAYMENT_PROVIDER` between fake and Authorize.net needs no code change; a replayed webhook is a no-op; a decline leaves requests in `pending_payment`; ZAP and review confirm no card data reaches the API; lightbox accessibility findings are recorded for the audit.
- Requests exist only after an approved payment; the total matches the server; e2e passes on the fake provider.
- Cannot issue unless participation is eligible, the transaction is paid, and every required proof is marked verified; numbers are unique and monotonic per state; expiration stays pinned even if the license is renewed afterwards (tested).

---

## 9. Status changes, adverse actions, expiry, and renewal

### Product ticket

**Clarify:** adverse-action report fields (summary + NPDB category, not documents) and the 5-day / 1-business-day windows; notification breadth (related states vs every participating state — see the tension note in the evidence folder); are Rules 3 and 4 final enough to build to (misdemeanor eligibility is still on the rules agenda); expiry notice cadence beyond the 60-day minimum (default 60/30/7); renewal (SOW v2: "Renew privileges"): whether a renewal is charged the same fees as a first privilege, and the wording of the SQL's continued-eligibility check.
**Wireframes:** license status update form with effective date; privilege deactivation with note; adverse-action report form (modal from a license or privilege card) with the SII flag; lift action; the confidential banner state; the renew action on a privilege card, the SQL's renewal check, and the remote-state renewal case.

### Engineering ticket

**Sprint:** 6 · **Blocked by:** License records and SQL review; builds against the seed's privileges and integrates with Privilege, payment, and issuance as it lands (renewal needs epic 8 merged) · **Provides:** `adverse_actions`, the cascade functions, the status-update and report forms, the expiry jobs, renewal · **Consumes:** `qualifying_licenses` from epic 7; `privileges` from epic 8; documents and the worker from epic 2; CardActionMenu from epic 4

Everything that changes a license or privilege after issuance (FLOW-04, FLOW-05). Cascades are pure functions with a test matrix so a rule change is a one-file change.

**Scope**

- Status updates: state actions on a license — expired, lapsed, inactive, reinstated, terminated, with effective date; deactivate a privilege with a note (issuing state or Commission override). Cascade matrix: license inactive/expired/terminated → all privileges inactive with reason; voluntary termination ends all privileges as of that date; a license still marked active past its expiry keeps privileges active until the SQL updates it; a reinstated license does not reactivate privileges. Emails to the PA and affected states.
- Adverse actions and SII: a state reports an action against a license or a privilege as a structured record — type, NPDB category (multi), summary, order date, effective start, emergency flag, public flag, optional attachment. License action → every privilege deactivated atomically; privilege action → that one only; lift with an effective end date; the 2-year bar sets `eligible_again_on`, enforced on new applications. SII is a flag plus contact and brief description, closable, visible only to state and Commission users, never emailed to the PA. Notifications to the PA (adverse action only), related states, and the Commission. Non-public records never reach public verification and carry a "confidential — do not redisclose" banner for state users.
- Expiry: a daily job emailing the PA at 60, 30, and 7 days before privilege expiry, once per threshold; a daily job writing the expiry history row and emailing the PA. Status itself is computed.
- Renewal (SOW v2; was deferred): the PA starts a renewal once the license's expiry is later than the privilege's pinned expiry; the SQL confirms continued eligibility on its case view with a renewal badge; the PA requests the same remote states with the renewal fee; on issue the privilege keeps its number and issue date and gains a renewed date and a new pinned expiry; jurisprudence already met may be reused before expiry. A PA whose privilege has already expired applies again and gets a new number. Check the wording against adopted Rule 3 first (FLOW-04's needs-review note). This is the part of the epic to trade away first if the Commission prioritises differently.

**Done when**

- Cascade matrix covers at least 8 cases and the 2-year bar; computed views reflect cascades; every affected privilege has a history row.
- Lifting one of two actions leaves the privilege encumbered; negative tests prove SII never appears in PA or public responses.
- Each expiry notice fires once per threshold, with frozen-time boundary tests.
- Renewal is refused until the license expiry has moved; number and issue date are unchanged after renewal; demonstrated on seed data in `test`.

---

## 10. Practitioner records, Commission dashboard, and reports

### Product ticket

**Clarify:** which dashboard tiles the Commission wants first (default five: applications by status, requests by status, issued last 30 days, median time-to-issue vs 72 hours, aging queues); which reports state users may export; what "payment reconciliation and financial reporting to Member State administrators to verify payment for each privilege issued" (SOW v2; it was out of scope) has to show — default: processor-approved payments per privilege and a remittance summary, no settlement status, since SOW §7.4 still says Focus is not responsible for reconciliation or settlement; brief pilot states that search is scoped to PAs with a relationship to their state (CompactConnect-experienced staff will expect to see everyone).
**Wireframes:** search and results; practitioner detail with sections (identity, SSN reveal with reason, history, licenses, applications, privileges, adverse actions, SII, documents); dashboard tile grid; reports page with filters and export; own-state transactions page.

### Engineering ticket

**Sprints:** 5–6 · **Blocked by:** Auth and accounts; builds on the demo seed and integrates with epics 7, 8, and 9 as each lands (the adverse-action section lands with Status, adverse actions, and expiry) · **Provides:** search, the practitioner record, the dashboard, CSV reports · **Consumes:** every vertical's tables and history; `read_private` and `read_ssn` from epic 5; DataTable and HistoryTimeline from epic 4

**Scope**

- Search and detail for state and Commission users: search by name, NPI, license number, privilege number, SQL state, privilege state, status, and expiring within N days (with the privileges export, this is SOW v2 "View privilege issuance, renewal, and expiration data"). State users see only practitioners using their state as SQL or holding a privilege or request there; Commission sees all. Detail as wireframed, with private fields gated by `read_private` and SSN reveal gated by `read_ssn` and audited with a reason; Commission-only privilege deactivation with note.
- Commission dashboard: the agreed tiles from the status views, each drilling through to search.
- Operational reports: CSV exports with date and state filters — privileges issued/renewed/expired/deactivated; applications received/decided with time-to-decision; transactions by state (PA, privilege, amount, provider reference, date); adverse actions reported. Definitions in code with golden-file tests; state users get their own state's rows only.
- Financial reporting (SOW v2): an own-state transactions page ("Access state financial transactions"); a payment verification report with one row per privilege issued (number, PA, state fee, Commission fee, transaction, provider reference, paid date) so a state administrator can confirm payment behind each privilege; a remittance summary per state per period for the Commission. All from processor-approved transactions.

**Done when**

- Scoping is proven (state A cannot see an unrelated PA); SSN reveal is audited with a reason.
- Dashboard numbers reconcile with search; renders in under 2 seconds on the demo seed; every chart has a data table.
- Golden-file tests pass for every report; a state user's export contains only their rows.

---

## 11. Public privilege verification

### Product ticket

**Clarify:** which fields the public sees beyond the rule minimum of name plus states (default adds privilege number, status, and dates; no adverse-action data; no NPI search); SOW v2 has the public verify "active and inactive" privileges — confirm an inactive privilege shows its status and dates and never the reason.
**Wireframes:** search, results, detail.

### Engineering ticket

**Sprint:** 6 · **Blocked by:** Backend platform (seed); Design system and app shell; real data arrives with Privilege, payment, and issuance · **Provides:** `/verify` and `/api/v1/public/*` with the allow-list schema · **Consumes:** `privileges` and the status views; the WAF rate limit from epic 3

**Scope**

- `/verify`: search by last and first name together, or by exact privilege number; results; detail showing the agreed fields and nothing else. Inactive privileges (expired, deactivated, encumbered) are returned with their status and dates, never the deactivation reason or the action behind it (SOW v2; FLOW-05). Unauthenticated `/api/v1/public/*` with strict response schemas; WAF rate limit returning 429; no enumeration.

**Done when**

- Schema tests prove no private or non-public field can appear; a privilege deactivated by a non-public adverse action shows as inactive with no reason; the rate limit works; pa11y clean.

---

## 12. Pilot readiness: accessibility, security validation, documentation, live operations test

### Product ticket

**Clarify:** UAT participants and dates (UAT is the SOW's "beta testing"); the live operations test (SOW v2, §2.3): who the Commission's testers and state staff are, what the Commission-controlled test data is, sandbox or a live card transaction, and the date; whether Focus certifies completion at the Sprint 7 or the Sprint 8 review, since the Commission's 14-day Final Review Period and Focus's 14-day no-cost remediation follow it; transition recipients for the repo, AWS account, monitoring, and third-party credentials. Also owns the **pilot readiness playbook** (SOW v2, §2.3): state onboarding workflow, technical integration pathway, and go-to-market plan, from sessions with up to two Commission-identified candidate states. No wireframes.

### Engineering ticket

**Sprints:** 6–8 · **Blocked by:** everything above (the accessibility sweep starts in Sprint 6 after epic 11; the rest closes out in Phase 3) · **Provides:** the QASP evidence, the transition package, the passed live operations test, the launch runbook · **Consumes:** everything

**Scope**

- Accessibility audit (Sprints 6–7): manual audit per screen (keyboard, NVDA and VoiceOver, 200% zoom, reduced motion, contrast, focus order, error association); fixes to zero; accessibility statement; pa11y-ci over every authenticated route; the payment lightbox exception documented.
- Security validation (Sprint 7): full ZAP active scan with authenticated contexts for every persona against `test`; ASVS 5.0 level 2 walk with evidence (SOW v2); fix medium and high; false-positive register; SBOM licence review and the third-party materials register reconciled with the Commission's written consent; secrets rotation drill; Cognito review.
- Documentation and transition (Sprints 7–8): C4 context and container diagrams; `docs/` index covering data model, API (Redoc), events, notifications, permission matrix, runbooks (deploy, rotate secrets, restore DB, add a state, provision staff and state admins via CLI, reset a user's authenticator); generated dependency licence inventory; transition checklist (repo, AWS account, logging and monitoring, Authorize.net, SES, and NCCPA credentials; anything Focus provisioned as an interim measure); the technical integration pathway for a state (ingestion specification, API reference, credential issue) as the engineering chapter of the playbook; one state-staff guide and one Commission guide; docstring/JSDoc coverage gate.
- Live operations test (Sprint 8; SOW v2, §2.3 — live pilot operations are out of scope, so this replaces go-live): the end-to-end script (register → participation → SQL verdict → privilege request → payment → issuance → public verification → status change) run in `prod` by the Commission's testers on Commission-controlled test data; payment in the processor's sandbox unless the Commission asks for a live transaction; SES production access; restore drill with timings; RTO/RPO stated; alarms; WAF tuned; seed states, fees, and attestations; test staff provisioned; PA self-signup on only for the test window; each runbook walked by someone other than its author; smoke suite in prod; the test record signed by the Commission's Product Manager; a launch runbook listing what a real pilot launch still needs (live processor credentials, real staff, self-signup on, on-call, test data purged).

**Done when**

- 0 automated and 0 manual accessibility findings, with test plan and results delivered.
- ZAP report clean of medium and high; security scan report delivered.
- A new engineer stands up local and deploys to `test` from the docs alone.
- The live operations test passes end to end and its record is delivered; test data is purged by one documented command; the launch runbook exists.

---

## 13. State licensee data ingestion (file upload and API)

Added in the SOW v2 pass. SOW §2.1: "Upload PA identifying information and licensure data" and "Upload compact uniform data set, as defined by compact policy, via API capability". SOW §3, Phase 2: "State licensee data ingestion (multi-format: API and upload)", designed against mock data.

### Product ticket

**Clarify:** which two or more representative member states the Commission names, and who in each can describe their data structures by Sprint 3; the open points in `product/context/evidence/tensions/TENSION-04-state-upload-versus-multi-party-record.md` — what the upload is for, which PAs a state uploads, what state staff still do per PA once data is uploaded, whether a later upload can end a privilege on its own, which value wins when the upload and the PA disagree.
**Output besides wireframes:** mock data files for each representative state, built with the Commission, and the ingestion data specification that covers where their formats diverge (SOW §3).
**Wireframes:** upload; preview with row errors; batch history; held changes awaiting staff confirmation.

### Engineering ticket

**Sprints:** 4–5 · **Blocked by:** License records and SQL review (the license-record half, Sprint 3) · **Provides:** the ingestion specification, the upload screen, the ingestion API and its machine credentials, `ingestion_batches` · **Consumes:** the license-record service and match keys from epic 7; `require(...)` and the staff CLI from epic 5; documents from epic 2

**Scope**

- One specification, two routes: a CSV upload in the state portal (validate → preview with row-level errors → commit; downloadable error report) and an authenticated JSON API with the same schema. One validator and one writer behind both.
- Machine credentials scoped to one state, issued and rotated through the staff CLI.
- Rows are written through epic 7's license-record service with their source, find-or-create on the same match keys, with history, audit, and events; each run is a batch row (who, when, counts, rejects).
- Built to Focus's preference until the Commission answers TENSION-04: ingestion writes the state's own license fields only; it does not create PA accounts, gate sign-up, or set eligibility; the SQL's review is still the decision; a row that would change the status or expiry of a license behind an active privilege is held for staff confirmation instead of cascading; the specification carries match keys, not the full SSN.
- Mock data only. No production data from a state and no connection to a real state system (SOW §2.3). Receiving real member-state data also starts the SOW §8.6 cyber-insurance requirement, so it is a contract event, not an engineering one.

**Done when**

- The same batch through upload and API produces the same rows; a re-sent batch is a no-op; a malformed row is rejected with its line and reason.
- State A's credential cannot write state B's records.
- An ingested license is the on-file record in epic 7's claimed-versus-on-file comparison, labelled with its source.
- Held changes are listed and applied only on confirm; nothing ingested changes a privilege on its own.

---

## 14. National credentialing integration (NCCPA)

Added in the SOW v2 pass. SOW §2.1, Commission list: "Integrate with national credentialing organizations" (it was out of scope in the earlier SOW).

### Product ticket

**Clarify:** who signs NCCPA's third-party contract and when (Executive Committee minutes, 2026-05-13: CSG, NCCPA, and Focus met on 2026-05-11; the contract is completed once development begins); any cost and who bears it; API documentation and a sandbox; which fields NCCPA returns and how often status may be refreshed. No wireframes beyond the mismatch flag on the SQL case view (epic 7's wireframe).

### Engineering ticket

**Sprint:** 6 · **Blocked by:** Auth and accounts (the PA profile) · **Provides:** `CredentialingProvider`, the looked-up certification value on the practitioner record · **Consumes:** the profile from epic 5; the worker from epic 2; the SQL case view from epic 7

**Scope**

- `CredentialingProvider` protocol with a fake provider locally and in `test`; the NCCPA adapter when the contract and API documentation arrive.
- Lookup when the PA saves a certification number, when the SQL opens the case, and on a scheduled refresh for PAs with an open application or an active privilege.
- The result is stored with its source and fetch time beside what the PA entered, not over it; a mismatch is flagged on the SQL case view; when the provider is unavailable the PA-entered value stands and the case view says so. The SQL still verifies the certification fields; the lookup informs that check.

**Done when**

- Switching the provider between fake and NCCPA needs no code change; a provider timeout blocks neither the profile save nor the SQL decision; lookups are audited; no NCCPA credential is in the repo.

---

## Cross-cutting product work (not tied to one epic)

- **User research plan** due end of Sprint 2; usability rounds in Sprint 4 (PA registration and application, including the note-and-resubmit loop), Sprint 5 (state portals — this round decides whether note-and-resubmit stands or a message thread comes back), Sprint 7 (Commission and public, small sample since UX is at 15% in Phase 3).
- **Assumptions log** (`product/context/assumptions-log.md`, not yet created — the PM creates it in Sprint 1) seeded from every "Clarify" line above and the deferred and candidate lists in the breakdown (§5.1, §5.2). Every question is logged with the date it was sent; one unanswered after the SOW's 5-business-day window (§8.5.2) is notified to the Commission with its impact (§8.5.1), and the default being built to is marked as at risk. Engineers append to it when they build to a default.
- **Sprint 1 questions to the Commission** are the "Clarify" lines of epics 1–8 and 13–14 sent as one batch, plus: the Commission's own data-system user stories from the March 2026 executive agenda; how the Technology Subcommittee is consulted between sprints; who the Commission's Technical Lead is and what access they need; the names of the representative states (epic 13) and the candidate states (playbook).
- **Estimates** (SOW v2, §3): the sizes in the breakdown's §5 are the rough estimates the SOW asks Focus to give per functionality. The PM shares them with the Commission's Product Manager when a ticket is prioritised, and an owner who sees a ticket running over says so, with the reason, before the sprint review.
- **Pilot readiness playbook and candidate-state engagement** (SOW v2, §2.3): sessions with up to two candidate states in Sprints 3–6, draft in Sprint 7, delivered in Sprint 8. Owned by the epic 12 product ticket.
- **Completion certification** (SOW v2, §2.3): Focus certifies MVP completion in writing once UAT has no open issues; the Commission then has 14 calendar days to review and Focus 14 to remediate at no additional cost. Default: certify at the Sprint 8 review (breakdown §7, risk 11).

---

## Appendix — mapping to the breakdown

For anyone cross-referencing `mvp-ticket-breakdown.md`.

| Epic | Breakdown items |
|---|---|
| 1 Repo foundation, local stack, and CI gates | F-01, F-14, F-07, F-08 |
| 2 Backend platform | F-02, F-05, F-03 (guardrails only), F-11, F-12, F-13, H-05 |
| 3 Environments and infrastructure security | F-09, F-10 |
| 4 Design system and app shell | X-01, F-06 |
| 5 Authentication, roles, and accounts | F-04, U-01, U-03 |
| 6 Compact participation application | S-03, L-03, L-04 |
| 7 License records and SQL eligibility review | S-01, L-01, L-05, L-06 |
| 13 State licensee data ingestion | L-02 |
| 14 National credentialing integration | N-01 |
| 8 Privilege application, payment, and issuance | P-02, P-01, P-03 |
| 9 Status changes, adverse actions, expiry, and renewal | A-01, A-02, A-04, A-05 |
| 10 Records, dashboard, and reports | D-01, C-01, C-02 |
| 11 Public privilege verification | V-01 |
| 12 Pilot readiness | H-01, H-02, H-03, H-04 |
| Cross-cutting product work | X-02, X-03, X-04, X-05, X-06, §6 questions |

---

## Revision — 2026-09-30, second pass

Checked against the SOW, `product/context/flows/`, the evidence signals, and the CompactConnect crosswalk. Changes: added "How an engineering ticket is owned" and provides/consumes lines on every epic; schedule now assigns whole epics by journey (tech lead: platform, state, Commission; fullstack: PA, public, design system); demo seed moved from epic 12 (Sprint 5) into epic 2 (Sprint 2) so epics 9, 10, and 11 start on realistic data instead of waiting on epic 8; epic 4 unblocked from epic 2; per-field provenance on the practitioner record (the uniform-data-set signal) added to epics 2, 6, and 7; crosswalk items previously marked "add to U-01" or "gap" added to epic 5 (session timeout, neutral registration copy, authenticator reset, per-environment self-signup flag), epic 6 ("why unavailable" list, "Verified by", "Expiring in N days", wizard behaviour), and epic 7 (one-way go-live, claimed-vs-on-file diff, existing adverse actions and SII in the case view, SQL-attached verification documents); the counsel question on "verify and submit" and the scoped-search briefing added to the product tickets of epics 7 and 10.

---

## Revision — 2026-10-05, SOW redline response v2

The SOW was replaced with the redline response v2; this file follows `mvp-ticket-breakdown.md` v5. Changes: two epics added (13 state licensee data ingestion, 14 NCCPA integration) and renewal added to epic 9, all of them the first things to trade if the Commission prioritises differently; epic 7 gains administrator contacts, the member-state directory, and an uploaded practice-requirements document; epic 8 gains per-proof verification by the remote state; epic 10 gains the state transactions page, the payment verification report, and the remittance summary; epic 11 shows inactive privileges without a reason; epic 12's go-live becomes the live operations test and it owns the pilot readiness playbook; ASVS 3.0 becomes 5.0; United States-only hosting and the third-party materials register added to epics 3 and 1; the acceptance paragraph, the Commission Technical Lead's review, the 5-business-day windows, and the loss of the proceed-on-assumptions sentence added to the operating model. Military affiliation is not scheduled (breakdown §5.2). Nothing in this revision has been prioritised with the Commission's Product Manager yet.
