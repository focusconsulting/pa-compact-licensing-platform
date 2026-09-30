---
artifact: flow
flow-id: FLOW-07
title: Domain event catalogue (F-05 contract)
status: draft
authored-by: CTO (Kalish)
last-revised: 2026-09-30
sources:
  - product/context/research-corpus/sources/pa-draft-rules-2_3_5.md
  - product/context/research-corpus/sources/minutes-august-25-2025-rules-committee-amended-approved.md
rules-cited: [R5 §5.3(e), R5 §5.6(b), ML §8.C]
tickets: [F-05, F-11, F-13, U-03, L-03, L-05, L-06, P-02, P-03, A-01, A-02, A-04]
decisions: [D2, D7, D8, D15]
see-also: [FLOW-01, FLOW-02, FLOW-03, FLOW-04, FLOW-05, compactconnect-crosswalk §3.7]
atoms: [ATOM-GOV-ML-16, ATOM-GOV-R5-04, ATOM-GOV-R5-09, ATOM-GOV-R23-10, ATOM-GOV-M0209-03, ATOM-GOV-M0825-02]
tensions: [TENSION-01-adverse-action-notification-breadth]
signals: [SIGNAL-the-system-does-the-heavy-lifting-for-states, SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance]
---

# FLOW-07 — Domain event catalogue

The producer writes the event in the same transaction as the change (transactional outbox, decision D2). Consumers are idempotent on `(event_id, handler)`. F-05 ships a test that every event type listed here has at least one test; adding an event means adding a row here.

## Events the pilot builds

| Event | Producer | Consumers |
|---|---|---|
| `practitioner.registered` | U-01 | notify PA (welcome) |
| `practitioner.profile_changed` | U-03 | history; propagate the change to every state where the PA has an application, QL, or privilege (`ATOM-GOV-M0825-02`); D-01 shows the history |
| `practitioner.email_change_requested` | U-03 | send the verification code to the new address (15-minute window), tell the old address (CompactConnect's pattern, crosswalk §3.2) |
| `application.submitted` | L-03 | notify PA, notify SQL ops |
| `application.info_requested` | L-05 | notify PA (link only, never the note) |
| `application.resubmitted` | L-03 | notify SQL ops; history keeps the note and the resubmission (D15) |
| `application.eligible` / `.denied` | L-05 | notify PA (denial carries the appeal text); notify Commission ops; metrics (time_to_decision) |
| `application.withdrawn` | L-06 job / PA | notify PA, SQL ops |
| `application.eligibility_withdrawn` | L-06 | cascade cancel privileges; notify PA, RS ops |
| `privilege.requested` | P-02 (on payment) | notify PA receipt (itemised), RS ops |
| `payment.declined` | P-02 | notify PA |
| `privilege.issued` / `.denied` | P-03 | notify PA; SQL ops; Commission ops; metrics (time_to_issue) |
| `privilege.deactivated` | A-01 / A-02 / L-06 | notify PA (with the state's note), issuing RS |
| `privilege.expiring` (60 / 30 / 7) | A-04 job | notify PA |
| `privilege.expired` | A-04 job | notify PA; history |
| `qualifying_license.status_changed` | L-01 / A-01 | cascade privileges; notify PA, RS ops |
| `adverse_action.reported` / `.lifted` | A-02 | cascade; notify PA, all states with QL/privilege, Commission [R5 §5.6(b)]; metrics (reporting timeliness) |
| `sii.flagged` / `.closed` | A-02 | notify states with QL/privilege only — never the PA [ML §8.C] |

Every producer above also writes a history row; history is the consumer that makes the record "include all changes" (R5 §5.3(e)) and feeds the dashboard timelines (L-04, D-01), which are rendered from history rows, not from stored events.

The PA-facing emails this table produces are, in order of the PA's journey: welcome, application received, information requested (link only), eligible or denied (with appeal text), payment receipt, privilege issued or denied per state, deactivated, adverse action reported or lifted, expiring at 60 / 30 / 7 days, expired, email-change code (crosswalk §3.7). SII is never mentioned to the PA.

## Deferred events (§5.1)

Listed so the names are reserved and the producers know where they plug in.

| Event | Returns with | Consumers |
|---|---|---|
| `case_message.posted` | case message thread (D15 fallback after usability round 2) | notify the other party (link only) |
| `renewal.requested` / `.eligible` / `.denied` | renewal flow (FLOW-04) | notify SQL ops / PA |
| `payment.settled` / `.returned` | ACH / settlement job (FLOW-03) | reports; gate issuance / deactivate |
| `user.invited` / `.deactivated` | staff user-management UI (U-02) | notify user |

## Runtime

- Production: the Worker (`python -m licensing_api.worker`) runs as an ECS service draining `domain_events`; scheduled jobs are EventBridge Scheduler → ECS run-task on the same image (decision D8).
- Local and test: `WORKER_MODE=inline` drains after each request, so a developer sees the email land in maildev without a second container.
- A handler that throws is retried, then dead-lettered with an alarm; replaying an event is a no-op.

## Evidence

Atoms are in `product/context/evidence/atoms/`; signals and tensions beside them. Rule section references above resolve to these IDs.

- `ATOM-GOV-R5-09`, `ATOM-GOV-ML-16`, `ATOM-GOV-M0209-03` — recipients of `adverse_action.reported` (see `TENSION-01`)
- `ATOM-GOV-R23-10` — `privilege.expiring` at 60 days is the rule minimum
- `ATOM-GOV-R5-04` — why history rows are consumers of every change
- `ATOM-GOV-M0825-02` — why `practitioner.profile_changed` propagates to states rather than waiting for the SQL
- `SIGNAL-the-system-does-the-heavy-lifting-for-states`
- `SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance`
