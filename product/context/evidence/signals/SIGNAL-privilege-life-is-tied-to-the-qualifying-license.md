---
signal-id: SIGNAL-privilege-life-is-tied-to-the-qualifying-license
strength: strong
date-validated: 2026-09-30
validated-by: CTO (Kalish)
tags: privilege-lifecycle, expiration, renewal, computed-status
---

> **Needs review (2026-10-01, SCRUM-39).** This file cites one atom that quoted draft rule text. That text changed when Rules 3 and 4 were adopted on 2026-04-06. `ATOM-GOV-R23-12` is replaced by `ATOM-GOV-R3-03`. The draft and adopted text are side by side in `product/context/evidence/CHANGES-2026-10-01-adopted-rules.md`.  Added 2026-10-02 (SCRUM-39): `ATOM-GOV-R23-09` is replaced by `ATOM-GOV-R3-07`. The adopted Rule 3.5(a) adds "or the qualifying license is voluntarily terminated by the PA" and "in accordance with Section 4.A of the model legislation". See the change index. Added 2026-10-02 (SCRUM-39): `ATOM-GOV-M1110-02` is replaced by `ATOM-GOV-M1110-04`, which adds the turns before it. J. Alley: "there is a need to know the PAs in your state who are practicing with your state as their SQL". The adopted Rule 3.5(c)(2) has the state issue the renewal notice "through the data system". Remove this note when the file is updated.

# SIGNAL — Privilege life is tied to the qualifying license

## Pattern

A compact privilege has no lifecycle of its own. Its validity, its expiration date, and its survival all derive from the qualifying license the PA relied on when they applied: the privilege is valid until that license expires or is revoked, its expiration is pinned to the license expiry in effect on the application date, renewing the license does not extend it, and renewal is a fresh issuance on the same privilege number after the SQL re-confirms eligibility. The rules committee expects the data system, not state staff, to track this coupling.

## Supporting atoms

- `ATOM-GOV-ML-09` — statute: privilege valid until QL expiration or revocation; QL adverse action removes it everywhere
- `ATOM-GOV-ML-12` — statute: privilege expires when the QL it was applied under expires
- `ATOM-GOV-R23-09` — rule: expiration pinned to the QL expiry on the application date; QL renewal does not renew the privilege
- `ATOM-GOV-R23-11` — rule: grace while the SQL has not yet updated an expired-but-active QL
- `ATOM-GOV-R23-12` — rule: SQL re-verifies continued eligibility at renewal
- `ATOM-GOV-M1110-02` — minutes: "the system should be doing the heavy lifting" on tracking renewals
- `ATOM-GOV-RFP-03` — RFP priority story: PA wants an expiration notice so they can renew

Distinct sources: 4 (ML, R23, M1110, RFP).

## Implications for the build

- Privilege status is computed on read from `expiration_date` + administrator flags + adverse actions (decision D1); no job flips it.
- `privileges.expiration_date` is a snapshot taken at request time (P-03), never a foreign key to the license's current expiry.
- Renewal (A-04) is `renewal_check` → SQL verdict → re-request through P-01 → re-issue keeping `privilege_number` and `issued_at`.
- QL status changes (L-01/A-01) cascade to privileges by event, never by editing privilege rows directly.
