---
signal-id: SIGNAL-the-system-does-the-heavy-lifting-for-states
strength: strong
date-validated: 2026-09-30
validated-by: CTO (Kalish)
tags: commission-role, system-responsibility, notifications, fees, events
---

> **Needs review (2026-10-01, SCRUM-39).** This file cites one atom that quoted draft rule text. That text changed when Rules 3 and 4 were adopted on 2026-04-06. `ATOM-GOV-R23-06` is replaced by `ATOM-GOV-R3-02`. The draft and adopted text are side by side in `product/context/evidence/CHANGES-2026-10-01-adopted-rules.md`. Added 2026-10-02 (SCRUM-39): `ATOM-GOV-M1110-02` is replaced by `ATOM-GOV-M1110-04`, which adds the turns before it. J. Alley: "there is a need to know the PAs in your state who are practicing with your state as their SQL". The adopted Rule 3.5(c)(2) has the state issue the renewal notice "through the data system". Added 2026-10-02 (SCRUM-39): one claim to re-check. The signal says the system tracks "which PAs use which SQL" so state staff do not have to. `ATOM-GOV-M1110-04` records that the state still needs to know, and Rule 3.5(c)(2) has the state send the renewal notice "through the data system". Remove this note when the file is updated.

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
