# PA Compact Data System — MVP Ticket Breakdown (draft v5)

<!-- markdownlint-disable MD036 -->

**Status:** brainstorm draft, revised 2026-09-30 against the SOW, `product/context/flows/`, and `product/context/evidence/`, descoped in a second pass (§5.1 lists every cut and what brings it back), three cuts reversed on CTO review (worker service, document upload, `state_admin` role), the API contract reduced to guardrails, a v4.3 pass aligning to the CompactConnect crosswalk and the uniform-data-set signal, and a v5 pass on 2026-10-05 against the SOW redline response v2, which replaced the SOW this backlog was derived from (§8). The Jira-ready consolidation of this document is `mvp-jira-tickets.md`; its "How an engineering ticket is owned" section is the operating model for the async team, and where its schedule differs from §3.3 the Jira schedule governs.
**Scope rule:** the SOW (`product/context/PA Compact Data System SOW - Focus Consulting.md`, redline response v2; §2.1, §2.3, §3, §5) is the source. §2.1 is now "Expected Core MVP Functional Capabilities": the anticipated universe of features and an input to prioritisation with the Commission's Product Manager, "not a fixed requirements list". So: what is needed to issue a privilege end to end is `must`; every other §2.1 item is either scheduled as `should` in the smallest form that satisfies it, or held as a `candidate` in §5.2 until the Commission prioritises it or answers the question that blocks it. RFP-only stories are dropped. Compact-rule behaviour is kept and marked `rule`. SOW section numbers below are the redline response v2's (the assumptions and engagement sections moved from §8.3 to §8.5).
**Target:** a pilot-ready, production-grade MVP accepted through a live operations test on Commission-controlled test data (SOW §2.3). Live pilot operations are out of scope for this period of performance; "pilot" below means that environment and that test, not real PAs. Work is ordered so that a deployable, secure, monitored production environment exists from Sprint 2 and every sprint's work lands in it.
**Flows:** read `product/context/flows/` first — the sequence diagrams there define what these tickets implement. Rule citations resolve to atoms in `product/context/evidence/atoms/`. Where this v4 pass cut something a flow still shows, §8 lists it so the flow can be updated.
**Reference implementation:** `../CompactConnect` (AGPL-3.0) for data shapes, workflows, screens; not storage or hosting. The product analysis against it, journey by journey and screen by screen with postures (follow / adapt / deviate / new), is `product/context/reference/compactconnect-crosswalk.md`.
**Team (SOW §6.1):** Tech Lead + Fullstack Engineer, async, AI-driven. The lanes below (A backend-leaning, B frontend-leaning) are v4's layer split; `mvp-jira-tickets.md` assigns whole epics by journey instead (tech lead: platform, state and Commission; fullstack: PA, public, design system) so hand-offs happen at platform seams, not mid-flow; PM/Product Lead at 80/50/30% and UX Designer/Researcher at 100/50/15% across the three phases. Product/design produces lo-fi wireframes; engineers produce hi-fi with Claude Design + the USWDS design library.

---

## 0. How to read this

- **Vertical slices.** Each ticket ships API + migration + UI + tests + docs for one capability, sized for one engineer in 1–2 days with AI tooling.
- **Contracts first, but not the API.** Tickets marked `CONTRACT` define shapes (data model, events, API guardrails, roles, notifications). Once merged, anyone builds against them with mocks/fakes. Endpoints themselves are defined by the vertical that owns them; the platform only fixes the auth dependency, envelopes, and conventions they must follow.
- **Every UI ticket has a design step** (§2.3): lo-fi wireframe from product/design → hi-fi via Claude Design with the project system prompt → implement with the design library.
- **Every ticket runs locally with no AWS.** The local stack (F-14) provides fakes for email, object storage, identity, and payments.
- **Tier:** `must` = required to issue a privilege end to end in the production-grade pilot environment; `should` = SOW §2.1 item scheduled in v5 that the live operations test survives without, and therefore the first thing the Commission's Product Manager can trade away; `rule` = compact-rule behaviour folded in; `candidate` = SOW §2.1 or §2.2 item not scheduled (§5.2); `deferred` = cut in v4, listed in §5.1 with its re-entry trigger.
- **Lane:** the SOW's two-engineer split (A backend-leaning, B frontend-leaning). One engineer: follow §3.2.
- **Sprints:** numbered 1–8 to match SOW §3 (16 weeks). Phase 1 = Sprints 1–2, Phase 2 = Sprints 3–6, Phase 3 = Sprints 7–8. There is no unfunded "Sprint 0"; foundation work is Sprint 1.

---

## 1. Ground truth

### 1.1 Repo state (audited 2026-09-29, re-checked 2026-09-30, main @ 5593c40)

Layout is `engineering/{api,client,infrastructure,docs,thoughts}` plus `product/`. Built: FastAPI + SQLModel + asyncpg on ECS Fargate; yoyo migrations at startup; JSON logging; OTel → ADOT; Cognito pool (admin-create only) + JWT validation; one `users` table with `role` CHECK; Next.js 14 static export + `@trussworks/react-uswds` 11, login, protected dashboard, 10 USWDS form components; Vitest; Storybook; Terraform for DEV (ALB/ECS/Aurora/ElastiCache/CloudFront/Cognito/Secrets/Route53/Slack alarms); GH Actions lint/test/deploy-DEV; pre-commit with gitleaks; Codecov (informational, target 90%); ADRs 0001–0004 in `engineering/docs/architecture_decision_records/`; `LICENSE` = MIT © Focus Consulting 2026.

Gap: no domain tables, no RBAC enforcement, no events/jobs, no email, no payments, no typed API client, no USWDS theme tokens, no app shell, no test/prod envs, no Terraform CI, no WAF/security headers, no SAST/DAST/a11y in CI, coverage not enforced, `AGENTS.md` describes a Connexion/Flask stack and an `api/`, `client/`, `iac/` layout that no longer exist.

Bugs to fix in F-01 (each re-verified in the tree on 2026-09-30): ECS sets `DB_USERNAME` (`ecs.tf:167`) while the app reads `DB_USER`; `CORS_ORIGINS` unset; client `CurrentUser.id` vs API `user_id`; i18n not initialised in the app; Dependabot directories point at `/api`, `/client`, `/infrastructure/…` instead of `/engineering/…`; plaintext `db_password = "password"` in `environments/dev/us-east-1/app.tfvars`; jumpbox secret read unconditionally in `networking.tf`; `ALLOW_USER_PASSWORD_AUTH` on the Cognito client.

### 1.2 The workflow is two-phase (FLOW-01, FLOW-02)

Phase 1: PA applies to the Commission, designates a State of Qualifying License (SQL); the SQL verifies eligibility and records the verdict in the system.
Phase 2: PA applies to remote state(s), pays; each remote state issues the privilege.

SOW state portal mapping: the redline response v2 removed "Verify qualifying licenses" from the state list and added the uploads below. The compact rules still require the SQL's review (R3r §3.4(b)), so Phase 1 stays L-05; "Issue compact privileges" = Phase 2 (P-03). How a state upload sits beside the review is open: `product/context/evidence/tensions/TENSION-04-state-upload-versus-multi-party-record.md`.

**SOW §2.1 → ticket traceability (redline response v2).** Every bullet has an owning ticket or a §5.2 candidate row. "v2" marks a bullet the redline response v2 added or changed.

| SOW §2.1 capability | Ticket(s) | Smallest satisfying form |
|---|---|---|
| PA: portal authentication | U-01 | Cognito self-signup + TOTP |
| PA: submit required information and documentation | U-03, L-03, F-12 | Uniform data set + attestations + sworn statement + supporting documents (proof of SQL basis per R2r §2.1(c); remote-state proofs per R3r §3.4(c)(3)–(6)). Q-07 sets which are required vs optional. The PA still submits the qualifying license in L-03; the SOW no longer lists that step, the rules require it |
| PA: apply for compact privileges online | P-01 | |
| PA: verify military affiliation (v2) | candidate U-04 (§5.2) | Not scheduled: the SOW does not say what the verification is for (Q-23) |
| PA: pay application fees | P-02 | Card via Authorize.net Accept UI lightbox |
| PA: track application status | L-04 | Dashboard with status timeline |
| PA: receive notifications regarding privilege processing | F-11 | Email only |
| PA: receive confirmation of timely privilege issuance (v2: "timely") | F-11 + L-04 | Email + privilege card; time-to-issue measured against the 72-hour target (Q-15) |
| PA: receive renewal notifications | A-04 | Expiry notice job |
| PA: renew privileges (v2) | A-05 | Renewal on the same privilege number after the SQL's continued-eligibility check |
| PA: view state practice requirements | S-01 + P-01 | Per-state URL or uploaded document, shown in the P-01 state panel and on `/public/states` |
| State: portal authentication | U-01 (staff entry) + F-04 | Admin-created Cognito users via CLI; `state_admin` role exists, its self-service UI is deferred |
| State: upload PA identifying information and licensure data (v2) | L-02 | CSV upload with validation, preview, and error report, built on mock data; writes license records (TENSION-04 default) |
| State: verify completion of jurisprudence exam requirements (v2) | P-03 + S-01 | The remote state marks each configured proof verified on the case view before issuing |
| State: receive notifications of compact privilege requests (v2) | F-11 + P-02 | `privilege.requested` → the remote state's ops list |
| State: issue compact privileges | P-03 | |
| State: view privilege issuance, renewal, and expiration data (v2) | D-01 + C-02 + A-05 | Search filters and the privileges export, with renewal dates once A-05 lands |
| State: upload state licensing administrator contact information (v2) | S-01 | Contact fields on the state settings form |
| State: view contact information for other member states (v2) | S-01 | Read-only directory for state and Commission users |
| State: access practitioner records | D-01 | |
| State: upload state practice requirements (v2) | S-01 | URL or one uploaded document per state; the hosted editor stays deferred (§5.1) |
| State: access state financial transactions (v2) | C-02 | Own-state transactions page and export |
| State: verify the existence of significant investigatory and disciplinary information (v2) | L-05 + D-01 + A-02 | Shown on the SQL case view and the practitioner record |
| State: update license or privilege status | A-01 | |
| State: notify member states of license status changes, including adverse action and SII (v2) | A-01 + A-02 + F-11 | Event-driven notices; recipient breadth per Q-20 |
| State: upload disciplinary information | A-02 | Structured report (summary + NPDB category per the Nov 10 2025 amendment); optional attachment via F-12 |
| State: upload the uniform data set via API (v2) | L-02 | The same ingestion specification over an authenticated API, proven on mock data; connecting a real state system is out of scope (SOW §2.3) |
| Commission: portal authentication | F-04 | |
| Commission: dashboards | C-01 | Five tiles |
| Commission: basic operational reports | C-02 | CSV exports |
| Commission: integrate with national credentialing organizations (v2; was "Out of Scope") | N-01 | NCCPA certification lookup behind a provider protocol; the real adapter waits on the NCCPA contract (Q-24) |
| Commission: payment reconciliation and financial reporting to member state administrators (v2; was "Out of Scope") | C-02 | Per-privilege payment verification report and per-state remittance summary, from processor-approved transactions. Settlement status stays deferred (§5.1); SOW §7.4 still says Focus is not responsible for reconciliation or settlement (Q-26) |
| Public verification of active and inactive privileges (v2: "and inactive") | V-01 | Inactive privileges returned with status and dates, never the reason |

SOW §2.3 and §3 items outside §2.1: live operations test (H-04); pilot readiness playbook and engagement with up to two candidate states (X-05); MVP completion certification and the Final Review Period (X-06); multi-format state data ingestion validated on mock data (L-02); a rough estimate per functionality and notice when one runs over (§0, §5).

### 1.3 Rule-derived invariants → acceptance criteria

| Rule | Invariant | Ticket |
|---|---|---|
| ML §4.B, R3r §3.5(a) | Privilege expiration = QL expiration as of the request; QL renewal does not extend it | P-03 |
| R3r §3.5(b) | Commission emails PA ≥60 days before privilege expiry | A-04 |
| R3r §3.5(c) | QL "active" past expiry keeps privileges active until the SQL updates it | A-01 |
| R3r §3.6 | Application withdrawn if incomplete 60 days after opened; unpaid privilege request abandoned on the same clock | L-06 |
| R3r §3.4(c)(3)–(6), §3.7(a) | Remote state may require proof (compliance, supervision agreement, prescriptive authority, jurisprudence) before issuance; each is `none \| attestation \| proof_upload` per state | S-01, P-01, F-12 |
| R2r §2.1(c) | PA submits proof of the SQL basis "as determined by the Commission"; the Commission may require more at any time | L-03, F-12 |
| R3r §3.8(a)–(b) | Denial or withdrawal is appealable with the SQL within 30 days of notice (confirm wording survived the redline before it goes in copy) | L-05, L-06 |
| ML §4.B, §6.G | QL adverse action deactivates all privileges; no auto-reinstatement; 2-year bar | A-02 |
| R3r §3.8(b) | Eligibility withdrawn → all privileges cancelled, PA emailed | L-06 |
| R5 §5.5(b) | Public data = name + states holding QL/privileges (plus what Q-12 allows) | V-01 |
| R5 §5.5(c), ML §8.C | SII visible only to state/commission users | A-02, D-01 |
| R5 §5.2(g) | Never store criminal background check results | L-05 |
| R5 §5.3(e) | History of every address/email change; keep every attestation, every state verification document, and NCCPA evidence | F-05, U-03, F-12 |
| R2r §2.1(b) | PA reports a primary-residence change within 30 days | U-03 |
| R3 §3.3(a)(5) | Unique identifier is SSN; system may map to an internal ID | F-02 |
| R5 §5.4 as amended Nov 10 2025 | Adverse action = summary + NPDB category (not documents); 5-day window, 1 business day if summary/emergency. `ATOM-GOV-R5-05` carries the pre-amendment 10-day text; the amendment is in the Nov 10 minutes L230–231 | A-02 |
| ML §2.P | Title-agnostic copy ("physician assistant"/"associate") | F-06 |

UI terms: **Compact Privilege**, **Qualifying License**, **State of Qualifying License (SQL)**, **Remote State**, **Participating State**, **Adverse Action**, **Significant Investigative Information (SII)**. See `glossary.md`.

---

## 2. Decisions

### 2.1 Architecture decisions (ADR each; Sprints 1–2)

| # | Decision | Default | Why |
|---|---|---|---|
| D1 | Data model | Relational, PA-only; status **computed on read**; `*_history` tables with previous/updated/removed | CompactConnect lesson: stored status drifts; expiry needs no job |
| D2 | **Event-driven core** | `domain_events` table written in the same transaction as every state change (transactional outbox); idempotent handlers do notifications, cascades, metrics. No side effects inside requests | Decouples features: a ticket adds a producer or a consumer, never both sides of someone else's flow |
| D3 | API | REST by persona (`/api/v1/me`, `/public`, `/states/{st}`, `/commission`, `/admin`); **guardrails only** — the auth dependency, one success and one error envelope, pagination/sort conventions, a required permission annotation, OpenAPI generated from code with a drift check, TS client + MSW regenerated by one command. Each vertical defines its own endpoints | v4.2: engineers building a vertical own its contract; the platform makes conformance automatic rather than pre-specifying routes |
| D4 | AuthN | Second Cognito pool for PAs (self-signup, email verification); staff pool stays admin-create; **TOTP MFA required for all users** | Decided |
| D5 | AuthZ | Roles `licensee`, `state_staff`, `state_admin`, `compact_admin`, `admin`; per-state permissions `read_private`, `read_ssn`, `write`, `admin`; FastAPI dependency reading permissions from the DB per request — no Redis cache at pilot scale | CompactConnect permission model on the existing CHECK. The `state_admin` role and its own-state scoping ship in F-04 so pilot states can configure their own settings (S-01); the self-service *user-management UI* is deferred in favour of the F-04 CLI (§5.1). ADR-0004's Redis cache superseded |
| D6 | Payments | **Authorize.net**, **Accept UI lightbox** (SAQ A, CompactConnect parity), behind a `PaymentProvider` protocol; `FakeProvider` locally; **card only**. ACH is post-pilot (§5.1) | Commission selects the processor (RFP Q&A 44.1) and is merchant of record (SOW §7.4). The lightbox is a third-party form; its accessibility is documented as a known exception in H-01 (Q-02b confirms) |
| D7 | Email | SES; templates in repo; sent only by the dispatcher from `notifications` rows; **maildev** locally | Idempotent, inspectable |
| D8 | Worker/jobs | One ECS service running the outbox dispatcher loop (`SELECT … FOR UPDATE SKIP LOCKED`) + EventBridge Scheduler → ECS run-task for cron jobs, same image (`python -m licensing_api.worker`, `python -m licensing_api.jobs run <name>`); `WORKER_MODE=inline` in dev/test | No new runtime; email, cascades, and expiry never run inside a request. Kept in scope on CTO review |
| D9 | Documents | S3 presigned upload/download + GuardDuty malware scan; **RustFS** locally (S3-compatible); one `documents` table with a polymorphic owner (application, privilege request, adverse action, practitioner) | Rules require proof from the PA (R2r §2.1(c); R3r §3.4(c)(3)–(6)) and retention of state verification documents and NCCPA evidence (R5 §5.3(e)(4)–(5)); which documents are *required* at pilot is Q-07, but the upload path itself is not optional |
| D10 | SSN | Separate table, pgcrypto with KMS-wrapped key, last-4 elsewhere, full read needs `read_ssn` + audit | Rule names SSN as identifier |
| D11 | UI | Next.js static export; USWDS via trussworks with theme-token overrides; i18n from day one (en); MSW for mocks | In repo already |
| D12 | Environments | `dev` (merge → deploy), `test` (tag → deploy), `prod` (tag + approval); one Terraform, per-env tfvars; plan on PR / apply on merge | QASP: dev/test/prod, one-command deploy; `test` is the SOW §4.2 demo environment |
| D13 | Local dev | `docker compose up` gives Postgres, maildev, RustFS, cognito-local; `PAYMENT_PROVIDER=fake`; seed script | Every ticket testable offline. v4: no Redis |
| D14 | Open source & CI | Public repo under a Commission GitHub org from Sprint 1 (Q-01) → free Actions minutes, CodeQL, secret scanning, Dependabot | SOW §4.2, §5.1, §7.5; security scans day one at zero cost |
| D15 | SQL → PA information requests | **Note + resubmit.** "Request information" stores a `request_note` on the application, flips it to `info_requested`, and emails the PA a link; the PA edits the application (including adding documents via F-12) and resubmits (back to `submitted`). Every note and resubmission is in history. No message thread, no remote-state requests at pilot | Satisfies R3r §3.4(a)(4) with zero new tables. The thread (v3 D15) is the §5.1 fallback if usability round 2 shows note + resubmit fails |

### 2.2 Local-dev fakes (F-14) — what each ticket can assume

| Concern | Local | Test/Prod | Switch |
|---|---|---|---|
| Email | maildev (SMTP :1025, web UI :1080) | SES | `EMAIL_BACKEND=smtp \| ses \| console` |
| Object storage | RustFS (S3 API) | S3 | `S3_ENDPOINT_URL` |
| Malware scan | `scan_status=clean` immediately | GuardDuty | `DOCUMENT_SCAN=none \| guardduty` |
| Identity | cognito-local (JWKS + hosted-UI-less SRP) or `AUTH_MODE=local` dev JWT issuer using the test RSA keypair already in `tests/conftest.py` | Cognito | `AUTH_MODE` |
| Payments | `FakeProvider` (amount cents `.00` approve / `.99` decline; posts the real webhook shape) | Authorize.net sandbox → live | `PAYMENT_PROVIDER=fake \| authorizenet` |
| Worker | inline after each request | ECS service | `WORKER_MODE=inline \| service` |
| Scheduler | `just job <name>` | EventBridge → ECS run-task | — |
| National credentialing (NCCPA) | `FakeProvider` (certification numbers ending `0` active / `9` lapsed) | NCCPA API once the contract is signed (Q-24); fake in `test` until then | `CREDENTIALING_PROVIDER=fake \| nccpa` |

### 2.3 Design workflow (applies to every UI ticket)

1. **Wireframe (product/design, before the ticket starts):** lo-fi black-and-white flow for the whole ticket — screens, fields, states, primary action per screen. Attached to the ticket; reviewed with the PO. Tools: Claude Design in lo-fi mode, or Excalidraw. Reference the CompactConnect screenshot/component named in the ticket.
2. **Hi-fi (engineer):** run Claude Design with the project system prompt (X-01) + the wireframe → comp using the USWDS token set and only components in the library.
3. **Implement:** trussworks components + `client/src/components` primitives; Storybook story per screen state; MSW handlers from the API contract.
4. **Check:** pa11y + axe in CI; PO reviews in DEV; usability round feeds a follow-up ticket if needed.

X-01 must land before any UI ticket: it produces the token overrides, the component library in Storybook, and the Claude Design system prompt.

### 2.4 Roles and what each can do (F-04 contract)

| Capability | `licensee` (PA) | `state_staff` | `state_admin` | `compact_admin` | `admin` (system) |
|---|---|---|---|---|---|
| Register, manage own profile, apply, pay | own | — | — | — | — |
| See own applications, privileges | own | — | — | — | — |
| Enter / update qualifying license records | — | own state (`write`) | own state | — | — |
| SQL eligibility verification (decide, request info, withdraw) | — | own state (`write`) | own state | — | — |
| Remote-state issuance (issue, deny) | — | own state (`write`) | own state | — | — |
| Report adverse action / SII, lift | — | own state (`write`) | own state | — | — |
| Update license / privilege status | — | own state (`write`) | own state | — | — |
| Upload licensee data by file or API (L-02) | — | own state (`write`); API by a machine credential scoped to one state | own state | — | — |
| View other member states' administrator contacts | — | all | all | all | all |
| Search practitioners | — | PAs with QL, request or privilege in own state (R5 §5.6(a)) | same | all | all |
| View private fields (DOB, address, last-4) | own | `read_private` | `read_private` | yes | yes |
| Reveal full SSN (audited) | — | `read_ssn` | `read_ssn` | `read_ssn` | — |
| See SII | — | yes (own scope) | yes | yes | yes |
| Create / deactivate staff users, grant permissions | — | — | own state, **via CLI at pilot** (F-04) | any, via CLI | any, via CLI |
| Configure own state (fees, proofs, lists, administrator contacts, practice-requirements URL or document) | — | — | own state | any | any |
| Configure compact (fees, live states, report lists) | — | — | — | yes | yes |
| Deactivate a privilege with note (override) | — | — | — | yes | yes |
| Dashboard, reports | — | own-state reports | own-state reports | all | all |
| Audit log | — | — | — | read | read |

`read_general` is implicit for all staff. `write`/`admin` are per state; a user can hold permissions in more than one state. `admin` is Focus during the PoP, then Commission IT. The `state_admin` role, its permission scoping, and own-state configuration ship in F-04/S-01; only the self-service **user-management UI** is deferred (§5.1) — at pilot, user creation and permission grants are done with the F-04 CLI by whoever holds `admin` on the state.

---

## 3. Order of work

### 3.1 Bottlenecks and how to defuse them

| Bottleneck | Blocks | Mitigation |
|---|---|---|
| F-02 data model | all features | Sprint 1; data dictionary + migrations + models, no logic; expand/contract migrations so amendments are cheap. SOW Phase 1 names "canonical data model definition" as a Phase 1 output |
| F-05 events/outbox | all cascades, all notifications | Ship with F-02 in Sprint 1; a producer/consumer pair with tests is the template every later ticket copies |
| F-03 API guardrails | all verticals | Auth dependency, envelopes, and the generate-client command land in Sprint 1; each vertical adds its own routes and gets OpenAPI, client, and mocks regenerated for free |
| F-04 RBAC | every state/commission endpoint | Permission matrix as data, DB read per request, no cache |
| P-02 Authorize.net account | end-to-end demo | `FakeProvider` first; adapter second; sandbox creds requested in Sprint 1 (Q-02) |
| X-01 design system | every UI ticket | Sprint 1, product/design + engineer B |
| One reviewer | throughput | Contract tickets get careful review; feature tickets lean on `/code-review` + skim; PRs ≤600 lines |
| Client decisions | see §6 | Each has a default. SOW §8.5.2 gives the Commission 5 business days for prioritisation, policy clarifications, and acceptance (was 2 and 3). The earlier SOW's sentence letting Focus proceed on reasonable assumptions after the window was removed; a late decision is now notified and logged (§8.5.1) and settled by schedule adjustment, reprioritisation, or change request. Building to a default before the answer is at Focus's risk of rework (§7 risk 12) |
| NCCPA contract and API documentation | N-01 | `FakeProvider` first; adapter second; contract started in Sprint 1 (Q-24) |
| Two representative states and their data structures | L-02 | Named by the Commission in Sprint 1 (Q-25); mock data and the ingestion specification are the product ticket's output by Sprint 3 |
| Phase 1 is short | everything | Two sprints hold 20 of the 63.75 nominal days while workshops and research run in parallel; engineers keep heads-down time in Phase 1, the PM/UX carry the workshops |

### 3.2 Critical path (must, one engineer)

```
F-01 → F-14 → F-02 → F-05 → F-03 → F-04 → F-06 → U-01 → L-01 → L-03 → L-05 → P-02 → P-01 → P-03 → A-01 → A-02 → D-01 → V-01 → C-01 → C-02
      (F-07, F-08, F-09 in Sprints 1–2; F-10 after F-09; F-11, F-13 with F-05; S-01, S-03, F-12 before L-03; L-04, L-06, A-04 off the path;
       v5 `should` tickets off the path: L-02 after L-01, A-05 after A-04, N-01 after U-03)
```

### 3.3 Sprint plan — pilot-first ordering, aligned to SOW §3 phases

| Sprint | SOW phase | Lane A | Lane B | Product / design / PM | Prod milestone |
|---|---|---|---|---|---|
| **1** | 1 Discovery & Foundations | F-01, F-14, F-02, F-05 | X-01, F-07, F-03, F-09 | §6 questions issued; ADRs D1–D15; GitHub org + public repo; Authorize.net sandbox request; research plan draft; wireframes: registration, TOTP, PA dashboard, profile | `test` env exists; first sprint demo runs in `test` |
| **2** | 1 | F-13, F-04, F-11, F-08, H-05 | F-06, F-10 | Research plan delivered (QASP); wireframes: application wizard, SQL review queue + case view, compact settings | **`prod` env exists, empty, monitored** |
| **3** | 2 Core Development | F-12, S-03, S-01, L-01 | U-01, U-03, L-03 | Wireframes: privilege application, RS issuance; usability round 1 recruiting | First release tag to prod (`v0.1.0`) |
| **4** | 2 | L-05, P-02 (fake + adapter), L-02 begins (on the mock data) | L-04, P-01 (on the contract; integrates when P-02 merges) | **Usability round 1** (PA registration + application); wireframes: adverse action, status updates, practitioner search, public verify, renewal | SQL verdict recorded end to end in `test` |
| **5** | 2 | P-03, L-06, L-02 | V-01, D-01 (adverse-action section lands with A-02) | **Usability round 2** (state portals: L-05, P-03, the L-02 upload); wireframes: dashboard, reports | **Privilege issued end to end in prod (test data)** |
| **6** | 2 | A-01, A-02, A-04, A-05 | C-01, C-02, N-01 | Usability follow-up tickets; candidate-state sessions for the playbook (X-05) | **every scheduled SOW §2.1 capability exists in `test`** |
| **7** | 3 Hardening & Pilot Readiness | H-02 + UAT fixes | H-01 + UAT fixes | **Usability round 3** (commission + public); UAT (the SOW's "beta testing") begins; playbook draft | UAT in `test` |
| **8** | 3 | H-04 + UAT fixes | H-03 + UAT fixes | Transition docs; playbook delivered (X-05); MVP completion certified (X-06) | **Live operations test passed in the pilot environment; Final Review Period begins** |

Within a sprint, a ticket that depends on a same-sprint ticket in the other lane starts against the F-03 contract and the H-05 seed and integrates when the dependency merges (L-03/F-12 in Sprint 3 — lane A does F-12 first; P-01/P-02 in Sprint 4; D-01/P-03 in Sprint 5). The Jira schedule regroups these by epic and by journey; it is the one the team runs.

Capacity: ticket sizes total **63.75 nominal engineer-days** (must 56.25, rule 1, should 6.5), up from 55.5 in v4.3 after the SOW redline response v2 (v3 was 67). SOW §6.1's FTE table gives 136 nominal engineer-days (36 in Phase 1, 80 in Phase 2, 20 in Phase 3); §6.2 prices 1,006 engineer-hours ≈ 126 days. At ~60% heads-down that is ~80 days. Load by phase: 20 / 36 / 7.75. Phase 2 now carries roughly 25% of its heads-down capacity as slack, down from 40%. That slack is still where usability follow-ups, rule changes (Q-16), and any §5.1 or §5.2 item the Commission pulls in will land, and it backs the Sprint 5 end-to-end milestone against the sandbox-credential dependency (Q-02). SOW §3 asks Focus to give the Commission a rough estimate per functionality and to say when one is running over: the sizes in §5 are those estimates, and the 6.5 `should` days are the ones to offer when something has to give.

---

## 4. Tickets

Common acceptance criteria on every ticket (not repeated): 100% coverage enforced (engineering constitution; SOW §5.2 floor is 90%); 0 lint errors/warnings against the GSA 18F Front-End Guide (SOW §5.2); pa11y + axe clean on new screens; OpenAPI updated + TS client regenerated on API change; migrations forward-only; audit + history rows on every mutation; domain event emitted for every state change and listed in `docs/events.md` (FLOW-07); runs against the local stack with no AWS; docstrings/JSDoc; docs updated in the same PR (SOW §5.2: documentation "complete and current at each sprint").

Format: size · tier · lane · depends → blocks.

---

### Epic F — Foundation and contracts

#### F-01 · Repo truth-up and known-bug sweep

**1d · must · A · — → all**
Rewrite `AGENTS.md` for FastAPI/SQLModel/yoyo and the `engineering/{api,client,infrastructure}` layout; fix root README; delete stale `__pycache__` dirs; fix `DB_USERNAME`→`DB_USER`, set `CORS_ORIGINS`, fix `CurrentUser`, initialise i18n, fix Dependabot directories, move DB password to Secrets Manager and rotate, make jumpbox rule conditional, remove `ALLOW_USER_PASSWORD_AUTH`; remove the ElastiCache module and its security-group/parameter wiring (nothing uses Redis after D5/D8); replace the current `LICENSE` (MIT © Focus Consulting) with the licence and copyright holder decided in Q-01 — SOW §7.5 makes the Commission the owner.
AC: `just lint && just test`, `pnpm lint && pnpm test` green; `/api/me` works on DEV; AGENTS.md is accurate; DEV applies cleanly without Redis.

#### F-14 · Local development stack and fakes

**1.5d · must · A · F-01 → every ticket**
docker-compose: Postgres, maildev, RustFS (bucket auto-created), cognito-local (or `AUTH_MODE=local` issuer — pick whichever gets a working login in <1 day); env switches from §2.2; `just up`, `just seed`, `just job <name>`; `client` proxies to local API; Playwright can run against it; README "run the whole system locally in 5 minutes".
AC: fresh clone → `just up` → register a PA, log in, receive the welcome email in maildev, upload a file to RustFS, complete a fake payment — all with no AWS credentials.

#### F-02 · Canonical data model v1 `CONTRACT`

**1.5d · must · A · F-01 → all**
Tables (PA-only): `states` (code, name, `is_member`, `effective_date`, `is_live`, privilege fee, per-state proof requirements — jurisprudence, supervision/collaborative agreement, prescriptive authority, other compliance — each `none | attestation | proof_upload` (S-01), practice-requirements URL, ops/adverse-action/report distribution lists); `practitioners` (uniform data set per R5 §5.3(c): names + other names, sex, dob, npi, address, phone, email, education program/year, NCCPA cert no/status/expiry, sql_state_code, user_id; provenance per field group — `entered_by`, `verified_by_state`, `verified_at` — so the SQL's confirmation in L-05 is its R5 §5.3(c) submission and L-04 can show "Verified by {state} on {date}"; see `SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance`); `practitioner_ssn` (encrypted, last4); `qualifying_licenses` (state, number, state_reported_status, issue/expiry, unrestricted, `source` = `manual | upload | api`, verified_by/at); `ingestion_batches` (state, route, actor, counts, rejects; L-02); `participation_applications` (status enum per FLOW-06, opened_at, decided_by/at, denial_reason, license_verified_at, cbc_completed_at, attestations JSONB, sql_basis incl. service-member basis, request_note); `privilege_requests` (application, remote_state, status, submitted/decided, denial_reason); `privileges` (number, issued_at, expiration_date pinned, administrator_status, deactivation_reason); `adverse_actions` (against, target, state, type, npdb_category[], summary, order_date, effective_start/end, is_public, is_emergency, sii flag + contact); `documents` (owner type/id, kind, s3_key, scan_status, uploaded_by); `fees` (state nullable, fee_type, amount_cents, effective_from); `transactions` + `transaction_line_items` (state-tagged); `notifications`; `domain_events` (F-05); `*_history` for practitioners, qualifying_licenses, participation_applications, privileges; `audit_log`. Extend `users` with the `state_admin` role in the CHECK and `permissions JSONB`. SQL views `v_qualifying_license_status`, `v_privilege_status`. `docs/data-model.md` data dictionary. ADRs D1, D10. v5 additions: `renewal_checks`, `privileges.renewed_at`, and `fee_type=renewal` (A-05); a credentialing source and `fetched_at` beside the PA-entered NCCPA fields (N-01); a per-proof `verified_by`/`verified_at` on privilege-request proofs (P-03); administrator contacts and a practice-requirements document reference on `states` (S-01). The deferred `case_messages` table is named in the dictionary as reserved, not created. Ownership after landing: the shared roots (`states`, `users`, `practitioners`, `practitioner_ssn`, `documents`, `notifications`, `domain_events`, `audit_log`) stay with the platform; every other table is owned by the vertical the dictionary names, which amends it by forward-only migration without approval.
AC: migrations apply on empty and current DEV DBs; every table has created/updated by/at; status views pass a fixture matrix (active, expired, encumbered, deactivated per reason, within-2-year-bar, R3r §3.5(c) grace); dictionary reviewed by tech lead + PM.
Refs: CompactConnect `cc_common/data_model/schema/{provider,license,privilege,adverse_action}/record.py`; `ATOM-GOV-R5-02`, `-03`, `-04`.

#### F-05 · Domain events, transactional outbox, history and audit `CONTRACT`

**1.5d · must · A · F-02 → all mutating tickets, F-11, F-13**
`domain_events` (id, type, aggregate type/id, payload, actor, request_id, occurred_at, handled_at per handler); `emit(event)` callable only inside a repo transaction; `history.write(entity, previous, updated, removed, effective_at)`; `audit.write(actor, action, entity, before/after)`; handler registry with idempotency on `(event_id, handler)` and dead-letter after N failures; dispatcher loop with `SELECT … FOR UPDATE SKIP LOCKED` run by the Worker (F-13, D8), `WORKER_MODE=inline` for dev/test; commission-only `GET /commission/audit`; event catalogue file (`docs/events.md`, seeded from FLOW-07 minus the §5.1 deferrals) with a test that every type in the catalogue has ≥1 test. ADR D2.
AC: a mutation without an event fails a test; a handler that throws is retried then dead-lettered with an alarm; replaying an event is a no-op; history row is in the same transaction as the change; two Worker tasks never double-handle an event.

#### F-03 · API guardrails and client generation `CONTRACT`

**1d · must · B · F-02 → all verticals**
Not a contract for the endpoints — each vertical owns its routes and models. This ticket fixes what every route must conform to: persona namespaces and which roles reach which; the auth dependency every route uses (consumed by F-04); one success envelope, one error envelope `{code, details[]}`, one pagination/sort convention; a permission annotation required on every route and checked by a test; OpenAPI generated from code with a drift check in CI; TS client (`openapi-typescript`) on the existing `authFetch` and MSW handlers regenerated by one command; one worked example route (`/api/me`) showing the pattern. ADR D3.
AC: a route without a permission annotation fails a test; a route returning a non-envelope shape fails a test; CI fails on spec drift; one command regenerates client and mocks; Storybook renders a page against MSW with no API.

#### F-04 · Roles, state-scoped permissions, MFA policy, staff provisioning `CONTRACT`

**1.5d · must · A · F-02 → S-01, L-01, L-05, P-03, A-*, D-01, C-***
`require(...)` dependency; permission matrix as data mirroring CompactConnect (compact `admin`; state `read_private|read_ssn|write|admin`; `read_general` implicit for staff); roles `licensee|state_staff|state_admin|compact_admin|admin`; "is my state the SQL for this PA" and "is my state a remote state for this PA" resolved separately (signal: the SQL is the sole eligibility authority); licensee endpoints scoped to `claims.sub`; permissions read from `users` per request; TOTP MFA enforced in both Cognito pools (Terraform) and asserted in the token (`amr`) by the API; `/api/me` returns effective permissions; **staff provisioning CLI** `just staff create|permit|deactivate` (Cognito `admin_create_user` + invite email + TOTP on first login) — runnable by `admin`/`compact_admin` for any state and by a `state_admin` for their own state (same scoping rule the deferred UI will use, §5.1). ADRs D4, D5.
AC: table-driven role × endpoint test; permission change effective on next request; token without MFA claim → 401; deactivated user → 403 next request; a `state_admin` CLI call outside their state is refused.

#### F-06 · App shell, design tokens, navigation

**2d · must · B · F-03, X-01 → every UI ticket**
USWDS `GovBanner`, header + logo, per-persona side nav from `/api/me`, footer/identifier, skip link; `_uswds-theme.scss` overrides from X-01; primitives (PageHeading, StatusTag for all enums, EmptyState, ConfirmModal, DataTable, StepIndicator, AlertBanner, CaseLayout for review screens); i18n namespaces; title-agnostic copy (ML §2.P); Storybook deployed to a static path on DEV.
AC: three persona navs render from mocked permissions; Lighthouse a11y 100; tokens documented.
Design: wireframe = nav/IA only. Refs: CompactConnect `webroot/src/components/Page/*`, `staff-user-documentation/images/*.png`.

#### F-07 · Quality gates

**1.5d · must · B · F-01 → H-01**
Codecov enforced 100% for `api`/`client` with documented exclusions (migrations, generated client, IaC); ESLint/Prettier/Stylelint configured to the GSA 18F Front-End Guide (SOW §5.2 "Properly Styled Code") with 0 warnings; pa11y-ci over Storybook + Playwright page list; axe in Vitest; Playwright e2e skeleton against the F-14 stack in CI; pre-commit; `just check` / `pnpm check`.
AC: coverage drop fails PR; a lint warning fails PR; contrast violation fails CI; e2e smoke <5 min.

#### F-08 · Security scanning

**1d · must · A · F-01 → H-02**
CodeQL (py, ts — covers what Semgrep/Bandit would add), `pip-audit`, `pnpm audit --prod`, Trivy on the image, Checkov on Terraform, gitleaks (exists), Dependabot fixed, secret scanning + push protection on the repo, SBOM (CycloneDX) per build feeding the dependency-licence inventory (SOW §5.2 Documentation; RFP Q&A 27.1), ZAP baseline nightly against DEV with authenticated context (adapt CompactConnect `owasp-zap/`), SARIF to GitHub Security, `SECURITY.md`, false-positive register. The SBOM also feeds a **third-party materials register**: SOW §7.5 says Focus shall not embed or deliver third-party materials, open-source components included, without the Commission's prior written consent, so the register is what the Commission consents to and what a new dependency is added to before it merges (Q-28).
AC: PR blocked on high/critical; ZAP report attached nightly; all of it runs on the free tier of a public repo (Q-01) — if the repo must stay private, the ticket documents the GHAS cost.

#### F-09 · Environments and Terraform CI

**2d · must · B · F-01 → F-10, H-04**
`test` and `prod` tfvars/backends; plan on PR (commented), apply on merge for `dev`, tag-driven promote to `test` (`v*-rc`) and `prod` (`v*`, environment protection + approval); `just deploy <env>`; bootstrap runbook; immutable ECR tags + lifecycle; drop `:latest`. `test` is the live demo environment for every sprint review (SOW §4.2) and must exist by the end of Sprint 1.
AC: fresh AWS account → running `test` stack from the runbook; one tag deploys to prod.

#### F-10 · Infrastructure security baseline

**1.5d · must · B · F-09 → H-04**
WAF on CloudFront (managed rules + rate limits on `/api/public/*` and auth); response headers policy (CSP, HSTS, XFO, Referrer-Policy); HTTPS CloudFront→ALB; RDS deletion protection, final snapshot, backups (7d test / 35d prod); KMS CMK; CloudTrail + GuardDuty (with S3 Malware Protection on the documents bucket); ASVS 5.0 mapping doc (SOW §5.2, QASP "Secure Code"; the earlier SOW said 3.0). **United States only** (SOW §2): every region, backup, log destination, and third-party service keeps software and Commission data on servers in the United States; CloudFront is geo-restricted and its price class set accordingly, and anything that cannot be confined is listed for the Commission (Q-28). Not at pilot: Cognito advanced security (paid tier), ElastiCache hardening (removed in F-01).
AC: Checkov clean; A on securityheaders.com; `docs/security/asvs-mapping.md` against ASVS 5.0; a Checkov or policy test fails on a non-US region.

#### F-11 · Notifications `CONTRACT`

**1.5d · must · A · F-05 → every notifying ticket**
`notify(template, recipient, ctx, idempotency_key)` writes a `notifications` row; Worker sends via `EMAIL_BACKEND`; SES domain + DKIM/SPF/DMARC in Terraform; Jinja HTML+text base layout with env banner outside prod; catalogue `docs/notifications.md` (event → recipient → template, from FLOW-07); per-state distribution lists on `states`. Recipient rule for adverse actions follows the Q-20 default (states with a QL, request, or privilege for the PA) until the Commission answers.
AC: duplicate idempotency key sends once; templates snapshot-tested; maildev shows mail locally; SES sandbox verified on DEV.

#### F-12 · Document storage

**1d · must · A · F-02, F-14 → L-03, P-01, A-02**
Private bucket (KMS, versioning); presigned POST with size/type limits; presigned GET after permission check (owner scoping follows F-04: the PA for their own, the SQL/RS for their cases, commission for all); GuardDuty scan → `scan_status`, downloads blocked until clean; RustFS locally; `FilePickerField` wired; `documents` rows are part of the retained record (R5 §5.3(e)(4)). Consumers: L-03 documents step (proof of SQL basis, NCCPA card — Q-07), P-01 per-state proofs where S-01 configures `proof_upload` (R3r §3.4(c)(3)–(6)), A-02 optional attachment, D-01 document list.
AC: 20 MB ok / 21 MB rejected; EICAR blocked in test env; document appears in practitioner history; state A cannot fetch state B's case document.

#### F-13 · Worker service and scheduled jobs

**1d · must · A · F-05 → L-06, A-04**
`python -m licensing_api.worker` dispatcher loop as an ECS service (same image as the API); `licensing_api/jobs/` registry + `python -m licensing_api.jobs run <name>`; EventBridge Scheduler → ECS run-task; job run log; alarms on failure/dead-letter; first jobs: `heartbeat`, `dispatch_events`. ADR D8.
AC: job failure → Slack alarm; jobs idempotent; `freezegun` tests; Worker task count 0 → alarm; dispatcher drains a backlog of 1,000 events in <1 min locally.

---

### Epic U — Identity and users

#### U-01 · PA registration, login with TOTP, password reset

**2d · must · B · F-03, F-06, F-11, F-14 → U-03, L-03**
Second Cognito pool (self-signup, email verification, TOTP required; self-signup is a per-environment Terraform flag, off in `prod` except during the H-04 live operations test; turning it on for real PAs is a launch-runbook step); API maps pool → role; `/register`, TOTP enrolment screen, `/login` per persona entry from a public landing, forgot/reset; registration and reset never reveal whether an email exists (crosswalk §7 item 11); 10-minute idle timeout with a 30-second warning (crosswalk §3.1); `just user reset-mfa <email>` for a lost authenticator after an out-of-band check (self-service recovery deferred, §5.1); first login creates `practitioners` row; WAF rate limit (F-10); emits `practitioner.registered`.
AC: register → verify → enrol TOTP → login → empty dashboard, in Playwright; staff can't use the PA entry and vice versa; existing and new emails get the same registration response; idle session refused after 10 minutes; `reset-mfa` forces re-enrolment; self-signup refused on `prod` while the flag is off.
Design: wireframe = landing (3 cards: PA / state & commission / verify a privilege), register, TOTP, login, reset. Ref: CompactConnect `PublicDashboard`, `RegisterLicensee`.

#### U-03 · PA profile (uniform data set)

**1d · must · B · U-01 → L-03**
`/account`: legal + other names, sex, DOB, NPI, address, phone, email (change with code), NCCPA cert no/status/expiry (PA-entered; N-01 adds the looked-up value beside it), education program/year; consent to service of process by mail at the primary residence (ML §5.A.2) and the 30-day duty to report an address change (R2r §2.1(b)) stated in copy; every address/email change → history row and `practitioner.profile_changed` (R5 §5.3(e)(1)–(2)); a change to a field the SQL has verified keeps `verified_at` and the record shows both (no email to the SQL by default, Q-10; `ATOM-GOV-M0825-02`); staff profile page.
AC: history visible in D-01; a post-verification edit is visible on D-01 with the SQL's stamp intact.
Design: wireframe = one form + read-only summary. Ref: CompactConnect `UserAccount`, `PrivilegePurchaseInformationConfirmation`.

---

### Epic S — Configuration

#### S-01 · Compact and state configuration

**2d · must · A · F-04, F-12 → L-03, L-05, P-01**
Seed all member states with `effective_date` (Q-03); `compact_admin` sets `is_live` (one-way, confirm dialog, crosswalk §4.2); a `state_admin` lands on their own state's form; per-state: privilege fee (versioned `effective_from`), remote-state proofs each as `none | attestation | proof_upload` — jurisprudence (R3r §3.7(a); RFP Q&A 23.1 expects attestation), supervision/collaborative agreement, prescriptive authority, other compliance (R3r §3.4(c)(3)–(6)) — practice requirements as a URL to the board's own page or one uploaded document (SOW §2.1 "view state practice requirements" and, since v2, "upload state practice requirements"; shown in P-01 and on `/public/states`; an uploaded document is public once scanned), ops/adverse-action/report distribution lists, state licensing administrator contacts (name, role, email, phone; SOW §2.1 v2 "upload state licensing administrator contact information"); a read-only **member-state contacts directory** for state and Commission users (SOW §2.1 v2 "view ... contact information for other compact member states"); commission: commission fee (default $0 until Rule 6 / the Finance Committee sets one, Q-05), report recipients; `GET /public/states`. `state_admin` edits their own state; `compact_admin` any (D5).
AC: fee history retained; non-live state not selectable; state admin edits own state only; a state without practice requirements shows "not provided" rather than a broken link; the contacts directory is not reachable by a PA or the public.
Design: wireframe = settings list + state settings form + contacts directory. Ref: `settings_tab.png`, CompactConnect `StateSettingsConfig`.

#### S-03 · Attestations catalogue

**1d · must · A · F-02 → L-03, P-01**
`attestations` (id, version, text, required, applies_to participation|privilege); seed from ML §4.A / Rule 3 (truthfulness, ARC-PA, NCCPA current, no convictions, no controlled-substance action, no current restriction, 2-year bar, not under investigation **in the SQL only** — Feb 9 2026 minutes, comment 8 — and cross-checked against open SII the SQL holds (FLOW-02), will comply with remote-state supervision/prescribing, jurisprudence per state, service of process); applications store `[{id, version, accepted_at}]`; stale version rejected.
Refs: CompactConnect `compact-config/attestations.yml`. Open: Q-06 wording sign-off; Q-16 (misdemeanor-conviction eligibility is on the Mar 9 2026 rules agenda and may change the "no convictions" text).

---

### Epic L — Qualifying license and eligibility (Phase 1)

#### L-01 · Qualifying license records (state entry)

**1.5d · must · A · F-04, F-05 → L-05, A-01**
State `write` users create/update a QL for a practitioner (find-or-create by name+DOB+last4 or NPI): number, state-reported status, issue/expiry, unrestricted, `source=manual` (L-02 writes the same records with `source=upload|api`); computed status; history classifies change (renewal/deactivation/other); emits `qualifying_license.status_changed`; PA sees it on the dashboard.
AC: own-state only; expiry moving later = renewal in history; status flips to inactive the day after expiry with no job (subject to the R3r §3.5(c) grace in A-01).
Design: wireframe = form + license card. Ref: CompactConnect `LicenseCard`. Open: Q-04 and TENSION-04 (how a state upload sits beside PA-entered data).

#### L-02 · State licensee data ingestion (file upload and API)

**3d · should · A · L-01, F-04, F-12 → L-05**
SOW §2.1 (v2) "Upload PA identifying information and licensure data" and "Upload compact uniform data set, as defined by compact policy, via API capability"; SOW §3 Phase 2 "State licensee data ingestion (multi-format: API and upload)". Was "bulk CSV license upload", dropped from v1 as not in the SOW. One ingestion data specification (`docs/ingestion-spec.md`) written against mock data built with the Commission from two or more representative member states, covering where their formats diverge (SOW §3; Q-25). Two routes into one validator and one writer: a CSV upload in the state portal (validate → preview with row-level errors → commit; downloadable error report) and `POST /states/{st}/license-ingestions` (JSON, same schema) with a machine credential scoped to one state, issued and rotated through the F-04 CLI. Rows go through L-01's service as `qualifying_licenses` with `source=upload|api`, find-or-create on the L-01 match keys, with history, audit, and `qualifying_license.status_changed`; each run is an `ingestion_batches` row. Built to the Focus preference in `TENSION-04-state-upload-versus-multi-party-record` until the Commission answers: ingestion writes the state's own license fields only; it does not create PA accounts, gate sign-up, or set eligibility; the SQL's review in L-05 is still the decision; a row that would change the status or expiry of a license behind an active privilege is held for staff confirmation instead of cascading on its own; the specification carries match keys (name, DOB, last-4 or NPI), not the full SSN. Mock data only: no production data from a state (SOW §3) and no connection to a real state system (SOW §2.3). Receiving real member-state data is also what starts the cyber-insurance requirement in SOW §8.6.
AC: the same batch through upload and API produces the same rows; a re-sent batch is a no-op; a malformed row is rejected with its line and reason; state A's credential cannot write state B's records; an ingested license is the on-file record in L-05's claimed-versus-on-file comparison; held changes are listed and applied only on confirm.
Design: wireframe = upload, preview with errors, batch history, held changes. Ref: CompactConnect's bulk upload screen, for the upload step only (crosswalk §2 explains why the rest differs). Open: Q-25, TENSION-04.

#### L-03 · Participation application wizard

**2d · must · B · U-01, U-03, S-03, F-12, F-11 → L-04, L-05**
Steps: intro "what to expect" → confirm profile → designate SQL + basis (R2r §2.1(a): primary residence, ≥25% of practice, employer, tax residence, or service member/spouse retaining primary residence) → qualifying license details (or pick an L-01 record) → documents (proof of SQL basis per R2r §2.1(c), NCCPA evidence per R5 §5.3(e)(5); which are required is Q-07, default all optional) → attestations → CBC acknowledgement → review + sworn statement (R3r §3.4(a)(1)) → submit. Server-side draft saved on every "Continue"; `opened_at` on submit; emits `application.submitted`; PA withdraw emits `application.withdrawn`; when `info_requested`, the wizard reopens with the SQL's `request_note` at the top and "Resubmit" (D15) — the documents step is where the PA answers a request for proof. No fee step at pilot (Q-05; §5.1).
AC: draft survives logout; submit atomic; needs a live SQL; PA can withdraw; resubmit returns status to `submitted` and keeps the note in history; a required-document rule from Q-07 blocks submit with a clear message.
Design: wireframe = every step + review + the resubmit variant. Ref: CompactConnect purchase wizard (`PrivilegePurchase*`), USWDS StepIndicator/ProcessList. Open: Q-04, Q-05, Q-07.

#### L-04 · PA dashboard, status tracking, privilege cards

**1.5d · must · B · L-03 → P-01**
SOW "Track application status", "Receive confirmation of privilege issuance". Cards: SQL block with "Verified by {state} on {date}" + QL card; participation application timeline (submitted → under review → info requested (with the note) → eligible/denied, dates, reason, appeal note); privilege cards (state, number, status, issued, expires, tooltip: expiry tied to QL) with a history timeline from history rows, "Expiring in N days" with a caution icon under 90 days (crosswalk §3.4); one primary CTA with a "Why is this unavailable?" reasons list (application in review, information requested, not yet eligible, two-year bar, eligibility withdrawn; crosswalk §3.3).
AC: reflects DB on load; empty states; timeline from history, not stored events; the reasons list matches the guards in L-03/P-01.
Design: wireframe = dashboard + privilege card/detail. Ref: CompactConnect `LicenseeDashboard`, `HomeStateBlock`, `PrivilegeCard`, `PrivilegeHistory`.

#### L-05 · SQL eligibility verification (state portal)

**1.5d · must · A · L-01, L-03, F-04, F-11 → P-01, L-06**
See FLOW-02 (`product/context/flows/02-sql-eligibility-verification.md`). Queue for my state as SQL (age, 60-day countdown); case view: identity incl. NCCPA status (R5 §5.3(e)(5); PA-entered, with the N-01 lookup beside it and a flag when they differ), claimed vs on-file license diff (the on-file record may be staff-entered in L-01 or ingested by L-02; the case view shows its source), basis + documents, attestations, existing adverse actions/SII; actions: verify license (links/creates L-01 record) and confirm identity — stamps `verified_by_state`/`verified_at` on the identity field groups, the R5 §5.3(c) submission — record CBC completed **date only** (R5 §5.2(g)), attach a verification document via F-12 (retained, R5 §5.3(e)(4)), request information (D15: `request_note` + `info_requested` + `application.info_requested` → PA email with a link, never the note body), decide eligible/deny with reason (enum excludes CHRI, ML §8.B.4); the decision is the R3r §3.4(b)(4) "notice to the Commission through the data system" — emits `application.eligible|denied` → PA email, Commission ops FYI, dashboard; denial email carries the appeal text (30 days with the SQL, R3r §3.8(a); Q-08); `time_to_decision` metric.
AC: only SQL-state `write`; decision requires license verified + CBC completed; verdict immutable except withdraw (L-06); all audited; state A sees nothing of state B's applications.
Design: wireframe = queue + case view with 4-item checklist (basis, license, CBC, attestations), request-note control, and one decision control — **no CompactConnect equivalent; design this first and test it in usability round 2 (Sprint 5).** Open: Q-04, Q-08 (denial reasons).

#### L-06 · Abandonment (applications and unpaid privilege requests) and eligibility withdrawal `rule`

**1d · rule · A · L-05, F-13 → —**
Job `abandon_stale_cases` (R3r §3.6): participation applications 60 days after `opened_at` still `submitted|info_requested` → `withdrawn` + `application.withdrawn`; privilege requests left `pending_payment` 60 days → `abandoned`. SQL action "withdraw eligibility" → `application.eligibility_withdrawn` + all privileges cancelled atomically (`deactivation_reason=eligibility_withdrawn`) + PA email with the 30-day appeal note (R3r §3.8(b)) + RS emails.
AC: cascade atomic; withdrawn PA blocked from P-01; boundary tests with `freezegun` for both clocks.

---

### Epic P — Privilege application, payment, issuance (Phase 2)

#### P-02 · Payment: provider protocol, fake, Authorize.net Accept UI

**1.5d · must · A · F-03, F-05, F-14 → P-01, C-02**
`PaymentProvider` protocol (`create_checkout`, `handle_webhook`, `get_status`); `FakeProvider` (local); **Authorize.net** adapter using **Accept UI lightbox** (D6) — the card form is Authorize.net's iframe on our page, only a token reaches the API; `transactions`/`line_items` (tagged by state + commission fee so the Commission can remit per state, R3r §3.2(a)(3); `refId=transaction_id`) written on the `net.authorize.payment.authcapture.created` webhook; webhook signature (HMAC-SHA512) verification; idempotent on `provider_ref`; `duplicateWindow`; emits `privilege.requested`/`payment.declined`; receipt email; `GET /me/transactions`; credentials in Secrets Manager. Card only; fees are non-refundable (R3r §3.4(c)(4)) so there is no void/refund path. ADR D6.
AC: `PAYMENT_PROVIDER=fake|authorizenet` with no code change; webhook replay idempotent; declined leaves requests `pending_payment`; no card data reaches the API (ZAP + review); the lightbox's accessibility findings are recorded for H-01.
Refs: CompactConnect `purchases/purchase_client.py`, `PrivilegePurchaseAcceptUI.vue`. Open: Q-02, Q-02b.

#### P-01 · Privilege application

**2d · must · B · L-05, S-01, S-03, P-02, F-12 → P-03**
Entry only if participation `eligible` and no 2-year bar (ML §4.A.8); select live remote states (non-live states absent; SQL + states with active privilege disabled; up to 20 per checkout, crosswalk §3.6); per-state panel: fee, each proof the state configured in S-01 as an attestation checkbox or an upload via F-12 (R3r §3.4(c)(3)–(6)), practice-requirements link; server-computed fee summary; privilege attestations; "expires on <QL expiry>" (R3r §3.5(a)) + "fees non-refundable" (R3r §3.4(c)(4)) acknowledgements; checkout via P-02; one `privilege_request` per state.
AC: requests exist only after payment approved; abandoned payment leaves `pending_payment`; total matches server; e2e via FakeProvider.
Design: wireframe = select states, per-state panel, summary, pay, done. Ref: CompactConnect `PrivilegePurchaseSelect`, `SelectedStatePurchaseInformation`, `PrivilegePurchaseFinalize`.

#### P-03 · Remote state issuance (state portal)

**1.75d · must · A · P-01, F-04, F-11 → A-01, D-01, V-01**
See FLOW-03 (`product/context/flows/03-payment-and-remote-state-issuance.md`). Queue for my state (age vs 72h operational target — RFP Q&A 46.1; the SOW no longer states it, Q-15); case view: SQL verdict + date, license, attestations and uploaded proofs per S-01, each with a "verified" control that stamps `verified_by`/`verified_at` (SOW §2.1 v2 "Verify completion of jurisprudence exam requirements"; the same control serves the other three proofs), payment, PA contact (for any off-system question — no in-app request-info at pilot, §5.1); actions: issue (number `PA-{ST}-{n}` per-state sequence, `issued_at`, `expiration_date` = QL expiry snapshot on request), deny with reason; emits `privilege.issued|denied` → PA, SQL ops, Commission ops; `time_to_issue` metric. The privilege row is the remote state's R5 §5.3(d) submission.
AC: cannot issue unless participation `eligible` and transaction `paid` (R3r §3.4(d)), and every proof the state configured as required is marked verified; number unique/monotonic; expiration pinned even if QL renewed after (test).
Design: wireframe = queue + case view (reuse L-05's CaseLayout) with sticky "Issue privilege". No CompactConnect equivalent.

---

### Epic A — Status changes, disciplinary information, expiry

#### A-01 · License and privilege status updates with cascades

**1.5d · must · A · L-01, P-03 → A-02, A-04**
SOW "Update license or privilege status". State actions on a QL: expired/lapsed/inactive/reinstated/terminated with effective date; on a privilege: deactivate with note (issuing state or `compact_admin`); cascade rules as pure functions + matrix (FLOW-05): QL inactive/expired/terminated → privileges inactive (reason); voluntary termination ends all privileges as of the termination date (R2r §2.2(d) as re-worded Feb 9 2026); R3r §3.5(c) grace (QL "active" past expiry stays active until SQL updates); reinstated QL does not reactivate privileges (ML §4.C); emits `qualifying_license.status_changed` / `privilege.deactivated` → notifications to PA and affected states.
AC: cascade matrix ≥8 cases; computed views reflect cascades; history on every affected privilege.
Refs: CompactConnect `deactivate_license_privileges`.

#### A-02 · Adverse actions and SII (disciplinary information)

**1.5d · must · A · A-01, F-12, F-11 → D-01**
SOW "Upload disciplinary information". State reports an adverse action against a QL or a privilege as a **structured record** (R5 §5.4 as amended Nov 10 2025: summary, not document copies): type (CompactConnect `EncumbranceType` enum), NPDB category (multi), summary, order date, effective start, `is_emergency`, `is_public`, optional attachment via F-12 for states that want the order on file; QL → all privileges deactivated atomically (`qualifying_license_adverse_action`, ML §6.G); privilege → that one only; lift with effective end; 2-year bar → `eligible_again_on` enforced in L-03/P-01; **SII** as a flag + contact + brief description on the same form (Nov 10 2025 minutes: "a checkbox … and contact information"), closable, visible only to state/commission users, never emailed to the PA (ML §8.C); events `adverse_action.reported|lifted`, `sii.flagged|closed`; notifications: PA (adverse action only), states per the Q-20 default, Commission (R5 §5.6(b)); `is_public=false` never reaches V-01, shows "confidential — do not redisclose" banner to state users (R5 §5.5(c)).
AC: cascade + 2-year matrix; lifting one of two actions stays encumbered; negative tests prove SII never appears in `licensee`/public responses.
Design: wireframe = report form (modal from license/privilege card), lift, SII flag. Ref: CompactConnect encumber/unencumber modals, `privilege_action_menu.png`.

#### A-04 · Expiry notices and expiry

**0.5d · must · A · P-03, F-13 → —**
SOW "Receive renewal notifications". Job `privilege_expiry_notices` (60/30/7 days; 60 is the R3r §3.5(b) minimum; idempotent per threshold) emitting `privilege.expiring` → PA email "your privilege in KS expires on DATE; renew your qualifying license, then apply again"; job `expire` writes the history row and emits `privilege.expired` (status itself is computed, D1). The renewal flow itself is A-05 (scheduled in v5; it was deferred in v4). A PA whose privilege has already expired applies again through P-01 and receives a new number.
AC: notice once per threshold; `freezegun` boundary tests.

#### A-05 · Privilege renewal

**1.5d · should · A · A-04, L-05, P-01, P-03 → —**
SOW §2.1 (v2) "Renew privileges" for the PA and "View privilege issuance, renewal, and expiration data" for the state. Deferred in v4 because the earlier SOW listed renewal notifications only; see FLOW-04. The PA starts a renewal for one or more privileges once the QL's expiry is later than the privilege's pinned expiry (otherwise "renew your qualifying license first"); the SQL confirms continued eligibility on the L-05 case view with a renewal badge (`renewal_checks`, R3r §3.5(d)); the PA then requests the same remote states through P-01 with `fee_type=renewal` (R3r §3.5(e)); on issue P-03 keeps the privilege number and `issued_at` and sets `renewed_at` and the new pinned expiry; jurisprudence already met may be reused before expiry (R3r §3.7(b)–(c)); events `renewal.requested|eligible|denied` (FLOW-07); "renewed" appears in the history timeline, D-01, and the C-02 privileges export. Check the wording against adopted Rule 3 before building: FLOW-04 carries a needs-review note for these citations.
AC: renewal refused until the QL expiry has moved; number and `issued_at` unchanged after renewal; `freezegun` tests around the expiry boundary; demonstrated on seed data in `test`, since no real privilege nears expiry inside the period of performance.
Design: wireframe = renew action on the privilege card, the SQL renewal check, the remote-state renewal case. Open: Q-05 (renewal fee amounts).

---

### Epic D — Practitioner records

#### D-01 · Practitioner search and detail (state and commission)

**1.5d · must · B · F-04, P-03 → C-01; A-02 adds the adverse-action section**
SOW "Access practitioner records related to compact participation". Search (name, NPI, license no, privilege no, SQL state, privilege state, status, expiring within N days — with the C-02 privileges export this is SOW §2.1 v2 "View privilege issuance, renewal, and expiration data"); scoping: state users see practitioners using their state as SQL or holding a privilege/request there (R5 §5.6(a)); commission sees all; detail: identity (private fields gated by `read_private`), SSN reveal (`read_ssn`, audited with reason), address/email history, QLs, applications (with request notes), privileges with history, adverse actions (with the confidentiality banner when `is_public=false`), SII (state/commission only), documents (F-12, permission-scoped); commission-only privilege deactivation with note (A-01). Any state user can find an adverse-action record through search — this is how the ML §8.D "available to any other Participating State" reading is satisfied under the Q-20 default.
AC: scoping proven (state A can't see an unrelated PA); SSN reveal audited with reason.
Design: wireframe = search, results, detail with sections. Ref: `license_search_tab.png`, `practitioner_details_page.png`, CompactConnect `LicensingDetail`.

---

### Epic C — Commission portal

#### C-01 · Commission dashboard

**1d · must · B · D-01, L-05, P-03 → —**
SOW "Access system dashboards to monitor privilege applications and issuance". Five tiles from SQL views: applications by status (with SQL-state breakdown); privilege requests by status (remote-state breakdown); privileges issued last 30 days; median time-to-issue vs the 72h target; aging queues (>3d requests, >45d applications without CBC); each drills through to D-01.
AC: numbers reconcile with D-01; <2 s on H-05 seed; charts have data tables.
Design: wireframe = tile grid. Follow the `dataviz` skill for chart conventions.

#### C-02 · Operational and financial reports

**1.75d · must · B · P-02, P-03 → —**
SOW "Generate basic operational reports". The redline response v2 moved "Payment reconciliation and financial reporting" out of the old "Out of Scope" list: §2.1 now has "Payment reconciliation and financial reporting to Member State administrators to verify payment for each privilege issued" (Commission) and "Access state financial transactions" (state). CSV exports with date/state filters: privileges issued/renewed/expired/deactivated; applications received/decided + time-to-decision; transactions by state (PA, privilege, amount, provider ref, date — the RFP-02 "track financial transactions with the compact for my state" story, reported from `paid` status); adverse actions reported; report definitions in code with golden-file tests; state users get their state's rows only. v5 adds: an own-state **transactions page** (the same rows on screen, filterable); a **payment verification report** with one row per privilege issued (privilege number, PA, state fee, Commission fee, transaction, provider reference, paid date) so a state administrator can confirm payment behind each privilege; a **remittance summary** per state per period for the Commission. All three report what the processor approved by webhook. SOW §7.4 still says Focus "will not be responsible for financial reconciliation or settlement", so settled-funds status is not shown; the settlement job stays in §5.1 (Q-26).
Refs: CompactConnect `transaction_reporting.py` columns.

---

### Epic V — Public verification

#### V-01 · Public privilege verification

**1.5d · must · B · P-03 → —**
SOW §2.1 (v2: "verify active and inactive PA compact privileges"; it said active only). Default fields per Q-12: name, SQL state, privilege states + number + status + dates; nothing else (R5 §5.5(b)). Inactive privileges (expired, deactivated, encumbered) are returned with the FLOW-06 status vocabulary and never the `deactivation_reason` or the action behind it (FLOW-05). `/verify` search (last+first name, or privilege number exact); results; detail; unauthenticated `/api/v1/public/*` with strict response schemas; WAF rate limit + 429; no enumeration (both names, or an exact number).
AC: schema tests prove no private field can appear; a privilege deactivated by a non-public adverse action shows as inactive with no reason; rate limit works; pa11y clean.
Design: wireframe = search + result + detail. Ref: CompactConnect `PublicLicensingList/Detail`.

---

### Epic N — National credentialing integration

#### N-01 · NCCPA certification status integration

**2d · should · B · U-03, F-13 → L-05**
SOW §2.1 (v2) "Integrate with national credentialing organizations" (Commission portal list; "Out of Scope" in SOW v1.0). `CredentialingProvider` protocol (`lookup(certification_number, identity)` → status, expiry, as-of); `FakeProvider` locally and in `test`; the NCCPA adapter when the contract and API documentation arrive. The Executive Committee minutes of 2026-05-13 record that CSG, NCCPA, and Focus met on 2026-05-11 and that NCCPA's third-party process needs a contract, to be completed once data system development begins (Q-24). Lookup runs when the PA saves a certification number (U-03), when the SQL opens the case (L-05), and on a scheduled refresh for PAs with an open application or an active privilege; the result is stored on the practitioner record with its source and `fetched_at`, beside what the PA entered and not over it; a mismatch is flagged on the L-05 case view; when the provider is unavailable the PA-entered value stands and the case view says so. The rule still has the SQL verify and submit the certification fields (R5 §5.3(c)(10)); the lookup informs that check and does not replace it. Lookup failures appear as a C-02 report column.
AC: `CREDENTIALING_PROVIDER=fake|nccpa` with no code change; a provider timeout blocks neither the profile save nor the SQL decision; lookups are audited; no NCCPA credential in the repo.
Open: Q-24 (contract, API shape, cost, which fields NCCPA returns).

---

### Epic H — Pilot readiness (continuous from Sprint 2; these are the close-out tickets, SOW Phase 3)

#### H-01 · Accessibility audit and remediation (WCAG 2.1 AA)

**2d · must · B · F-07, all UI**
Manual audit per screen (keyboard, NVDA + VoiceOver, 200% zoom, reduced motion, contrast, focus order, error association); fixes to zero; accessibility statement; `docs/accessibility.md`; pa11y-ci over every authenticated route; the payment lightbox exception (Q-02b) documented.
AC: 0 automated, 0 manual findings; test plan + results delivered.

#### H-02 · Security validation (ZAP full + ASVS 5.0)

**2d · must · A · F-08, F-10, all API**
ZAP full active scan with authenticated contexts for all personas against `test`; ASVS 5.0 level 2 walk with evidence (SOW §5.2 now names 5.0; the F-10 mapping is rebuilt against its chapter structure); fix medium/high; false-positive register; licence review of the SBOM and the third-party materials register reconciled with the Commission's consent (SOW §7.5, Q-28); secrets rotation drill; Cognito review.
AC: clean report (no medium/high); security scan report delivered (SOW §5.1).

#### H-03 · Documentation and transition package

**2.25d · must · B · all**
C4 context + container diagrams (Mermaid in repo); `docs/` index: data model, API (Redoc), events, notifications, permission matrix, runbooks (deploy, rotate secrets, restore DB, add a state, provision staff and state admins via CLI), dependency licence inventory (generated from the SBOM), transition checklist per SOW §5.3 (repo, AWS account, logging/monitoring, third-party credentials incl. Authorize.net, SES, and NCCPA; anything Focus provisioned as an interim measure is transferred at or before contract close); the **technical integration pathway** for a state (ingestion specification, API reference, credential issue, sandbox walk-through) as the engineering chapter of the pilot readiness playbook (X-05); one state-staff guide and one commission guide (pattern: CompactConnect `staff-user-documentation/`); docstring/JSDoc coverage gate.
AC: a new engineer stands up local + deploys to `test` from docs alone.

#### H-04 · Live operations test and deployment readiness

**1.5d · must · A · F-09, F-10**
SOW §2.3 acceptance (v2): "Successful live operations test demonstrating end-to-end privilege issuance in a Pilot Environment using Commission-controlled test data", with §3 Phase 3 "Deploy to production-grade, pilot ready environment". §2.3 puts live pilot operations, state coordination, and state system integration out of scope for this period of performance, so this ticket no longer takes a pilot live. Prod has existed since Sprint 2; this is the close-out: the test script (register → participation → SQL verdict → privilege request → payment → issuance → public verification → status change) run in `prod` by Commission-designated testers on Commission-controlled test data; payment in the processor's sandbox unless the Commission asks for a live transaction (Q-27); SES production access; restore drill with timings; RTO/RPO stated (Q-13); alarms; WAF tuned; seed states/fees/attestations job; test staff provisioned via the F-04 CLI; PA self-signup stays off in `prod` (U-01 flag) outside the test window; each runbook walked by someone other than its author; smoke suite in prod; the test record signed by the Commission's Product Manager. What a pilot launch needs afterwards (live processor credentials, real staff, self-signup on, on-call, test data purged) is written as the launch runbook and feeds the playbook (X-05).
AC: the live operations test passes end to end and its record is delivered; test data is purged by one documented command; the launch runbook exists.

#### H-05 · Seed and demo data

**0.5d · must · A · F-02, F-05 → every vertical, C-01**
`just seed demo`: deterministic synthetic states, attestations, practitioners, licenses, applications in every FLOW-06 status, privilege requests, privileges, transactions, adverse actions, and SII, written through the models (not the endpoints) so it lands with F-02 in Sprint 2; `docs/demo.md` script for sprint reviews (SOW §4.2 demos in `test`). v4.3: moved from Sprint 5 to Sprint 2 and promoted to `must` — it is what lets A-*, D-01, C-*, and V-01 start against realistic rows before P-03 lands. Each vertical adds the rows its screens need. No performance profile at pilot.

---

### Epic X — Product/design deliverables that gate engineering

#### X-01 · Design system: tokens, component library, Claude Design prompt

**1.5d · must · design + B · — → F-06, every UI ticket**
Brand assets from the Commission (Q-09) → USWDS theme tokens (`$theme-color-primary*`, type scale, radius, spacing); Storybook component library documenting every allowed component + primitive with usage rules; **Claude Design system prompt** (`docs/design/claude-design-prompt.md`): tokens, component whitelist, layout rules (USWDS grid, 16px gutters), terminology table, plain-language rules, a11y rules, "generate from this wireframe" instructions; lo-fi wireframe kit (page templates for wizard, queue, case view, dashboard, settings form); one exemplar screen per portal generated and approved by the PO.
AC: `docs/design/` has tokens, library, prompt, kit, exemplars; F-06 implements the tokens.

#### X-02 · Wireframes per UI ticket

**ongoing · must · design**
One lo-fi flow per UI ticket, one sprint ahead (see §3.3 product column). SOW §2.3 (v2): acceptance criteria for each user story are agreed with the Commission before development, so the product ticket also gets the ticket's AC lines confirmed by the Commission's Product Manager. Attached to the ticket before it starts. UX is at 100% in Sprints 1–2 and 50% in Sprints 3–6 (SOW §6.1), so the Sprint 1–2 wireframe batches are the largest.

#### X-03 · User research plan and per-sprint artifacts

**PM/UX · must**
Plan due end of Sprint 2 (QASP); rounds in Sprints 4, 5, 7 (PA registration + application incl. the note + resubmit loop; state portals incl. L-05/P-03; commission + public); synthesis → follow-up tickets in the following sprint. Round 2 is the gate on D15: if SQL staff or PAs cannot work the note + resubmit loop, the §5.1 message thread comes back in Sprint 6. Round 3 falls in Phase 3 where UX is at 15% (SOW §6.1) — keep it to a small commission + public sample or pull it into Sprint 6.

#### X-04 · Assumptions log and decision register

**PM · must**
`product/context/assumptions-log.md` seeded from §6, §5.1, and §5.2; SOW §8.5. Every §6 question is logged with the date it was sent; one still unanswered after the SOW §8.5.2 window (5 business days) is notified to the Commission and its impact recorded here (§8.5.1), with the default we are building to marked as at risk. Every §5.1 deferral and §5.2 candidate is logged with its trigger.

#### X-05 · Pilot readiness playbook and candidate-state engagement

**PM/UX · must**
SOW §2.3 (v2): a pilot readiness playbook "documenting the state onboarding workflow, technical integration pathway, and go-to-market plan", and engagement "with up to two Commission-identified candidate states to gather requirements and validate pilot readiness assumptions". Candidate states named in Sprint 1 (Q-03, Q-25; the same states can supply the data structures for L-02); sessions in Sprints 3–6; draft at the end of Sprint 7; delivered in Sprint 8. Engineering contributes the technical integration pathway (H-03) and the launch runbook (H-04). Actual state coordination and live pilot operations are out of scope (§2.3).

#### X-06 · MVP completion certification and Final Review Period

**PM · must**
SOW §2.3 (v2): on Focus's written certification of MVP completion, "such that there are no open issues in beta testing", the Commission has 14 calendar days to review against the agreed user-story acceptance criteria; Focus remediates notified deficiencies within 14 calendar days at no additional cost; functionality beyond the agreed user stories is a change order. Each sprint's software is also delivered to the Commission's Product Manager and Technical Lead, who inspect it against the QASP before accepting it, within 5 business days (§4.2, §8.5.2); non-compliant software is corrected in the next sprint at no additional cost (§5.2). Default: UAT in Sprint 7 is the beta test; certify at the Sprint 8 review. See §7 risk 11 for the alternative.

---

## 5. Summary

| ID | Title | Size | Tier | Lane | Sprint |
|---|---|---|---|---|---|
| F-01 | Repo truth-up | 1 | must | A | 1 |
| F-14 | Local dev stack + fakes | 1.5 | must | A | 1 |
| F-02 | Data model | 1.5 | must | A | 1 |
| F-05 | Events, outbox, history, audit | 1.5 | must | A | 1 |
| X-01 | Design system + Claude Design prompt | 1.5 | must | design+B | 1 |
| F-07 | Quality gates | 1.5 | must | B | 1 |
| F-03 | API guardrails + client generation | 1 | must | B | 1 |
| F-09 | Environments + Terraform CI | 2 | must | B | 1 |
| F-13 | Worker + jobs | 1 | must | A | 2 |
| F-04 | RBAC + MFA + staff CLI | 1.5 | must | A | 2 |
| F-11 | Notifications | 1.5 | must | A | 2 |
| F-08 | Security scanning | 1 | must | A | 2 |
| F-06 | App shell + tokens | 2 | must | B | 2 |
| F-10 | Infra security baseline | 1.5 | must | B | 2 |
| F-12 | Documents | 1 | must | A | 3 |
| S-03 | Attestations | 1 | must | A | 3 |
| S-01 | Compact + state config, contacts directory | 2 | must | A | 3 |
| L-01 | Qualifying license records | 1.5 | must | A | 3 |
| L-02 | State licensee data ingestion (upload + API) | 3 | should | A | 4–5 |
| U-01 | PA registration/login/TOTP | 2 | must | B | 3 |
| U-03 | PA profile | 1 | must | B | 3 |
| L-03 | Participation application wizard | 2 | must | B | 3 |
| L-05 | SQL eligibility verification | 1.5 | must | A | 4 |
| P-02 | Payment (fake + Authorize.net Accept UI) | 1.5 | must | A | 4 |
| L-04 | PA dashboard + privilege cards | 1.5 | must | B | 4 |
| P-01 | Privilege application | 2 | must | B | 4 |
| P-03 | Remote state issuance, proof verification | 1.75 | must | A | 5 |
| L-06 | Abandonment + withdrawal | 1 | rule | A | 5 |
| H-05 | Seed/demo data | 0.5 | must | A | 2 |
| V-01 | Public verification | 1.5 | must | B | 5 |
| D-01 | Practitioner search + detail | 1.5 | must | B | 5 |
| A-01 | Status updates + cascades | 1.5 | must | A | 6 |
| A-02 | Adverse actions + SII | 1.5 | must | A | 6 |
| A-04 | Expiry notices + expiry | 0.5 | must | A | 6 |
| A-05 | Privilege renewal | 1.5 | should | A | 6 |
| C-01 | Commission dashboard | 1 | must | B | 6 |
| C-02 | Operational and financial reports | 1.75 | must | B | 6 |
| N-01 | NCCPA certification integration | 2 | should | B | 6 |
| H-02 | Security validation | 2 | must | A | 7 |
| H-01 | Accessibility audit | 2 | must | B | 7 |
| H-04 | Live operations test + deployment readiness | 1.5 | must | A | 8 |
| H-03 | Docs + transition + integration pathway | 2.25 | must | B | 8 |

Totals: must 56.25 · rule 1 · should 6.5 · **63.75 engineer-days** (X-02–X-06 are PM/UX effort, not counted). v4.3 was 55.5; v3 was 67. v4.3 had 39 tickets; v5 has 42 (L-02, A-05, N-01 added).

### 5.1 Deferred — post-MVP backlog with re-entry triggers

Each row was in v3 and cut in v4. Nothing here is lost: the trigger says what brings it back, the size says what it costs, and the "shape" says where it plugs in so the build doesn't paint it out. v5 took the renewal flow off this list (it is A-05) and rewrote the triggers the new SOW changes.

| Deferred | Was | Size | Trigger to pull back in | Shape it plugs into |
|---|---|---|---|---|
| **ACH / eCheck** (`submitted_payment_pending`, settlement polling, `payment.settled/.returned`, fake `.50`) | P-02, Q-02c, FLOW-03/06 | 1.5 | Commission requires bank payment at pilot | `PaymentProvider` protocol; one new request status |
| **Payment settlement sync job** | P-02 `should` | 0.5 | ACH enabled, or the Commission's answer to Q-26 is that "verify payment for each privilege issued" (SOW §2.1) means settled funds, not processor approval | F-13 job; `get_status` already in the protocol; one column on the C-02 payment verification report |
| **Own USWDS card form (Accept.js + nonce, SAQ A-EP)** | P-02 / Q-02b option | 1 | H-01 cannot document the lightbox as an acceptable exception, or the Commission rejects the exception | Same protocol; `create_checkout` returns a nonce flow instead of a token |
| **Card-fee pass-through to the PA** | S-01, Q-02 | 0.25 | Commission says yes to Q-02 | One `fees` row `fee_type=card_surcharge` |
| **Participation fee checkout step** | L-03 fee step, `fee_type=participation` | 0.5 | Q-05: a Commission or SQL participation fee exists at pilot | P-02 checkout with `participation` line items; L-03 gains a step before review |
| **Case message thread** (`case_messages`, `case_message.posted`, thread component, remote-state request-info) | D15 v3, L-05, P-03, L-04, FLOW-02/07 | 1 | Usability round 2 (Sprint 5) shows note + resubmit fails, or a remote state cannot issue without asking the PA something in-system | Table + one component reused on both case views; replaces `request_note`; attachments via F-12 |
| **Staff user-management UI** (invite, resend, edit permissions, deactivate; `state_admin` scoped to own state, `compact_admin` any) | U-02 | 1 | More than 3 live states, a state asks to manage its own users without the CLI, or L-02's machine credentials need self-service rotation | U-02 as written in v3 over the F-04 CLI and the `state_admin` role that already exists |
| **Practice-requirements editor + public page** (markdown, preview, last-updated) | S-02 | 1 | The URL-or-document form in S-01 does not satisfy "Upload state practice requirements" (SOW §2.1), or the Commission wants the content hosted as pages | Replaces the URL field in S-01 |
| **In-app notification list on the PA dashboard** | L-04 | 0.5 | Usability shows PAs lose emails | `notifications` rows already exist; one list view |
| **45-day abandonment reminder** | L-06 | 0.25 | Commission asks for it | Second threshold in `abandon_stale_cases` |
| **Adverse-action reporting-timeliness tile** and 7/90-day issuance variants | C-01 | 0.25 | Commission asks after seeing C-01 | Views already carry `reported_at − order_date` |
| **Monthly summary report email** | C-02 | 0.25 | Commission asks | F-13 job over C-02 definitions |
| **NPI search on public verification** | V-01 | 0.1 | Q-12 includes NPI | One more `where` |
| **Redis permission cache** (ADR-0004) and ElastiCache | F-04, F-10 | 0.5 | p95 auth latency > 50 ms at pilot load | Cache in front of the per-request DB read |
| **Performance seed profile (10k practitioners)** | H-05 | 0.5 | C-01/D-01 slow on real data | `just seed perf` |
| **Semgrep + Bandit** | F-08 | 0.25 | CodeQL misses a class of finding H-02 turns up | Two more CI steps |
| **Cognito advanced security** (paid tier) | F-10 | 0.1 | Credential-stuffing observed, or H-02 requires it | Terraform flag |
| **U-03 "re-verification needed" flag on edited verified fields** | U-03 | 0.25 | SQL staff ask for it in round 2 | History already records the change |
| **Self-service lost-authenticator recovery** (re-prove identity + password → email link → re-enrol; CompactConnect `MfaResetStartLicensee`) | U-01, crosswalk §3.1 / §9.3 | 0.5 | Admin resets via `just user reset-mfa` become a support burden, or the Commission asks | U-01's reset command becomes a public flow on the PA pool |

Sum of deferred sizes ≈ 10 days (11.5 in v4.3, less the renewal flow).

Dropped from v1 as not in the SOW, and still dropped: SQL change/voluntary termination initiated by the PA (the state-side cascade is in A-01), PA self-report of an adverse action by a non-participating state (ML §4.A.12), expungement + certified export (ML §8.F, R5 §5.2(f) — handled by policy in H-03 runbooks), printable verification document/QR, contact CSV export. Two v1 drops are back because the redline response v2 lists them: bulk license upload (L-02) and military affiliation (candidate U-04, §5.2).

### 5.2 SOW §2.1 and §2.2 candidates not scheduled in v5

SOW §2.1 calls its list "the anticipated universe of features to be considered for MVP delivery", evaluated against "core privilege issuance workflows, available budget, and timeline" with the Commission's Product Manager. §2.2 "Additional MVP Capabilities" replaced the old "Out of Scope" list: its items "may be added" through the agile process. These are the items v5 does not schedule, with what would schedule them.

| Candidate | SOW | Size | What schedules it | Shape it plugs into |
|---|---|---|---|---|
| **U-04 Military affiliation** (PA declares an affiliation and uploads proof; staff see it on the case view) | §2.1 PA list, "Verify military affiliation" | 0.75 | The Commission says what the verification is for and who performs it (Q-23): a fee effect, an expedited path, or a record only | U-03 profile + F-12 documents; a fee effect is one `fees` rule |
| **Connecting a real state licensing system** to the L-02 API, or real-time lookups against one | §2.2; §2.3 puts state system integration out of scope for the period of performance | per state | A follow-on SOW, or the Commission prioritises one state and supplies its system owner | L-02's API and machine credentials |
| **Advanced reporting or analytics** | §2.2 | — | Commission asks after C-01/C-02 | Status views and report definitions |
| **Digital credential wallets or verifiable credentials** | §2.2 | — | Commission prioritises | `privileges` + V-01 |
| **Enterprise identity federation or SSO** | §2.2 | — | A state requires its own identity provider | Second identity provider on the staff Cognito pool |
| **Advanced identity proofing** | §2.2 | — | Commission prioritises; today identity is established by the SQL's review | U-01 registration |
| **Support tooling** | §2.2 | — | Follow-on operations SOW (§5.3) | Audit log + D-01 |

---

## 6. Sprint 1 — questions for the client

Each has a default and what it gates. SOW §8.5.2 gives the Commission 5 business days for prioritisation decisions and policy or regulatory clarifications. The earlier SOW let Focus proceed on reasonable assumptions after the window; that sentence is gone, so an unanswered question is notified and logged with its impact (§8.5.1, X-04), and the default is what we build to at our own risk of rework until it is answered.

### Answer in Sprint 1

| # | Question | Default | Gates |
|---|---|---|---|
| **Q-01** | Open source and Commission ownership are settled by SOW §5.1, §5.3, §7.5 (§4.2 now says a "Commission-designated" repository, and §5.3 lets Focus create accounts as an interim measure and transfer them by contract close). Remaining: public from day one or at delivery; which GitHub org and who administers it; which licence (repo currently carries MIT © Focus Consulting; RFP Q&A 30.1 states no preference; CompactConnect is AGPL-3.0). Public from day one = free Actions minutes, CodeQL, secret scanning, Dependabot; private until delivery would need GitHub Advanced Security (paid) or self-hosted scanners. | Public day one, Apache-2.0, copyright the Commission, Commission org, Focus as admins during PoP | F-01, F-08, H-03 |
| **Q-02** | Authorize.net: who opens the merchant account (Commission as merchant of record per SOW §7.4)? Timeline for sandbox credentials (Sprint 1 request, needed by Sprint 3) and live credentials (Sprint 7)? Card only at pilot — confirm no bank/ACH requirement (§5.1). Card-fee pass-through to the PA yes/no? SOW §7.4 (v2) puts every processor cost on the Commission (acquisition, setup, transaction, ongoing fees), which is the background to the pass-through question. | Commission is MoR; sandbox by Sprint 3; card only; no pass-through | P-02, S-01, H-04 |
| **Q-02b** | Confirm the payment form shape: Authorize.net's Accept UI lightbox (smallest PCI scope, SAQ A, third-party form whose accessibility we document as a known exception) rather than our own USWDS form (SAQ A-EP questionnaire for the Commission, §5.1). | Lightbox, a11y exception documented | P-02, H-01, H-02 |
| **Q-03** | Pilot states: which participating states are in the pilot, which act as SQL vs remote state, and a named staff contact per pilot state for provisioning and usability sessions. Member list to seed: 19 per the RFP (Oct 2025), NC effective 2026-04-01, NJ enacted 2026-01-09 → 20; MA, MI, PA, NY carried over and AL, AZ, FL, MO, NM filed in 2026 (Jan 14 2026 exec minutes). Also name the up to two candidate states for the pilot readiness playbook (SOW §2.3, X-05). | Seed all 20 with `effective_date`; 2–3 live for the live operations test | S-01, F-04, H-04, X-03, X-05 |
| **Q-04** | Qualifying license data. The redline response v2 lists state upload of PA and licensure data by file and API, so the earlier either/or (states pre-load by hand, or the PA enters and the SQL verifies) is now three-way, and what the upload is for is open: see `TENSION-04-state-upload-versus-multi-party-record` and Q-25. Still to confirm: the CBC is entirely outside the system and we record only the completion date. Counsel to confirm that the SQL's in-system verification satisfies "verify and submit" under Rule 4 §5.3(c) and ML §8.B for a state that sends no feed, and whether a field that arrives in a feed counts as verified without it. | PA enters, SQL verifies; an uploaded license is the on-file record the SQL compares against; CBC outside, date only; in-system verification is the submission | L-01, L-02, L-03, L-05, F-02 |
| **Q-05** | Fees: the Nov 3 2025 commission minutes say no compact-fee revenue is anticipated "until a future date", but "Commission Privilege Fee" is on the Mar 10 2026 Finance Committee agenda and "Draft Rule 6 – Fees" on the Mar 9 2026 Rules Committee agenda. What did those decide? Is there any participation fee at pilot (if yes, the L-03 checkout step returns, §5.1)? Who provides pilot-state privilege fee amounts and when? Is a renewal charged the same fees as a first privilege (A-05)? | Commission privilege fee configurable, $0 until Rule 6 sets it; state privilege fees configurable; no participation fee; renewal fee equals the privilege fee | S-01, L-03, P-01, A-05 |
| **Q-06** | Attestation wording for participation and privilege applications (we draft from ML §4.A / Rule 3; Commission/legal signs off). Sworn statement = checkbox + typed name + timestamp, or e-signature? | Checkbox + typed name + timestamp + IP | S-03, L-03, P-01 |
| **Q-07** | Which documents are *required* vs optional at application? The rules let the Commission require proof of the SQL basis (R2r §2.1(c)) and let remote states require proof of compliance, a supervision/collaborative agreement, prescriptive-authority requirements, and jurisprudence (R3r §3.4(c)(3)–(6)); R5 §5.3(e)(5) wants NCCPA evidence on file. Per pilot state: which of these are attestation, which are upload, and what is mandatory before submit? | All optional uploads; every remote-state proof is an attestation unless the state says otherwise; SQL/RS may request more via the note + resubmit loop | L-03, P-01, S-01, F-12 |
| **Q-08** | Denial reason lists for SQL eligibility and remote-state issuance (must exclude CHRI), and the appeal text shown to the PA — confirm "within 30 days of receipt, filed with the SQL" (R3r §3.8(a)–(b), numbered 3.9 in the Feb 9 2026 minutes). | Enum from ML §4.A items + "other"; 30-day appeal copy | L-05, L-06, P-03 |
| **Q-09** | Brand assets: logo files, palette, typography, any style guide; who approves the look | Derive from pacompact.org; Public Sans; adjusted USWDS blue | X-01, F-06 |
| **Q-21** | The Mar 11 2026 Executive Committee agenda lists "Data System User Stories" and a "Technology Committee". Please share the user stories so the backlog refinement in SOW §4.4 starts from the Commission's own list. The redline response v2 names the Commission's Product Manager and has prioritisation made "in consultation with the Commission Chair, and the Technology Subcommittee when possible": who sits on the subcommittee and how is it consulted between sprints? | RFP §3.1 priority stories + SOW §2.1 as the backlog seed | §4 backlog, X-03 |
| **Q-22** | Each pilot state: the public URL of its PA practice requirements page, or the document to upload (SOW §2.1 "view" and, since v2, "upload state practice requirements"). | "Not provided" shown until received | S-01, P-01 |
| **Q-23** | SOW §2.1 (v2) adds "Verify military affiliation" for the PA. What is the verification for (a fee effect, an expedited path, a record only), who performs it (the PA attests, the SQL confirms, a third party), and what proof is accepted? | Not scheduled (candidate U-04, §5.2) until answered | U-04, U-03 |
| **Q-24** | NCCPA integration (SOW §2.1 v2; Executive Committee minutes 2026-05-13): who signs the NCCPA third-party contract and when; any cost and who bears it; the API documentation and a sandbox; which fields NCCPA returns and how often status may be refreshed. | `FakeProvider` until the contract is signed; PA-entered certification stands | N-01, U-03, L-05 |
| **Q-25** | State data ingestion (SOW §2.1 v2, §3 Phase 2). Which two or more representative states will the Commission name, and who in each can describe their data structures by Sprint 3? And the open points in `TENSION-04`: what the upload is for; which PAs a state uploads (all it licenses, or only applicants); what state staff still do per PA once data is uploaded; whether a later upload can end a privilege on its own; which value wins when the upload and the PA disagree. | Mock data from two named states; upload writes license fields only, changes behind an active privilege are held for staff, the SQL's review stays the decision | L-02, L-01, L-05, U-01 |
| **Q-26** | SOW §2.1 (v2) lists "Payment reconciliation and financial reporting to Member State administrators to verify payment for each privilege issued"; §7.4 still says Focus is not responsible for reconciliation or settlement. Is a report of processor-approved payments per privilege what is meant, or must it show settled funds and remittances made to each state? | Processor-approved payments per privilege and a remittance summary; no settlement status | C-02, P-02 |
| **Q-27** | Live operations test (SOW §2.3 v2): who are the Commission-designated testers and state staff; what "Commission-controlled test data" is and who prepares it; sandbox or a live card transaction; target date. | Sprint 8, in `prod`, processor sandbox, test data seeded by Focus to the Commission's sign-off | H-04, X-06 |
| **Q-28** | SOW §7.5 (v2): Focus may not embed or deliver third-party materials, open-source components included, without the Commission's prior written consent. Will the Commission give standing written consent to the dependency list (the SBOM register, F-08) and a rule for additions (for example OSI-approved permissive licences, notified each sprint)? SOW §2: all software and Commission data stay on servers in the United States — does that extend to a CDN's edge caches and to email and payment processors? | Standing consent requested in Sprint 1 against the SBOM; US regions only; CDN geo-restricted to the US | F-08, F-10, H-02 |
| **Q-29** | SOW §4.2 and §6.1.1 (v2): the Commission's Technical Lead inspects each sprint's software against the QASP and does code review. Who is it, what repository and environment access do they need, and does their review gate merges or the sprint acceptance only? | Review at sprint acceptance, 5 business days; does not gate merges | every engineering ticket, X-06 |

### Answer by Sprint 4

| # | Question | Default | Gates |
|---|---|---|---|
| **Q-10** | Uniform data set specifics: "sex" values, other-names handling, education program list source, phone required; which fields the PA may edit after SQL verification, and whether the SQL is emailed when one changes | USWDS-recommended options; PA edits, history records it, no email to the SQL (`ATOM-GOV-M0825-02`) | F-02, U-03, L-04 |
| **Q-11** | SSN: collect full SSN at application (rule) or last-4 + NPI? Who may view full SSN (default: SQL users with `read_ssn`, audited)? | Full, encrypted; last-4 shown; reveal audited | F-02, U-03, D-01 |
| **Q-12** | Public verification fields beyond name + states (rule minimum): privilege number, status, issue/expiry dates? Adverse-action existence? NPI as a search key? | Number, status, dates; no adverse-action data; no NPI | V-01 |
| **Q-13** | Operations: SOW §7.2 has Focus provisioning and managing hosting during the PoP; §5.3 (v2) says every account and service is intended to be Commission-owned, lets Focus create them as an interim measure and transfer them by contract close, and makes the Commission responsible for timely provisioning where it elects to use its own. Does the Commission want to own the AWS account from Sprint 1 (Focus operates inside it) or receive a transfer at the end? RTO/RPO targets and retention. On-call belongs to the follow-on operations SOW, since live pilot operations are out of scope here (§2.3) | Commission-owned account, Focus-operated, from Sprint 1; RTO 4h / RPO 24h documented | F-09, H-04 |
| **Q-14** | Notification cadence beyond the 60-day rule minimum (30/7?), and which Commission mailbox receives ops notifications | 60/30/7 email | F-11, A-04 |

### Settle during Phase 1

| # | Question | Default | Gates |
|---|---|---|---|
| **Q-15** | The earlier SOW's §2.3 said the 72-hour issuance goal was "an operational target ... not a system-level SLA". The redline response v2 removed that sentence and has the PA "receive confirmation of timely privilege issuance" (§2.1). RFP Q&A 46.1 is now the only source for the operational reading. Confirm: 72 hours is a target shown on the dashboard, not an SLA, and the clock is remote-state receipt of a paid request → issuance. | As stated | C-01, P-03 |
| **Q-16** | Are Rules 2/3 (redline approved Feb 9 2026) and Rule 4 (data system, reviewed Nov 10 2025) final enough to build to? The Mar 9 2026 Rules Committee agenda still carries "Draft Rule 6 – Fees" and "Misdemeanor Convictions & Compact Eligibility", which touch S-03/L-05. Rule contact with the 5-business-day window (SOW §8.5.2) | Build to R2r/R3r/R5 as amended Nov 10 / Feb 9; attestation text versioned so a change is a data change | A-01, A-02, S-03 |
| **Q-17** | Adverse action report fields: confirm summary + NPDB category (not documents), 5-day / 1-business-day windows (Nov 10 2025 minutes) | As in A-02 | A-02 |
| **Q-18** | Usability recruiting: 3–5 PAs + 2–3 state staff per round, Sprints 4/5/7 — can the Commission commit dates now (SOW §4.3, §8.5.2)? | Plan as stated | X-03 |
| **Q-19** | Terminology sign-off (SQL, Compact Privilege, Remote State) and the title-agnostic requirement | Rule terms | X-01, F-06 |
| **Q-20** | Adverse-action notification breadth: the statute (ML §8.D) says notify *all* participating states; draft Rule 4 §5.6(b) says only states where the PA holds a QL or privilege; the Feb 9 minutes prefer "accessible" over "distributed". Which reading governs the email recipient list? See `product/context/evidence/tensions/TENSION-01-adverse-action-notification-breadth.md`. | Push to related states; any state can find the record via search | F-11, A-02, D-01 |

---

## 7. Risks

1. **Rules were drafts when this was written.** Rules 3 and 4 were adopted on 2026-04-06; the citations here (R2r, R3r, R5) are to the drafts and are being re-checked under SCRUM-39 (`product/context/evidence/CHANGES-2026-10-01-adopted-rules.md`; the flows carry needs-review notes). Cascades, windows, fees, and attestation text live in a few pure functions and seed tables with a test matrix so a rule change (Rule 6 fees, misdemeanor eligibility) is a one-file or one-row change.
2. **SQL verification has no reference UI.** L-05/P-03 are designed from wireframes first and tested in usability round 2 (Sprint 5) before being considered done. Round 2 is also the gate on the note + resubmit decision (D15).
3. **Authorize.net account latency.** FakeProvider keeps P-01/P-03 moving; the end-to-end prod demo in Sprint 5 needs sandbox credentials by Sprint 3.
4. **Single reviewer.** Contract tickets get careful review; the rest lean on automated review and small PRs.
5. **AGENTS.md is wrong today.** F-01 first, or AI sessions will build against a stack that doesn't exist.
6. **Coverage is informational.** F-07 in Sprint 1 or the 90% AQL is unrecoverable by Sprint 8.
7. **Prod from Sprint 2 means real cost early.** Small instance sizes in `prod` until Sprint 7; the point is the pipeline and controls, not capacity.
8. **Phase 1 is two sprints, not three.** Sprint 1 is the heaviest sprint in the plan (11.5 nominal days, eight foundation tickets across two lanes) and runs while workshops do; if F-02/F-05 slip, everything in Phase 2 slips. Mitigation: F-01 and F-14 are half-day-scale with AI tooling, the PM/UX absorb the workshop load, and F-09 may finish in Sprint 2 without moving the `test`-env milestone past the first demo.
9. **Descoping can overshoot.** §5.1 deferrals assume no pilot state needs a self-service user UI, a participation fee, or a bank payment. If the Sprint 1 answers to Q-02, Q-05 reverse any of these, the item returns at the size shown; after v5 Phase 2 holds ~12 days of slack for that, not ~20.
10. **No in-app channel for remote states.** P-03 has issue/deny only; a remote state with a question contacts the PA by email from D-01. If round 2 shows this is unworkable, the message thread returns (§5.1) in Sprint 6.
11. **The Final Review Period falls after week 16.** SOW §2.3 gives the Commission 14 calendar days after Focus certifies completion, then Focus 14 days to remediate at no additional cost. Certifying at the Sprint 8 review puts both outside the funded period. Certifying at the Sprint 7 review keeps the review inside Sprint 8 but pulls H-03 and H-04 a sprint earlier. Decide by Sprint 5.
12. **The right to proceed on assumptions is gone.** SOW v1.0 let Focus proceed on reasonable assumptions when a decision was late (2 and 3 business days). The redline response v2 removed that sentence and set every window to 5 business days (§8.5.2). A late decision is notified and logged (§8.5.1) and settled by schedule adjustment, reprioritisation, or change request. Building to a §6 default before the answer arrives is at Focus's risk of rework, and a sprint is 10 business days.
13. **Scope grew inside the same ceiling.** v5 schedules 8.25 more engineer-days against the same ~80 heads-down days and \$270,000. §2.1 is a candidate list, so each `should` ticket (L-02, A-05, N-01) is a prioritisation decision for the Commission's Product Manager, to be put to them with its estimate in Sprint 1.
14. **Two more external dependencies.** N-01 needs an NCCPA contract and API documentation; L-02 needs two representative states and their data structures. Both run on a fake or on mock data until then, as P-02 does.
15. **State ingestion is built to a preference, not an answer.** `TENSION-04` is open. If the Commission's answer makes the upload the source of the PA record or of the eligibility decision, L-02, L-05, U-01, and FLOW-01/02 change, and that is more than the 3 days L-02 carries.
16. **Third-party materials need written consent** (SOW §7.5). Every open-source dependency is in scope of that sentence. Without standing consent (Q-28) each new dependency is a contract question.
17. **Non-compliant software is corrected at no additional cost** in the next sprint (SOW §5.2), judged by the Commission's Product Manager and Technical Lead, and the security standard is now ASVS 5.0. The CI gates (F-07, F-08) are what keep this from becoming unpaid work.

---

## 8. Revision notes

### v4.3 → v5 (2026-10-05) — SOW redline response v2

The SOW this backlog was derived from (v1.0, 2026-03-09) was replaced with the redline response v2. `product/context/flows/README.md` ("SOW alignment") lists the scope changes flow by flow; this pass applies them to the tickets.

- **Scope rule rewritten.** §2.1 is a candidate list, the old §2.2 "Out of Scope" is gone, and §2.3 defines acceptance as a live operations test on Commission-controlled test data with live pilot operations out of scope. New tier `candidate` and new §5.2.
- **Three tickets added, all `should`:** L-02 state licensee data ingestion by upload and API (3d; SOW §2.1 and §3 Phase 2; built to the `TENSION-04` preference on mock data), A-05 privilege renewal (1.5d; off the §5.1 deferred list), N-01 NCCPA certification integration (2d; behind a provider protocol until the contract exists).
- **Five tickets grew:** S-01 (+0.5: administrator contacts, member-state directory, practice-requirements document), P-03 (+0.25: per-proof verification), C-02 (+0.75: state transactions page, payment verification report, remittance summary), H-03 (+0.25: technical integration pathway), and V-01 at no cost (inactive privileges shown without a reason).
- **H-04 is no longer a pilot go-live.** It is the live operations test and deployment readiness. New PM items X-05 (pilot readiness playbook, up to two candidate states) and X-06 (completion certification and the 14-day Final Review Period).
- **Standards and terms:** ASVS 3.0 → 5.0 (F-10, H-02); United States-only hosting (F-10); third-party materials register and consent (F-08); Commission Technical Lead review and 5-business-day acceptance (X-06); decision windows 2/3 → 5 business days and the proceed-on-assumptions sentence removed (§3.1, §6, X-04); SOW section references moved from §8.3 to §8.5.
- **Questions:** Q-01, Q-02, Q-03, Q-04, Q-05, Q-13, Q-15, Q-21, Q-22 revised; Q-23 to Q-29 added. **Risks:** 9 revised, 11 to 17 added.
- **Capacity:** 55.5 → 63.75 engineer-days; Phase 2 slack about 40% → about 25%.
- **Not done in this pass:** rule citations are still to the draft rules (SCRUM-39 is re-checking them against the adopted Rules 3 and 4); military affiliation is not scheduled (Q-23); nothing here has been prioritised with the Commission's Product Manager yet.

### v4.2 → v4.3 (2026-09-30) — crosswalk and signal alignment; ownership for an async team

- **Ownership model** moved to `mvp-jira-tickets.md` ("How an engineering ticket is owned"): one owner per epic end to end, decisions an engineer makes alone vs with product vs with the tech lead, provides/consumes per epic, table ownership, review rules, journey-based assignment. The lane split in §3.3 is retained as history; the Jira schedule governs.
- **H-05 seed to Sprint 2, `must`**, written through the models so it lands with F-02. This is the structural change that lets A-01/A-02/A-04, D-01, C-01/C-02, and V-01 start on realistic rows instead of waiting for P-03; their Jira "blocked by" lines shrink accordingly. Epic 4 (design system) is unblocked from the platform (hand-written MSW for `/api/me` until F-03's generator lands).
- **Per-field provenance** (`entered_by`, `verified_by_state`, `verified_at`) added to `practitioners` in F-02, stamped by L-05, shown by L-04 — from `SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance` (commit 5e27633, after v4.2). F-02's `states` row corrected to the four-proof matrix S-01 already described.
- **Crosswalk items** folded in: U-01 (10-minute idle timeout, neutral registration copy, `reset-mfa` CLI, per-environment self-signup flag), U-03 (post-verification edits keep the stamp), S-01 (one-way go-live with confirm), L-04 ("why unavailable" reasons, "Verified by", "Expiring in N days"), L-05 (existing adverse actions and SII beside the investigation attestation, SQL-attached verification document), P-01 (20-state cap), H-04 (enable self-signup, renewal-trigger date, runbook walk-through). New §5.1 row: self-service authenticator recovery.
- Q-04 gains the counsel question FLOW-02 folded into it; Q-10 gains the "email the SQL?" question.
- The v4 note "Flows that now describe more than the backlog builds" is resolved: all seven flows were revised 2026-09-30 with "Deferred" headings and now cite only existing tickets.

### v4.1 → v4.2 (2026-09-30) — API contract reduced to guardrails; Jira consolidation

- **F-03 is no longer an endpoint contract** (D3). Engineers building a vertical define its routes and models as they go; the platform ticket fixes only the auth dependency, success/error envelopes, pagination conventions, a required permission annotation, and the OpenAPI → TS client → MSW generation pipeline, with one worked example route. Size 1.5 → 1; total 56 → 55.5.
- **`mvp-jira-tickets.md` created**: the 39 items consolidated into 12 epics, each with one product ticket (requirements + basic wireframes) and one engineering ticket (implementation; engineers create beads as they see fit), scheduled two engineering tickets in flight per sprint. This document remains the reasoning and the deferred list.

### v4 → v4.1 (2026-09-30) — three cuts reversed on CTO review

- **Worker ECS service back in scope** (D8, F-13 at 1d). The dispatcher loop runs in its own service again; scheduled jobs stay on EventBridge → run-task on the same image. F-05, F-11 wording follows.
- **Document upload back in scope as `must`** (D9, F-12 at 1d, Sprint 3, lane A first). The v4 deferral rested on "no SOW §2.1 item requires a file"; the rules say otherwise. R2r §2.1(c) has the PA submit proof of the SQL basis "as determined by the Commission"; R3r §3.4(c)(3)–(6) let a remote state require proof of compliance, a supervision/collaborative agreement, prescriptive-authority requirements, and jurisprudence; R5 §5.3(e)(4)–(5) put state verification documents and NCCPA evidence in the uniform data set. What is *required* at pilot is still Q-07; the upload path is not optional. RustFS returns to F-14, S3 Malware Protection to F-10, `documents` to F-02, a documents step to L-03, per-state `proof_upload` to S-01/P-01, an optional attachment to A-02.
- **`state_admin` role back in scope** (D5, F-04, §2.4). The role, its per-state `admin` permission, and own-state configuration in S-01 ship; only the self-service user-management UI (U-02) stays deferred, and the F-04 CLI enforces the same own-state scoping a `state_admin` will get in the UI later.
- Net: 53.5 → 56 engineer-days, 38 → 39 tickets; §5.1 loses three rows and the deferred total is ≈ 11 days.

### v3 → v4 (2026-09-30) — descoping pass

Rule applied: keep what SOW §2.1 names, in the smallest form that satisfies it for a 2–3 state pilot; keep rule behaviour a pilot privilege can actually exercise in 16 weeks; defer everything else with a trigger. Result before the v4.1 reversals: 67 → 53.5 engineer-days, 42 → 38 tickets, two Q-items closed.

Cuts (all listed with triggers in §5.1; struck items were reversed in v4.1):

- **ACH/eCheck gone entirely** (Q-02c closed; card only). The settlement-sync job goes with it.
- **Payment shape decided**: Accept UI lightbox. Q-02b becomes a confirmation; the comparison table is out of the ticket.
- ~~Document upload deferred~~ — reversed in v4.1.
- **Renewal flow deferred** (A-04 shrinks to expiry notices + expiry). No privilege issued in Sprint 5 can reach a QL expiry inside the period of performance.
- **Case message thread replaced by note + resubmit** (D15). Zero new tables; remote states have no in-app request-info at pilot.
- **Staff user-management UI deferred** (U-02 gone; staff provisioned with the F-04 CLI). ~~`state_admin` role dropped~~ — reversed in v4.1.
- **S-02 collapsed to a URL** per state in S-01 (new Q-22 asks for the links).
- **P-04 folded into L-04** (privilege cards + history on the dashboard).
- **Redis/ElastiCache removed** (no cache at pilot, D5). ~~Separate Worker service removed~~ — reversed in v4.1.
- Trimmed: F-08 (no Semgrep/Bandit), F-10 (no Cognito advanced security), L-06 (no 45-day reminder), C-01 (five tiles), C-02 (no monthly email), V-01 (no NPI search), H-05 (no perf profile), U-03 (no re-verify flag), L-04 (no notification list).

Kept deliberately despite being cuttable: TOTP for PAs (D4, decided); SSN encryption (rule); the outbox/event core (it is what makes every cut above re-addable without rework); the full security and a11y gates (QASP).

Flows that now describe more than the backlog builds (update or annotate): FLOW-02 (message thread → note + resubmit), FLOW-03 (ACH, reconcile job, Accept-shape table), FLOW-04 (renewal flow entirely), FLOW-06 (`submitted_payment_pending`, renewal transitions, `info_requested` on privilege requests), FLOW-07 (`case_message.posted`, `payment.settled/.returned`, `renewal.*`, `user.invited/.deactivated`; and the non-existent ticket `P-05`).

### v2 → v3 (2026-09-30) — review against SOW, flows, evidence

- Sprint plan compressed from nine sprints (0–8) to the eight the SOW funds (§3, 16 weeks), mapped to SOW Phases 1/2/3.
- Capacity restated: v2 claimed must ≈ 54 days; the table summed to 67. SOW capacity quoted from §6.1 (136 nominal days by phase) and §6.2 (1,006 h ≈ 126 days).
- Added the SOW §2.1 → ticket traceability table (§1.2).
- Team line matched to SOW §6.1; common AC cites the GSA 18F Front-End Guide and per-sprint documentation currency.
- Q-15 marked settled by SOW §2.3 / RFP Q&A 46.1; Q-01 narrowed; Q-13 rewritten around SOW §7.2 / §5.3.
- Scheduling defects fixed: L-03 depended on a later-sprint F-12; H-05 depended on a later-sprint P-03.
- Facts corrected: `LICENSE` exists (MIT © Focus); member states are 20 (NJ enacted 2026-01-09, NC effective 2026-04-01); a Commission privilege fee and Draft Rule 6 are on the March 2026 agendas; the 5-day adverse-action window cites the Nov 10 2025 minutes; the 30-day appeal window is in the R3 redline; new Q-21 for the Commission's own user stories.
- Flow gaps closed: 60-day abandonment of unpaid privilege requests (L-06); service-member SQL basis (L-03); R2r §2.1(b) address-change duty (U-03); FLOW-07 events named in their producing tickets; L-05 decision = the R3r §3.4(b)(4) notice to the Commission.
