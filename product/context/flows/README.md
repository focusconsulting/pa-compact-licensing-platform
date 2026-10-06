---
artifact: flow-index
status: draft
authored-by: CTO (Kalish)
last-revised: 2026-10-05
---

# Flows — PA Compact Data System

Cross-story workflow definitions for the MVP. Each flow is one file with `artifact: flow` front matter so a story's spec can cite it (`product/context/flows/<file>`) instead of restating it. Flows are derived from the compact rules in the research corpus; every step that a rule forces carries its citation. Where a flow describes something the pilot defers (`product/backlog/mvp-ticket-breakdown.md` §5.1), the deferred part is kept under a "Deferred" heading so the build does not paint it out.

The journey these flows serve, with the assumptions and open questions for the Commission, is on the Research and Usability page: <https://focusdigital.atlassian.net/wiki/spaces/PC/pages/69074952>. Which of the 14 items in Rule 4.3(c) a state or FSMB can supply is on the license data comparison page: <https://focusdigital.atlassian.net/wiki/spaces/PC/pages/71663618>.

| ID | File | What it covers | Feeds tickets |
|---|---|---|---|
| FLOW-01 | [01-end-to-end-privilege-issuance.md](01-end-to-end-privilege-issuance.md) | Account → participation → privilege, the whole happy path; the uniform data set's three writers; where we differ from CompactConnect | U-01, U-03, L-01, L-03, L-04, L-05, P-01, P-02, P-03 |
| FLOW-02 | [02-sql-eligibility-verification.md](02-sql-eligibility-verification.md) | Phase 1 state side: the SQL's four duties as its "verify and submit", note + resubmit, decision, abandonment | L-01, L-03, L-04, L-05, L-06 |
| FLOW-03 | [03-payment-and-remote-state-issuance.md](03-payment-and-remote-state-issuance.md) | Phase 2: state selection and per-state proofs, fee calculation, Authorize.net, webhook, issuance/denial | P-01, P-02, P-03, S-01 |
| FLOW-04 | [04-expiration-and-renewal.md](04-expiration-and-renewal.md) | Pinned expiry, 60/30/7 notices, expiry; the renewal flow (deferred) | A-04, L-04, P-01 |
| FLOW-05 | [05-adverse-action-cascade.md](05-adverse-action-cascade.md) | QL adverse action → all privileges deactivated; lift; 2-year bar; eligibility withdrawal; the CompactConnect dialogs we reuse | A-01, A-02, L-06 |
| FLOW-06 | [06-state-machines.md](06-state-machines.md) | Participation application, privilege request, privilege status | F-02, L-05, P-03 |
| FLOW-07 | [07-domain-event-catalogue.md](07-domain-event-catalogue.md) | Every domain event, its producer and consumers (the F-05 contract); deferred events reserved by name | F-05, F-11, F-13 |

## SOW alignment (redline response v2, 2026-10-05)

The SOW at `product/context/PA Compact Data System SOW - Focus Consulting.md` was replaced on 2026-10-05 with the redline response v2. Three changes bear on these flows:

- **§2.1 is a candidate list.** It is now "Expected Core MVP Functional Capabilities": the anticipated universe of features, an input to backlog prioritisation with the Commission's Product Manager, and "not a fixed requirements list". The list also grew, mostly on the state side.
- **§2.2 "Out of Scope" is gone.** Two of its items moved into §2.1 (integration with national credentialing organizations; payment reconciliation and financial reporting). The rest are now "Additional MVP Capabilities" that may be added through the agile process.
- **§2.3 changed.** It no longer says the 72-hour issuance goal is "not a system-level SLA". Acceptance adds a live operations test of end-to-end issuance in a pilot environment using Commission-controlled test data. Live pilot operations, state coordination, and state system integration are out of scope for the period of performance.

The deferred list in `product/backlog/mvp-ticket-breakdown.md` §5.1, and its "Dropped from v1 (not in SOW)" line, were derived from the earlier SOW and have not been re-derived. Where a flow still says "deferred (§5.1)" for something §2.1 now lists, the flow says so; the deferral stands until the backlog is re-prioritised with the Commission.

| SOW §2.1 item | Change | Flows | State of the flow |
|---|---|---|---|
| PA: renew privileges | new | FLOW-04, FLOW-06, FLOW-07 | Drawn in FLOW-04, still marked deferred; needs a prioritisation decision |
| PA: verify military affiliation | new | FLOW-01 | No step. The SOW does not say what the verification is for |
| PA: receive confirmation of timely privilege issuance | "timely" added; the "not a system-level SLA" sentence removed from §2.3 | FLOW-01, FLOW-03 | Covered. The 72-hour target now rests on the RFP Q&A alone |
| PA: submit qualifying license for verification; State: verify qualifying licenses | removed from the list | FLOW-01, FLOW-02 | Steps kept: the compact rules require them (R3r §3.4(a)–(b)) |
| State: upload PA identifying information and licensure data; upload the uniform data set via API (also §3 Phase 2, "multi-format: API and upload") | new | FLOW-01, FLOW-02 | Plug-in point named in both flows; the ingestion flow itself is not drawn. Open: `TENSION-04-state-upload-versus-multi-party-record` |
| State: verify completion of jurisprudence exam requirements | new | FLOW-03 | Covered by the proof review on the case view; whether the state records a separate verification is open |
| State: receive notifications of compact privilege requests | new | FLOW-03, FLOW-07 | Covered (`privilege.requested` → RS ops) |
| State: view privilege issuance, renewal, and expiration data | new | FLOW-03, FLOW-04 | Issuance and expiry are covered by notices and practitioner records; renewal data arrives with the renewal flow |
| State: upload and view state licensing administrator contact information | new | none | Not in any flow |
| State: upload state practice requirements | new | FLOW-03 | The flow carries a per-state URL (S-01); an upload is not drawn |
| State: access state financial transactions | new | FLOW-03 | The data exists (line items tagged by state); a state-side view is not drawn |
| State: verify the existence of significant investigatory and disciplinary information | new | FLOW-02, FLOW-05 | Covered |
| State: notify member states of license status changes, including adverse action and significant investigatory information | new | FLOW-05, FLOW-07 | Covered |
| Commission: integrate with national credentialing organizations | moved in from "Out of Scope" | FLOW-01, FLOW-02 | Not drawn; NCCPA certification is PA-entered and SQL-verified today |
| Commission: payment reconciliation and financial reporting to member state administrators | moved in from "Out of Scope" | FLOW-03 | Not drawn. §7.4 still says Focus "will not be responsible for financial reconciliation or settlement" |
| Public verification of active and inactive privileges | "and inactive" added | FLOW-05, FLOW-06 | Covered by the status vocabulary; FLOW-05 adds the confidentiality invariant |

## Actors used in every diagram

- **PA** — physician assistant (role `licensee`)
- **SQL staff** — state board user in the PA's State of Qualifying License (`write` on that state)
- **RS staff** — state board user in a Remote State
- **Commission** — commission staff (`compact_admin`)
- **Web** — Next.js client · **API** — FastAPI · **DB** — Postgres (tables + `domain_events` outbox, one transaction)
- **Worker** — event dispatcher + scheduled jobs (ECS task) · **Email** — SES (maildev locally) · **Pay** — Authorize.net (fake provider locally)

## Shape of every write

Validate → write rows + history + audit + `domain_events` row in **one transaction** → return. The Worker reads `domain_events`, fans out to idempotent handlers (notifications, cascades, metrics), and marks each event handled. Nothing sends email or cascades inside a request. See decision D2 in `product/backlog/mvp-ticket-breakdown.md` §2.1.

## The record the flows move

All seven flows write to one Commission-held record per PA, the **uniform data set** (R5 §5.3). The PA enters the identity fields (FLOW-01 Phase 0), the SQL verifies them and authors the license fields (FLOW-02), each remote state authors its privilege fields (FLOW-03), and the Commission computes what no state authors (denials, ineligibility periods). Every field carries who entered it, who verified it, and when; every change is history (FLOW-07). See `SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance`.

## Sources

The rules these flows encode are ingested under `product/context/research-corpus/sources/` (see `INDEX.md`). Each flow carries `atoms:` and `signals:` in its front matter and an `## Evidence` section; the atoms live in `product/context/evidence/atoms/` and quote the converted sources by line.

- `sources/pa-compact-model-legislation.md` — **ML**
- `sources/pa-compact-rule-2-and-3-drafts.md` — **R2r / R3r** (redlines approved Feb 9 2026)
- `sources/pa-draft-rules-2_3_5.md` — **R5** (data-system rule, renumbered to Rule 4 on Nov 10 2025)
- `sources/minutes-august-25-2025-rules-committee-amended-approved.md`, `sources/minutes-nov-10-2025-rules-committee-approved.md`, and `sources/rules-committee-feb-9-2026-minutes-amended-approved.md` — committee decisions
- `sources/pa-compact-commission-data-system-rfp.md` — RFP priority stories
- `product/context/PA Compact Data System SOW - Focus Consulting.md` — **SOW** (redline response v2; the RFP is its Exhibit A)
- `sources/compactconnect-staff-user-guide.md` and `sources/compactconnect-backend-design.md` — the reference implementation's own documentation

How these flows compare to CompactConnect's, as a product analysis, is in `product/context/reference/compactconnect-crosswalk.md` (§2 for the four rule-driven differences, §3–§6 per persona, §10 for the screen map); the screen captures each flow names are in `product/context/reference/compactconnect-screens/`. Each flow points at the crosswalk sections it draws on in its `see-also`.

Rendered version of the 2026-09-29 draft of all seven flows: <https://claude.ai/artifact/NHKAjy3Ci1i6ia7nMGJnZY> (private; predates this revision).
