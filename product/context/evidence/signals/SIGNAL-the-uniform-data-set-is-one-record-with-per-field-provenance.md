---
signal-id: SIGNAL-the-uniform-data-set-is-one-record-with-per-field-provenance
strength: strong
date-validated: 2026-09-30
validated-by: CTO (Kalish)
tags: uniform-data-set, data-model, provenance, sql-verification, pa-entered, commission-generated
---

> **Needs review (2026-10-01, SCRUM-39).** This file cites two atoms that quoted draft rule text. That text changed when Rules 3 and 4 were adopted on 2026-04-06. `ATOM-GOV-R23-06` is replaced by `ATOM-GOV-R3-02`; `ATOM-GOV-R5-02` is replaced by `ATOM-GOV-R4-01`. The draft and adopted text are side by side in `product/context/evidence/CHANGES-2026-10-01-adopted-rules.md`. Added 2026-10-02 (SCRUM-39): `ATOM-GOV-R5-03` is replaced by `ATOM-GOV-R4-03`. The adopted Rule 4.3(d) adds "where applicable" after "shall verify and submit". See the change index. Remove this note when the file is updated.

# SIGNAL — The uniform data set is one record with per-field provenance

## Pattern

The statute says a participating state "shall submit a uniform data set," but the rules and the committee's own reading treat the uniform data set as a single Commission-held record per PA that several parties contribute to, each verifying its own lane. The PA enters the application, attestations, and later address and email changes directly into the Commission's system. The SQL "verifies and submits" the identity, education, certification, license, and discipline fields. Each remote state verifies and submits its privilege fields. The Commission itself generates fields no state authors, such as denials and compact-level ineligibility periods. When the committee faced the one field where the PA and the state could disagree, the address, it settled on the PA updating in the system, the update propagating to states, and the SQL following up if concerned. "Submit" is therefore satisfied by a state's verification act inside the system, not by a separate state upload that competes with what the PA entered.

## Supporting atoms

- `ATOM-GOV-ML-14` — statute: a participating state shall submit a uniform data set "as required by the Rules of the Commission"
- `ATOM-GOV-R5-02` — rule: the SQL shall "verify and submit" the 15 practitioner fields
- `ATOM-GOV-R5-03` — rule: the remote state shall "verify and submit" the privilege fields
- `ATOM-GOV-R5-04` — rule: PA-provided address and email changes, and the PA's applications and attestations, are part of the uniform data set
- `ATOM-GOV-R23-03` — rule: the Commission provides the online application and routes it to the SQL
- `ATOM-GOV-R23-06` — rule: the SQL receives the application through the Commission and evaluates eligibility
- `ATOM-GOV-M0825-01` — minutes: the drafter separated "things that would be submitted by the state" from "things that would be maintained by the commission within the data system"
- `ATOM-GOV-M0825-02` — minutes: on address, "If a PA comes to the system to update their address, that would be populated to all the member states. If the state of qualifying license had concerns, they could follow up with the PA."

Distinct sources: 4 (ML, R5, R23, M0825).

## Implications for the build

- The data model (F-02) holds one PA record with per-field provenance: who entered the value, who verified it, and when. The SQL's confirmation on the eligibility review screen is recorded as that state's submission of the 5.3(c) fields, and the documents it attaches are retained under 5.3(e)(4).
- Fields split by author. PA-entered and SQL-verified: names, sex, DOB, SSN, NPI, address, phone, email, education, NCCPA number. State-only: license number, status, issue and expiration dates, adverse actions, significant investigative information, licensure denials (L-01). Remote-state-only: privilege number, status, dates, privilege adverse actions (P-03). Commission-computed: compact ineligibility periods and denial associations. Third-party where the Commission chooses it: current NCCPA status (5.2(c), 5.3(e)(5)).
- PA edits to verified fields after verification stay PA-owned. History records the change and it propagates to states with a relationship to the PA (U-03, D-01); the "re-verification needed" flag is the optional follow-up already listed in the backlog. This is the address ruling from `ATOM-GOV-M0825-02` applied generally, and matches the backlog defaults in Q-04 and Q-10.
- Residual question for Commission counsel, folded into Q-04: confirm that an in-system verification by SQL staff satisfies "verify and submit" under Rule 4 §4.3(b) and ML §8.B, so no separate state-side data feed is expected at pilot.
- Related: `SIGNAL-the-system-does-the-heavy-lifting-for-states` (the Commission's system carries the mechanics; states verify and decide).
