---
artifact: flow-index
status: draft
authored-by: CTO (Kalish)
last-revised: 2026-09-30
---

# Flows — PA Compact Data System

Cross-story workflow definitions for the MVP. Each flow is one file with `artifact: flow` front matter so a story's spec can cite it (`product/context/flows/<file>`) instead of restating it. Flows are derived from the compact rules in the research corpus; every step that a rule forces carries its citation. Where a flow describes something the pilot defers (`product/backlog/mvp-ticket-breakdown.md` §5.1), the deferred part is kept under a "Deferred" heading so the build does not paint it out.

| ID | File | What it covers | Feeds tickets |
|---|---|---|---|
| FLOW-01 | [01-end-to-end-privilege-issuance.md](01-end-to-end-privilege-issuance.md) | Account → participation → privilege, the whole happy path; the uniform data set's three writers; where we differ from CompactConnect | U-01, U-03, L-01, L-03, L-04, L-05, P-01, P-02, P-03 |
| FLOW-02 | [02-sql-eligibility-verification.md](02-sql-eligibility-verification.md) | Phase 1 state side: the SQL's four duties as its "verify and submit", note + resubmit, decision, abandonment | L-01, L-03, L-04, L-05, L-06 |
| FLOW-03 | [03-payment-and-remote-state-issuance.md](03-payment-and-remote-state-issuance.md) | Phase 2: state selection and per-state proofs, fee calculation, Authorize.net, webhook, issuance/denial | P-01, P-02, P-03, S-01 |
| FLOW-04 | [04-expiration-and-renewal.md](04-expiration-and-renewal.md) | Pinned expiry, 60/30/7 notices, expiry; the renewal flow (deferred) | A-04, L-04, P-01 |
| FLOW-05 | [05-adverse-action-cascade.md](05-adverse-action-cascade.md) | QL adverse action → all privileges deactivated; lift; 2-year bar; eligibility withdrawal; the CompactConnect dialogs we reuse | A-01, A-02, L-06 |
| FLOW-06 | [06-state-machines.md](06-state-machines.md) | Participation application, privilege request, privilege status | F-02, L-05, P-03 |
| FLOW-07 | [07-domain-event-catalogue.md](07-domain-event-catalogue.md) | Every domain event, its producer and consumers (the F-05 contract); deferred events reserved by name | F-05, F-11, F-13 |

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
- `sources/compactconnect-staff-user-guide.md` and `sources/compactconnect-backend-design.md` — the reference implementation's own documentation

How these flows compare to CompactConnect's, as a product analysis, is in `product/context/reference/compactconnect-crosswalk.md` (§2 for the four rule-driven differences, §3–§6 per persona, §10 for the screen map); the screen captures each flow names are in `product/context/reference/compactconnect-screens/`. Each flow points at the crosswalk sections it draws on in its `see-also`.

Rendered version of the 2026-09-29 draft of all seven flows: <https://claude.ai/artifact/NHKAjy3Ci1i6ia7nMGJnZY> (private; predates this revision).
