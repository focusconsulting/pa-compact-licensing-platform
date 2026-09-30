---
signal-id: SIGNAL-the-system-does-the-heavy-lifting-for-states
strength: strong
date-validated: 2026-09-30
validated-by: CTO (Kalish)
tags: commission-role, system-responsibility, notifications, fees, events
---

# SIGNAL — The system does the heavy lifting for states

## Pattern

The rules assign the Commission — and in practice its data system — the mechanics of the compact: the online application, routing it to the SQL, carrying the SQL's notice, collecting and remitting fees, and tracking which PAs use which SQL and when their privileges come due. State staff are expected to verify and decide, not to track, chase, or forward. Where a draft rule implied the Commission had to push information to every state, the committee changed it to "accessible" so states are not flooded with records they have no relationship to.

## Supporting atoms

- `ATOM-GOV-R23-03` — rule: Commission provides the application, facilitates SQL review, collects and remits fees
- `ATOM-GOV-R23-06` — rule: the SQL's notice is issued "through the data system"
- `ATOM-GOV-M1110-02` — minutes: "The system should be doing the heavy lifting there … flagging this as a need for data system developers"
- `ATOM-GOV-M0209-03` — minutes: "distributed" → "accessible"; states not involved should not have data forwarded to them
- `ATOM-GOV-RFP-02` — RFP priority story: state admin wants confirmation, issuance, data access, and financial tracking to be easy

Distinct sources: 4 (R23, M1110, M0209, RFP).

## Implications for the build

- Domain events and the transactional outbox are foundation (decision D2, F-05); every state-facing notification is a consumer, and every renewal or expiry is a job the system runs (F-13, A-04).
- Fee line items are tagged by state at payment time (P-02) so the Commission can remit and report per state (C-02) even though reconciliation is out of scope.
- Notifications go to states with a relationship to the PA; broader visibility is search (D-01), not email. See TENSION-01 for the statute/rule gap on adverse-action breadth.
