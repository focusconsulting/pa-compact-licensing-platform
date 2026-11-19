# Roles, Per-State Permissions, and Two-Factor Sign-In Plan

## Overview

SCRUM-104 makes the API enforce the permission matrix SCRUM-103 agreed, and requires TOTP for every sign-in. The work ships as stacked pull requests. The first enforces authorisation. The others add TOTP in an order that never leaves sign-in broken: the client and the local mock learn the challenge before the pool and the API require it.

## Related

- Jira: SCRUM-104 (epic SCRUM-92); builds on SCRUM-103 and SCRUM-79; consumers SCRUM-105, SCRUM-106, SCRUM-116, SCRUM-133
- Spec: [`mvp-ticket-breakdown.md` F-04 and D4/D5](../../../../../product/backlog/mvp-ticket-breakdown.md)
- Flows: [FLOW-01](../../../../../product/context/flows/01-end-to-end-privilege-issuance.md)
- Rules: Rule 4 §4.5 (confidentiality), §4.6(a) (state access)
- ADRs: [ADR-0009](../../../../adrs/0009-route-authorization-and-change-context.md), [ADR-0020](../../../../adrs/0020-state-standing-and-relationship-scoping.md), [ADR-0010](../../../../adrs/0010-local-sign-in-uses-password-auth.md), [ADR-0018](../../../../adrs/0018-pyjwt-for-cognito-token-verification.md)
- Area: api, client, infrastructure, mocks

## Decisions (2026-11-16)

1. Authorisation ships first; TOTP follows in stacked PRs under this ticket.
2. The branch stacks on SCRUM-103 (#193) and retargets to `main` when it merges.
3. A grant outside what the role may be granted (`GRANTABLE`) matches nothing. Without this, a stray `{"KS": ["compact_admin"]}` would pass `/commission` routes.
4. `is_remote_for` keys on `submitted_at`, not status: FLOW-06 lets an unpaid request be withdrawn, and the state never received it. ADR-0020 and the contract are corrected.
5. The API asserts MFA from the ID token's `amr` claim (Cognito: `["pwd", "otp", "mfa"]` for a TOTP sign-in). Cognito documents `amr` as rolling out gradually, so the pools also set `mfa_configuration = "ON"`.

## PR 1: enforce the matrix (this branch)

- `licensing_api/permissions.py`: `require` checks standing for a `state_param` route; `held_permissions` reads `*` grants when no state is named; `GRANTABLE` limits grants per role.
- `licensing_api/repo/scope.py`: `is_sql_for`, `is_remote_for`, `holds_license_in`, `related_to`.
- `tests/test_permissions.py`: the role × endpoint test, driven from the matrix in `roles-and-permissions.md`; standing; Commission grants; a permission change and a deactivation take effect on the next request.
- `tests/test_scope.py`: each predicate, including drafts, unpaid requests, and persistence after withdrawal.
- Docs: the `require` contract, the grant rule, and the `is_remote_for` wording.

### Success criteria

- [x] `just lint`, `just test-coverage` at 100%
- [x] Removing the standing check fails the matrix test

## PR 2: the client answers TOTP challenges

Branch `feature/SCRUM-104-totp-client`, stacked on PR 1.

- `client/src/lib/auth.ts`: one set of challenge callbacks serves `signIn` and `completeNewPassword`, so a new user goes from setting a password straight to enrolment. `mfaSetup` associates a software token and resolves with its secret; `verifyTotpSetup` confirms the first code; `answerTotp` answers `totpRequired`; `totpUri` builds the `otpauth://` link.
- `AuthContext`: `completeNewPassword` returns the next step; `verifyTotpSetup` and `answerTotp` sign the user in.
- Login page: an enrolment step (a QR code of the `otpauth://` URI, the link itself, and the setup key grouped in fours) and a code step.

These steps stay inert while the pool has MFA off.

The QR code uses `qrcode.react` ([ADR-0021](../../../../adrs/0021-qrcode-react-for-totp-enrolment.md)); the PR names it for the Commission's consent (SOW §7.5).

### Success criteria

- [x] `pnpm lint`, `pnpm exec tsc --noEmit`, `pnpm test:coverage` at 100%

## PR 3: try TOTP locally against the DEV pool

Branch `feature/SCRUM-104-local-totp`, stacked on PR 2.

No emulator both enrols an authenticator app at sign-in and issues `amr` (cognito-local refuses `AssociateSoftwareToken` with a session; see ADR-0022). Decision (2026-11-17): local sign-in stays on cognito-local with password auth and no TOTP, and `just up dev` points the local API, Worker, and client at DEV's real pool.

- `engineering/infrastructure/justfile`: `cognito-env <env>` prints the Cognito settings from the app component's outputs.
- Root `justfile`: `up` takes an optional environment and exports those settings before starting the apps.
- ADR-0022, which amends ADR-0010; the README and the mock's README.

### Success criteria

- [x] A failed `cognito-env` stops `just up dev` before anything starts
- [x] Exported settings override the `.env` files for `uv run`, uvicorn, and Next.js
- [ ] `just up dev` signs in against DEV (needs DEV credentials)

## PR 4: require TOTP

- `iac/components/app/opentofu/cognito.tf`: `mfa_configuration = "ON"` with `software_token_mfa_configuration`. The PA pool (SCRUM-106) is created the same way.
- `licensing_api/auth.py`: refuse a token whose `amr` lacks `mfa` with `401 MFA_REQUIRED`, and check `iss`.
- An ADR for authentication: TOTP everywhere, asserted from `amr`.
- AC: a token without the MFA claim gets 401.
- First, with `just up dev` and a DEV user enrolled in TOTP, check that DEV's ID token carries `amr` (decision, 2026-11-17). If it doesn't, the check falls back to the pool's MFA setting.
- Tokens from cognito-local carry no `amr`, so local sign-in against the mock needs its own answer when the API requires it (ADR-0022, Consequences).

## What We're NOT Doing

- Staff provisioning and `reset-mfa` (SCRUM-105); PA registration and the PA pool (SCRUM-106).
- Rescoping documents with `related_to`: `visible_to_state` counts the states told about a PA (FLOW-07), which is a different question. That is a follow-up ticket.

## Security impact

Every field tier is affected, because standing and grants decide who reaches any state's records. The change only narrows access. Commission users lose `/states/{st}` routes; they use `/commission` instead, as ADR-0020 decided, and no Commission client screen calls a state route today. Grants the role may not hold stop counting. The risk is over-narrowing, and the matrix test covers each role against every route family.
