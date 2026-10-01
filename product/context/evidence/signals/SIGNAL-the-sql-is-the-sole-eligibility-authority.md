---
signal-id: SIGNAL-the-sql-is-the-sole-eligibility-authority
strength: strong
date-validated: 2026-09-30
validated-by: CTO (Kalish)
tags: sql, eligibility, state-scoping, two-phase-workflow
---

> **Needs review (2026-10-01, SCRUM-39).** This file cites four atoms that quoted draft rule text. That text changed when Rules 3 and 4 were adopted on 2026-04-06. `ATOM-GOV-R23-05` is replaced by `ATOM-GOV-R3-01`; `ATOM-GOV-R23-06` is replaced by `ATOM-GOV-R3-02`; `ATOM-GOV-R23-12` is replaced by `ATOM-GOV-R3-03`; `ATOM-GOV-R23-15` is replaced by `ATOM-GOV-R3-06`. The draft and adopted text are side by side in `product/context/evidence/CHANGES-2026-10-01-adopted-rules.md`. Remove this note when the file is updated.

# SIGNAL — The State of Qualifying License is the sole eligibility authority

## Pattern

Only the state the PA designates as their State of Qualifying License decides whether the PA may participate in the compact: it evaluates eligibility, runs the background check, confirms the designation basis, issues the verdict through the data system, re-confirms at renewal, and can withdraw the verdict. Remote states act on that notice; they do not re-verify, and once the SQL withdraws eligibility they "do not have a say" in whether privileges continue. This is why the workflow is two-phase and why state-portal permissions are scoped by role-in-relation-to-the-PA, not by a flat "state user" role.

## Supporting atoms

- `ATOM-GOV-R23-01` — rule: the PA designates one SQL by residence, practice, employer, or tax basis
- `ATOM-GOV-R23-05` — rule: the participation application goes to the SQL, with a sworn statement and CBC through the SQL's process
- `ATOM-GOV-R23-06` — rule: the SQL's four duties, ending in a notice "through the data system"
- `ATOM-GOV-R23-12` — rule: the SQL re-verifies continued eligibility at renewal
- `ATOM-GOV-R23-15` — rule: SQL withdrawal auto-cancels every privilege with no remote-state action
- `ATOM-GOV-M0209-02` — minutes: "the remote states do not have a say in the privileges continuing"
- `ATOM-GOV-RFP-02` — RFP priority story: state admin wants to "easily confirm qualifying licenses" and see PAs "utilizing my state as the state of qualifying license"

Distinct sources: 3 (R23, M0209, RFP).

## Implications for the build

- L-05 is a first-class state-portal capability with its own queue and case view; it has no CompactConnect precedent.
- Remote-state issuance (P-03) is gated on `participation_applications.status = eligible` and never re-runs eligibility checks.
- Eligibility withdrawal (L-06) cascades atomically to every privilege and notifies remote states after the fact, not for approval.
- Permission checks resolve "is this user's state the SQL for this PA?" (write on applications) separately from "is this user's state a remote state for this PA?" (write on privilege requests).
