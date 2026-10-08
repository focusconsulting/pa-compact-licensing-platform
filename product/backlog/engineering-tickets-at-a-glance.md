# Engineering Tickets at a Glance

The fourteen engineering tickets in [`mvp-jira-tickets.md`](mvp-jira-tickets.md), one short card each: what it is, who it is for, which flows it implements, and how we know it is done. That file holds the full scope and the product tickets, and it governs where the two differ.

Every ticket also meets the shared **definition of done**: 100% test coverage, no lint errors or warnings, pa11y and axe clean on new screens, OpenAPI and the TypeScript client regenerated on any API change, forward-only migrations, history and audit rows on every change, a domain event for every state change, runs locally with no AWS credentials, and docs updated in the same PR.

**⚠ Under review** marks an acceptance criterion that conflicts with the adopted compact rules, the built data model, or the engineering constitution; the note says how, and the backlog owner decides the fix.

| # | Ticket | Sprint | Blocked by |
|---|---|---|---|
| 1 | [Repo foundation, local stack, and CI gates](#1-repo-foundation-local-stack-and-ci-gates) | 1 | — |
| 2 | [Backend platform](#2-backend-platform) | 1–2 | 1 |
| 3 | [Environments, deploy pipeline, and infrastructure security](#3-environments-deploy-pipeline-and-infrastructure-security) | 1–2 | 1 |
| 4 | [Design system and app shell](#4-design-system-and-app-shell) | 2 | 1 |
| 5 | [Authentication, roles, and accounts](#5-authentication-roles-and-accounts) | 3 | 2, 4 |
| 6 | [Compact participation application (PA side)](#6-compact-participation-application-pa-side) | 4 | 5 |
| 7 | [Qualifying license records and SQL eligibility review](#7-qualifying-license-records-and-sql-eligibility-review) | 3–4 | 5 (review part: 6) |
| 8 | [Privilege application, payment, and remote-state issuance](#8-privilege-application-payment-and-remote-state-issuance) | 5 | 7 |
| 9 | [Status changes, adverse actions, expiry, and renewal](#9-status-changes-adverse-actions-expiry-and-renewal) | 6 | 7 (renewal: 8) |
| 10 | [Practitioner records, Commission dashboard, and reports](#10-practitioner-records-commission-dashboard-and-reports) | 5–6 | 5 |
| 11 | [Public privilege verification](#11-public-privilege-verification) | 6 | 2, 4 |
| 12 | [Pilot readiness](#12-pilot-readiness) | 6–8 | everything above |
| 13 | [State licensee data ingestion](#13-state-licensee-data-ingestion) | 4–5 | 7 (license records) |
| 14 | [National credentialing integration (NCCPA)](#14-national-credentialing-integration-nccpa) | 6 | 5 |

---

## 1. Repo foundation, local stack, and CI gates

**Summary.** Fixes what is wrong in the repo today, gives every engineer a one-command local stack that needs no AWS account, and turns the quality and security rules into CI checks that fail a PR.

**User story.** As an engineer on the team, I want a working local stack and automatic quality gates from day one, so that every ticket can be built and tested offline and nobody has to police standards in review.

**Flows.** None directly; every flow runs on this stack.

### Acceptance criteria

- From a fresh clone, `just up` lets you register a PA, log in, receive the welcome email in maildev, upload a file, and complete a payment, with no AWS credentials. ⚠ Under review: the backlog says "a fake payment"; the constitution requires the payment to go to an out-of-process mock server.
- `/api/me` works on DEV.
- DEV applies cleanly without Redis.
- A coverage drop, a lint warning, a contrast violation, or a high or critical security finding fails the PR. ⚠ Under review: the SOW's quality plan also fails medium findings.
- The end-to-end smoke test runs in under 5 minutes.
- Everything runs on the free tier of a public repo; if the repo must stay private, the GitHub Advanced Security cost is documented.

---

## 2. Backend platform

Data model, events, API guardrails, notifications, documents, worker.

**Summary.** The shared foundation every feature builds on: the database tables (built in PRs #81 and #82), helpers that record history, audit, and events with every change, the rules every API route follows, email sending, file storage, the background worker, and realistic demo data.

**User story.** As an engineer building a feature, I want shared tables, history and event helpers, API conventions, notifications, documents, and a worker already in place, so that I write only my feature's logic and it behaves like every other feature.

**Flows.** [FLOW-06 state machines](../context/flows/06-state-machines.md) (the statuses the tables enforce) · [FLOW-07 domain events](../context/flows/07-domain-event-catalogue.md) (the event catalogue) · [Flows README](../context/flows/README.md) ("shape of every write").

### Acceptance criteria

- Migrations apply to an empty database and to the current DEV database.
- Every table has created and updated by and at.
- The status views pass a fixture matrix: active, expired, encumbered, each deactivation reason, within the 2-year bar. ⚠ Under review: the backlog also lists a "grace rule" case, which the adopted Rule 3 dropped.
- A change without an event fails a test.
- A handler that throws is retried, then dead-lettered with an alarm.
- Replaying an event does nothing; two worker tasks never handle the same event.
- A route without a permission annotation fails a test; a route returning the wrong response shape fails a test.
- CI fails when the OpenAPI document drifts from the code; one command regenerates the client and mocks.
- Storybook renders a page against mocks with no API running.
- A notification with a repeated idempotency key is sent once; email templates are snapshot-tested; SES sandbox is verified on DEV.
- A 20 MB upload succeeds, 21 MB is rejected, the EICAR test file is blocked in the test environment, and state A cannot fetch state B's case document.
- A failed job raises a Slack alarm; the dispatcher drains 1,000 queued events in under a minute locally.
- `just seed demo` on an empty database produces the fixture set, the status views agree with it, and the same seed loads into `test`.

---

## 3. Environments, deploy pipeline, and infrastructure security

**Summary.** Stands up the `test` and `prod` environments next to `dev`, makes deploying a matter of pushing a tag, and hardens the infrastructure: firewall, security headers, encryption, backups, malware scanning, and United States-only hosting.

**User story.** As the Commission, I want secure, US-only test and production environments that the team can deploy with one tag, so that every sprint is demoed on real infrastructure and the pilot runs on a hardened stack.

**Flows.** None directly.

### Acceptance criteria

- A fresh AWS account reaches a running `test` stack by following the runbook alone.
- One tag deploys to prod.
- `prod` exists, empty and monitored, by the end of Sprint 2.
- Checkov reports no issues.
- securityheaders.com gives an A grade.
- An OWASP ASVS 5.0 mapping document exists.
- A policy test fails when anything uses a non-US region.

---

## 4. Design system and app shell

**Summary.** Turns the brand into USWDS design tokens, documents the approved components in Storybook, writes the design prompt and wireframe kit the team uses for every screen, and builds the app shell and shared UI pieces every screen is assembled from.

**User story.** As a PA, a state staff member, or a Commission user, I want every screen to look and behave consistently and accessibly, so that I can find my way around and complete tasks without relearning the interface.

**Flows.** [FLOW-06 state machines](../context/flows/06-state-machines.md) (the status labels the shared status tag shows).

### Acceptance criteria

- The design folder holds the tokens, the component library, the design prompt, the wireframe kit, and exemplar screens, and the shell uses the tokens.
- All three portals' navigation (PA, state, Commission) renders from mocked permissions.
- Lighthouse accessibility score is 100.

---

## 5. Authentication, roles, and accounts

**Summary.** Lets PAs register and sign in with two-factor authentication, lets staff be provisioned per state, enforces who can do what in each state, and gives the PA a profile for their uniform data set.

**User story.** As a PA, I want to create an account and keep my profile current, so that I can apply to the compact. As state or Commission staff, I want to sign in with exactly the permissions my role and state allow, so that I can act only on the records I am responsible for.

**Flows.** [FLOW-01 end-to-end issuance](../context/flows/01-end-to-end-privilege-issuance.md), Phase 0 (account and profile).

### Acceptance criteria

- A table-driven test checks every role against every endpoint.
- A permission change takes effect on the next request.
- A token without the two-factor claim is refused (401); a deactivated user is refused (403).
- A state admin cannot use the staff CLI outside their own state.
- End-to-end: register → verify email → enrol two-factor → log in → empty dashboard.
- Staff cannot use the PA sign-in, and PAs cannot use the staff sign-in.
- Registering an email that already exists gets the same response as a new one.
- A request after 10 idle minutes is refused.
- `just user reset-mfa` forces two-factor re-enrolment at the next login.
- Self-signup is refused on `prod` while its flag is off.
- Address and email history is visible on the practitioner record.

---

## 6. Compact participation application (PA side)

**Summary.** Phase 1 of the process, from the PA's side: the PA applies to participate in the compact and names their State of Qualifying License (SQL), then follows the application's progress on their dashboard, and resubmits if the SQL asks for more information.

**User story.** As a PA, I want to apply to participate in the compact and track my application, so that my State of Qualifying License can confirm I am eligible and I can then apply for privileges.

**Flows.** [FLOW-01 end-to-end issuance](../context/flows/01-end-to-end-privilege-issuance.md), Phase 1 · [FLOW-02 SQL verification](../context/flows/02-sql-eligibility-verification.md) (request information and resubmit) · [FLOW-06 state machines](../context/flows/06-state-machines.md) (participation application).

### Acceptance criteria

- A draft application survives logging out.
- Submitting is all-or-nothing and requires a live SQL.
- The PA can withdraw an application.
- Resubmitting returns the application to "submitted" and keeps the SQL's note in its history.
- A document marked required blocks submission with a clear message.
- The dashboard shows what is in the database on load; timelines come from history, not stored events.

---

## 7. Qualifying license records and SQL eligibility review

State side.

**Summary.** Gives states their configuration (fees, required proofs, practice requirements, contacts, going live), lets state staff record PA licenses, and gives the State of Qualifying License a queue and case view to verify each application and decide eligibility. Also runs the 60-day withdrawal clocks and lets the SQL withdraw eligibility.

**User story.** As staff at a PA's State of Qualifying License, I want to record license data and review each participation application in one place, so that I can verify the PA, record my decision through the data system as the rules require, and let eligible PAs move on to privileges.

**Flows.** [FLOW-02 SQL verification](../context/flows/02-sql-eligibility-verification.md) · [FLOW-05 adverse action cascade](../context/flows/05-adverse-action-cascade.md) (withdrawing eligibility) · [FLOW-06 state machines](../context/flows/06-state-machines.md).

### Acceptance criteria

- Only users with write access in the SQL's state can act on its applications.
- A decision requires the license verified and the background check completed.
- A decision cannot be changed, except by withdrawing eligibility; everything is audited.
- State A sees nothing of state B's applications.
- Verifying stamps who verified each identity field group and when, and the PA's dashboard shows "Verified by {state} on {date}".
- A verification document the SQL attaches appears on the practitioner record.
- Fee history is kept; a state that is not live cannot be chosen.
- A state admin cannot edit another state; the contacts directory is not visible to PAs or the public.
- A license whose expiry moves later shows as a renewal in its history.
- A license shows as no longer in effect the day after it expires, with no job needed. ⚠ Under review: the backlog says it "flips to inactive"; the built status computes `expired`.
- Withdrawing eligibility deactivates every privilege in one step.
- A PA whose eligibility was withdrawn cannot start a privilege application.
- Both 60-day clocks (incomplete applications and unpaid privilege requests) have boundary tests. ⚠ Under review: the backlog says unpaid requests are "abandoned"; the adopted rule and the built schema say `withdrawn`.

---

## 8. Privilege application, payment, and remote-state issuance

**Summary.** Phase 2 of the process: an eligible PA picks remote states, pays the state and Commission fees by card in one checkout, and each remote state verifies the PA's proofs and issues or denies the privilege from its own queue.

**User story.** As an eligible PA, I want to choose the states I want to practise in, pay once, and receive my privileges, so that I can practise there without separate licenses. As remote-state staff, I want a queue of paid requests with everything I need to decide, so that I can issue or deny each one quickly.

**Flows.** [FLOW-03 payment and issuance](../context/flows/03-payment-and-remote-state-issuance.md) · [FLOW-01 end-to-end issuance](../context/flows/01-end-to-end-privilege-issuance.md), Phase 2 · [FLOW-06 state machines](../context/flows/06-state-machines.md) (privilege request).

### Acceptance criteria

- Switching between the test payment service and Authorize.net needs no code change. ⚠ Under review: the backlog describes an in-app fake; the constitution requires an out-of-process mock reached by URL.
- A replayed payment webhook does nothing; a declined payment leaves the requests waiting for payment.
- No card data reaches our API (confirmed by ZAP and review); the payment form's accessibility findings are recorded for the audit.
- The total the PA pays matches the server's calculation.
- Requests reach the remote state only after an approved payment. ⚠ Under review: the backlog says requests "exist only after" payment; they are created waiting for payment and become submitted when it is approved.
- The end-to-end test passes.
- A privilege cannot be issued unless participation is eligible, the payment is complete, and every required proof is marked verified. ⚠ Under review: the check should also confirm the PA is not within the 2-year bar and the license is in effect.
- Privilege numbers are unique and increase per state.
- A privilege's expiry stays fixed even if the license is renewed afterwards (tested).

---

## 9. Status changes, adverse actions, expiry, and renewal

**Summary.** Everything that changes a license or privilege after it is issued: states update license status, report disciplinary actions and significant investigative information, privileges cascade accordingly, PAs are warned before a privilege expires, and PAs can renew.

**User story.** As state staff, I want to report a license status change or an adverse action once, so that every affected privilege updates automatically and the right people are told. As a PA, I want to be warned before a privilege expires and be able to renew it, so that I can keep practising without a gap.

**Flows.** [FLOW-04 expiration and renewal](../context/flows/04-expiration-and-renewal.md) · [FLOW-05 adverse action cascade](../context/flows/05-adverse-action-cascade.md) · [FLOW-06 state machines](../context/flows/06-state-machines.md) (privilege status).

### Acceptance criteria

- The cascade matrix covers at least 8 cases and the 2-year bar.
- The computed statuses reflect each cascade, and every affected privilege gets a history row.
- Lifting one of two actions on a privilege leaves it encumbered.
- Tests prove significant investigative information never appears in PA or public responses.
- Each expiry notice (60, 30, and 7 days) is sent once per threshold, with frozen-time boundary tests.
- Renewal is refused until the license's expiry has moved later.
- A renewed privilege keeps its number and issue date.
- Renewal is demonstrated on seed data in `test`.

---

## 10. Practitioner records, Commission dashboard, and reports

**Summary.** Lets state and Commission staff search for practitioners and view their full record (with private fields and SSN reveal gated and audited), gives the Commission an operational dashboard, and provides CSV reports, including the financial reports states use to confirm payment behind each privilege.

**User story.** As state or Commission staff, I want to find a practitioner and see their whole record, and to export operational and financial reports, so that I can answer questions, monitor the compact, and confirm payment behind every privilege.

**Flows.** [FLOW-05 adverse action cascade](../context/flows/05-adverse-action-cascade.md) (confidential records on the practitioner record) · [FLOW-06 state machines](../context/flows/06-state-machines.md) (the statuses search and the dashboard report).

### Acceptance criteria

- State A cannot see a practitioner unrelated to state A.
- Revealing a full SSN is audited with a reason.
- Dashboard numbers match search results.
- The dashboard renders in under 2 seconds on the demo seed, and every chart has a data table.
- Every report has golden-file tests.
- A state user's export contains only their state's rows.

---

## 11. Public privilege verification

**Summary.** A public page where anyone can look up a PA by name or privilege number and see their privileges, active and inactive, with only the fields the Commission allows and never the reason a privilege was deactivated.

**User story.** As an employer or a member of the public, I want to check whether a PA holds a compact privilege in a state, so that I can confirm they may practise there.

**Flows.** [FLOW-05 adverse action cascade](../context/flows/05-adverse-action-cascade.md) (what the public never sees) · [FLOW-06 state machines](../context/flows/06-state-machines.md) (the public status labels).

### Acceptance criteria

- Schema tests prove no private or non-public field can appear in a public response.
- A privilege deactivated by a non-public adverse action shows as inactive, with no reason.
- The rate limit works (429 when exceeded).
- pa11y reports no issues.

---

## 12. Pilot readiness

Accessibility, security validation, documentation, live operations test.

**Summary.** The close-out that proves the system meets the contract: a full accessibility audit, a full security scan and ASVS review, the documentation and transition package, and the live operations test the Commission runs end to end on test data.

**User story.** As the Commission, I want evidence that the system meets the quality standards and passes a live operations test, so that I can accept the MVP and take ownership of it.

**Flows.** All seven, through the live operations test script, which follows [FLOW-01 end-to-end issuance](../context/flows/01-end-to-end-privilege-issuance.md) and adds a status change and public verification.

### Acceptance criteria

- No automated and no manual accessibility findings, with the test plan and results delivered.
- The ZAP report has no medium or high findings, and the security scan report is delivered.
- A new engineer can set up locally and deploy to `test` from the docs alone.
- The live operations test passes end to end and its record is delivered.
- The test data is removed by one documented command. ⚠ Under review: deleting records conflicts with the constitution's "no hard deletes" and "no test data in production"; the proposal is to mark and exclude them instead.
- The launch runbook exists.

---

## 13. State licensee data ingestion

File upload and API.

**Summary.** Lets a state send its licensee data to the system by uploading a CSV in the state portal or through an authenticated API, both using one specification and one validator, built against mock data from representative states.

**User story.** As state licensing staff, I want to send our licensee data by file or API instead of keying it in, so that the license on file is accurate when our staff review a PA's application.

**Flows.** [FLOW-02 SQL verification](../context/flows/02-sql-eligibility-verification.md) (an uploaded license is the on-file record the SQL compares against) · [FLOW-01 end-to-end issuance](../context/flows/01-end-to-end-privilege-issuance.md) ("what the SOW adds"). Open question: [TENSION-04](../context/evidence/tensions/TENSION-04-state-upload-versus-multi-party-record.md).

### Acceptance criteria

- The same batch sent by upload and by API produces the same rows.
- Re-sending a batch does nothing.
- A malformed row is rejected with its line number and reason.
- State A's credential cannot write state B's records.
- An ingested license appears as the on-file record in the SQL's comparison, labelled with its source.
- Changes that would affect a license behind an active privilege are listed and applied only when staff confirm.
- Nothing ingested changes a privilege on its own.

---

## 14. National credentialing integration (NCCPA)

**Summary.** Looks up each PA's NCCPA certification and shows the result beside what the PA entered, flagging any mismatch on the SQL's case view. The real NCCPA connection waits on the NCCPA contract; until then it runs against a test service.

**User story.** As SQL staff, I want to see the PA's certification as NCCPA reports it next to what the PA entered, so that I can verify it with confidence. As a PA, I want my certification checked without extra steps, so that my application moves faster.

**Flows.** [FLOW-02 SQL verification](../context/flows/02-sql-eligibility-verification.md) (the SQL verifies NCCPA certification) · [FLOW-01 end-to-end issuance](../context/flows/01-end-to-end-privilege-issuance.md) (the PA enters it in their profile).

### Acceptance criteria

- Switching between the test service and NCCPA needs no code change. ⚠ Under review: the test service must be an out-of-process mock reached by URL (constitution Principle IV).
- If NCCPA times out, neither saving the profile nor the SQL's decision is blocked.
- Every lookup is audited.
- No NCCPA credential is in the repo.
