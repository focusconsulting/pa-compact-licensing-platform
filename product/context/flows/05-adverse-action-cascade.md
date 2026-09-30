---
artifact: flow
flow-id: FLOW-05
title: Adverse action on the qualifying license — cascade, lift, eligibility withdrawal
status: draft
authored-by: CTO (Kalish)
last-revised: 2026-09-30
sources:
  - product/context/research-corpus/sources/pa-compact-model-legislation.md
  - product/context/research-corpus/sources/pa-compact-rule-2-and-3-drafts.md
  - product/context/research-corpus/sources/pa-draft-rules-2_3_5.md
  - product/context/research-corpus/sources/minutes-nov-10-2025-rules-committee-approved.md
rules-cited: [ML §4.A.8, ML §4.B, ML §4.C, ML §6.A, ML §6.B.1, ML §6.G, R3r §3.8(b), R5 §5.4, R5 §5.5(c), R5 §5.6(b)]
tickets: [A-01, A-02, L-06, C-01]
decisions: [D1, D2, D9]
open-questions: [Q-16, Q-17]
see-also: [FLOW-02, FLOW-06, compactconnect-crosswalk §4.7]
atoms: [ATOM-GOV-ML-03, ATOM-GOV-ML-07, ATOM-GOV-ML-09, ATOM-GOV-ML-11, ATOM-GOV-ML-16, ATOM-GOV-ML-17, ATOM-GOV-R23-15, ATOM-GOV-R5-05, ATOM-GOV-R5-06, ATOM-GOV-R5-09, ATOM-GOV-M0209-02, ATOM-GOV-M0209-03]
tensions: [TENSION-01-adverse-action-notification-breadth]
signals: [SIGNAL-disciplinary-data-is-confidential-by-default, SIGNAL-the-sql-is-the-sole-eligibility-authority]
---

# FLOW-05 — Adverse action on the qualifying license

ML §4.B / §6.G: an adverse action on the QL deactivates **every** privilege. There is no automatic reinstatement; the PA may apply again two years after the restriction ends (ML §4.A.8, §4.C). An adverse action against a **single privilege**, reported by that remote state (ML §6.B.1), affects only that privilege.

```mermaid
sequenceDiagram
    autonumber
    participant SQL as SQL staff
    participant API
    participant DB
    participant Worker
    participant Email
    participant PA
    participant RS as Remote states

    SQL->>API: POST /states/{sql}/adverse-actions {against=qualifying_license, type, npdb_category[], summary, order_date, effective_start, is_public, is_emergency, attachment?, sii?{contact, description}}
    API->>DB: adverse_action row, every active privilege → administrator_status=inactive, deactivation_reason=qualifying_license_adverse_action, history rows, events adverse_action.reported + privilege.deactivated ×N (one transaction)
    Worker->>Email: PA "privileges deactivated" (with rule citation)
    Worker->>Email: each RS where PA holds a privilege — adverse action report [R5 §5.6(b)]
    Worker->>Email: Commission ops
    note over API: 5-day reporting window, 1 business day if emergency [R5 §5.4 as amended Nov 10] — reported_at − order_date surfaced on C-01

    SQL->>API: PATCH .../adverse-actions/{id} {effective_end}
    API->>DB: restriction lifted, practitioner.eligible_again_on = effective_end + 2 years
    note over PA: Privileges do NOT reactivate. After eligible_again_on, PA starts Phase 1 again.

    opt SQL withdraws eligibility [R3r §3.8(b)]  (L-06)
        SQL->>API: POST .../applications/{id}/withdraw-eligibility {reason}
        API->>DB: application=eligibility_withdrawn, all privileges → cancelled (reason=eligibility_withdrawn), events
        Worker->>Email: PA "eligibility withdrawn, privileges cancelled, appeal with the SQL"
        Worker->>Email: each RS
    end
```

## Report content and confidentiality

- Per the Nov 10 2025 amendments to R5 §5.4: a **structured record** (summary plus NPDB category), not document copies; a state that wants the order on file may attach it (optional, D9). SII is a checkbox plus contact information and a brief description on the same form; 5-day window, 1 business day for summary/emergency actions.
- `is_public=false` records never reach public verification (V-01) and show a "confidential — do not redisclose" banner to state users (R5 §5.5(c)).
- SII is visible only to participating-state and commission users, never to the PA or the public (ML §8.C).
- Notification goes to the PA, every state where the PA holds a QL or privilege, and the Commission (R5 §5.6(b)); other states may request the report (R5 §5.6(c)).

## CompactConnect reference (crosswalk §4.7)

The dialogs follow CompactConnect's card action menu (`staff-privilege-action-menu.png`) and differ only in what we add and in what the cascade does:

| Action | CompactConnect | Here |
|---|---|---|
| Deactivate a privilege | compact admin only; required note; confirm; PA and state emailed (`staff-deactivate-privilege-modal.png`) | issuing state or Commission; same dialog |
| Report discipline ("encumber") | action type + NPDB category (multi) + start date; on a license it *marks* every privilege encumbered (`staff-encumber-privilege-modal.png`) | same two pick-lists, plus summary, order date, emergency and public flags, optional attachment, SII checkbox with contact; on a QL it **deactivates** every privilege (ML §4.B / §6.G) |
| Lift | pick the action(s), give an end date; the privilege stays encumbered while any action is unlifted; on lift, restored (`staff-lift-encumbrance-modal.png`) | same dialog; a QL-level lift does **not** reactivate, the PA may reapply two years after the end date; a privilege-level lift restores that privilege when all actions on it are lifted |
| Investigation / SII | add / end investigation, shown as a red banner and an "Investigation" discipline status on cards (`staff-add-investigation-modal.png`) | a flag, contact, and description on the adverse-action form; closable; state and Commission users only |
| License status change | arrives with the next bulk upload; renewal reactivates privileges | a form on the license card (expired, lapsed, inactive, reinstated, terminated, effective date); reinstatement does not reactivate (ML §4.C) |
| Confidential records | none; all discipline is public | `is_public` flag; non-public records never reach the public site and carry a "confidential — do not redisclose" banner (R5 §5.5(c)) |

## Cascade matrix (A-01 / A-02 test cases)

| Trigger | Effect on privileges | Reactivation |
|---|---|---|
| Adverse action on QL | all → inactive, `qualifying_license_adverse_action` | none; PA re-applies after `eligible_again_on` |
| Adverse action on one privilege | that privilege → encumbered (computed) | when all actions on it are lifted |
| QL expired / lapsed / inactive (state update) | all → inactive, `qualifying_license_inactive` | none; PA re-applies |
| QL voluntarily terminated | all → inactive, `qualifying_license_terminated` | none |
| Eligibility withdrawn by SQL | all → cancelled, `eligibility_withdrawn` | none; appeal with SQL |
| State deactivates a privilege (or commission override) | that privilege → inactive, `state_deactivated` | none |
| QL reinstated | no change | PA re-applies (ML §4.C) |

## Evidence

Atoms are in `product/context/evidence/atoms/`; signals and tensions beside them. Rule section references above resolve to these IDs.

- `ATOM-GOV-ML-09`, `ATOM-GOV-ML-11` — QL adverse action removes every privilege until restrictions lift plus two years
- `ATOM-GOV-ML-07` — the 2-year bar on re-eligibility
- `ATOM-GOV-R23-15`, `ATOM-GOV-M0209-02` — eligibility withdrawal auto-cancels privileges; remote states have no say
- `ATOM-GOV-R5-05` — adverse action report content and windows (the Nov 10 amendment to summary + 5 days was struck at review; cite the minutes directly if needed)
- `ATOM-GOV-ML-03` — what counts as Significant Investigative Information
- `ATOM-GOV-ML-17`, `ATOM-GOV-R5-06` — public/not-public designation and the public subset
- `ATOM-GOV-ML-16`, `ATOM-GOV-R5-09`, `ATOM-GOV-M0209-03` — notification breadth; see `TENSION-01-adverse-action-notification-breadth`
- `SIGNAL-disciplinary-data-is-confidential-by-default` (borderline — see the signal for how to strengthen it)
