# Roles, Permissions, and Profile Fields (Epic 5 Contract Step) Plan

## Overview

This plan fixes what the epic 5 tracks build against: the role × route-family permission matrix, how a state's relationship to a PA is resolved, and the profile field groups the SQL stamps. It is a contract step, so it ships documentation, an ADR, and one consistency test. The code changes belong to SCRUM-104, SCRUM-105, and SCRUM-107.

## Related

- Jira: SCRUM-103 (epic SCRUM-92); consumers SCRUM-104, SCRUM-105, SCRUM-107, SCRUM-132, SCRUM-153
- Spec: [`mvp-ticket-breakdown.md` §2.4 and F-04](../../../../../product/backlog/mvp-ticket-breakdown.md)
- Flows: [FLOW-01](../../../../../product/context/flows/01-end-to-end-privilege-issuance.md), [FLOW-02](../../../../../product/context/flows/02-sql-eligibility-verification.md) (the SQL's verification stamps)
- Rules: Rule 4 §4.3(c) and (e) (uniform data set), §4.6(a) (state access)
- ADRs: [ADR-0009](../../../../adrs/0009-route-authorization-and-change-context.md), [ADR-0017](../../../../adrs/0017-state-standing-and-relationship-scoping.md) (new)
- Area: api

## Decisions (agreed 2026-11-09)

1. A `/states/{state_code}` route needs standing in that state: home `state_code`, or any grant there. Commission users read states through `/commission`.
2. Relationships are SQLAlchemy predicates in `repo/scope.py`: `is_sql_for`, `is_remote_for`, `holds_license_in`, `related_to`.
3. A relationship persists once a non-draft application or a paid request forms it.
4. A Commission user's `read_ssn` is held under the `*` key, for `compact_admin` only.

Defaults taken without a separate decision:

- Other names go in a `practitioner_other_names` child table under the `identity` stamp.
- The change logs are read from `practitioners_history`.
- The SSN is covered by the `identity` stamp.

## Changes

- `engineering/adrs/0017-state-standing-and-relationship-scoping.md`: decisions 1–4.
- `engineering/docs/platform-contract.md`: adds the Permission matrix, Relationships, and Profile fields sections, plus the epic 5 track list.
- `engineering/docs/roles-and-permissions.md`: adds standing, the `*` grant, and links to the matrix and the predicates.
- `engineering/docs/data-model.md`: adds `practitioner_other_names`; the change logs come from history.
- `engineering/api/tests/test_profile_fields.py`: holds the contract's group table to the `Practitioner` model.

## What We're NOT Doing

- Changing `require` or `held_permissions`, and adding `repo/scope.py` (SCRUM-104).
- The staff CLI (SCRUM-105) and the `practitioner_other_names` migration (SCRUM-107).
- The role × endpoint test (SCRUM-104), which is driven from the matrix.

## Verification

- `just lint`
- `just test-coverage`
- `pre-commit run --files <changed files>`
