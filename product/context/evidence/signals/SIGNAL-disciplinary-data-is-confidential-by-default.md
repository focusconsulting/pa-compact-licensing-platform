---
signal-id: SIGNAL-disciplinary-data-is-confidential-by-default
strength: borderline
date-validated: 2026-09-30
validated-by: CTO (Kalish)
tags: confidentiality, adverse-action, sii, public-data, access-control
---

# SIGNAL — Disciplinary data is confidential by default

## Pattern

The uniform data set is confidential except for a PA's name and the states where they hold a qualifying license or privilege. A contributing state can mark what it reports as not-shareable with the public, and a participating state can only see the records of PAs who hold a license or privilege in that state. Anything beyond that — adverse-action detail, the existence of investigative information — is scoped to states, not to the PA and never to the public.

## Supporting atoms

- `ATOM-GOV-ML-17` — statute: contributing states may designate information not shareable with the public; it is still reported to the Commission
- `ATOM-GOV-R5-06` — rule: uniform data sets are confidential except names and states of QL/privilege
- `ATOM-GOV-R5-08` — rule: a state's access is limited to PAs holding a QL or privilege in that state

Distinct sources: 2 (ML, R5) → **borderline** under signal-strength-check. Three further atoms were proposed and struck at review (`ML-15` SII available only to participating states; `R5-07` sealed and no redisclosure; `RFP-04` priority story on protecting confidential information). Approving any one of them would make this STRONG with 3 sources.

## Implications for the build

- V-01's public response schema is an allow-list (name, states, and whatever Q-12 adds), enforced by schema tests.
- `adverse_actions.is_public` defaults to false; SII is a flag with contact info, visible only in state and commission portals, never emailed to the PA.
- D-01 search scoping is by relationship to the PA (SQL, request, privilege in my state), not by "any state user".
