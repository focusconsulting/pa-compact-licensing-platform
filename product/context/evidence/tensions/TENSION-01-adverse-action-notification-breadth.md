---
tension-id: TENSION-01-adverse-action-notification-breadth
date-surfaced: 2026-09-30
surfaced-by: CTO (Kalish)
status: open
---

# TENSION-01 — Who must be told about an adverse action?

## Positions

- **Statute (ML §8.D):** "The Commission shall promptly notify **all** Participating States of any Adverse Action … This Adverse Action information shall be available to any other Participating State." — `ATOM-GOV-ML-16`
- **Draft rule (R5 §5.6(b)):** "it shall promptly notify **each Participating State where the PA holds a Qualifying License or a Compact Privilege**" — `ATOM-GOV-R5-09`
- **Committee direction (Feb 9 2026):** on the related SQL-change clause, "distributed" was changed to "accessible" because "Participating states where the applicant is not requesting a privilege may not want the information forwarded to them." — `ATOM-GOV-M0209-03`

## Why it matters

It sets the recipient list for the `adverse_action.reported` event (F-11) and whether the commission and state portals expose adverse actions on PAs a state has no relationship with (D-01, A-02). Reading the statute literally means every participating state's adverse-action mailbox receives every report; reading the rule means only related states are notified and the rest can look it up. The two readings can be reconciled ("notify" = push to related states, "available" = searchable by any state), but that reconciliation is the Commission's to make, not ours.

## Proposed resolution path

Gates F-11, A-02, D-01; raised with the Commission as Q-20 in `product/backlog/mvp-ticket-breakdown.md` §6.

Default in the backlog: follow the rule — push to states where the PA holds a QL, privilege, or open request; satisfy "available to any other Participating State" by letting any state user find the record through D-01 search with the confidentiality banner. Put the question to the Commission's rules counsel as Q-20 and record the answer here under `## Resolution`.
