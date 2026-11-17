---
category: architecture
status: proposed
date: 2026-11-17
---

# ADR-0022: Local TOTP Sign-in Against the DEV Pool

## Status

Proposed. Amends [ADR-0010](0010-local-sign-in-uses-password-auth.md).

## Date

2026-11-17

## Context

SCRUM-104 requires TOTP at every sign-in (F-04, D4). The client answers
Cognito's challenges: enrolment (`MFA_SETUP`) and a code at each sign-in
(`SOFTWARE_TOKEN_MFA`). The API will check the ID token's `amr` claim,
which Cognito sets to `["pwd", "otp", "mfa"]` after a TOTP sign-in.

The local Cognito mock cannot run that flow, and no emulator can:

| Emulator | Enrolment at sign-in | Code at sign-in | `amr` |
|---|---|---|---|
| cognito-local (pinned) | No: `AssociateSoftwareToken` refuses a session | Yes, for a user already enrolled | No |
| moto | Only after a new password | One secret shared by every user | No |
| Magnito | Unconfirmed | Yes | No |
| AWS Emulator | Open fidelity issues on `MFA_SETUP` (SCRUM-196) | Unconfirmed | No |

A Cognito stand-in of our own could do all three. It would be several
hundred lines, maintained for local use only, and it would prove our
client against our own reading of Cognito, not against Cognito.

Cognito itself documents `amr` as "rolling out gradually", and as
possibly not yet available to a given pool. Whether our pool issues it
for an SRP sign-in has to be checked against the pool.

## Decision

1. **Local sign-in stays on cognito-local, with password auth and no
   TOTP.** `just up` and the end-to-end tests are unchanged, and need no
   AWS account.
2. **`just up <env>` signs in against that environment's real pool.**
   `just cognito-env <env>` (`engineering/infrastructure`) reads the pool
   and app client IDs from the app component's outputs, as `just deploy`
   does, and prints the API's and the client's Cognito settings, with an
   empty endpoint and auth flow. `just up` exports them before starting
   the API, the Worker, and the client, overriding the `.env` files. The
   SDK then signs in with SRP and answers whatever MFA the pool requires.
   Everything else, the database included, stays local.
3. **TOTP and SRP are tried by hand against DEV.** This is how a
   developer checks a sign-in change before it reaches DEV, and how
   SCRUM-104 checks that DEV's tokens carry `amr` before the API requires
   it.

## Pros and cons

### Local mock by default, the DEV pool on request (chosen)

- Good: the client is proved against Cognito itself, SRP included, which
  ADR-0010 left untested before DEV.
- Good: no Cognito code of our own, and no new local service.
- Good: the default local stack and CI keep needing no AWS account.
- Bad: TOTP and SRP are not covered by CI; a regression shows up when a
  developer tries `just up dev`, or on DEV.
- Bad: it needs DEV credentials, and a user in DEV's pool whose email
  matches a local user.

### A Cognito stand-in of our own

- Good: the whole flow, `amr` included, locally and in CI.
- Bad: several hundred lines to maintain for local use, checked only
  against our reading of Cognito.

### cognito-local with every user enrolled

- Good: a code at every local sign-in, with no AWS account.
- Bad: enrolment is never exercised locally, and there is still no
  `amr`.

### A setting that skips MFA locally

- Bad: a code path that changes behaviour by environment, which
  constitution Principle IV forbids.

## Consequences

- Tokens from cognito-local carry no `amr`. When the API requires it
  (SCRUM-104, part 4), local sign-in against the mock needs a decision of
  its own: an exception to Principle IV, recorded in that part's ADR, or
  enrolled mock users and a stand-in that issues the claim.
- A user who first signs in through the mock is linked to the mock's
  `sub`, so the same email cannot then sign in from DEV's pool
  ([ADR-0009](0009-route-authorization-and-change-context.md)).
  `just infra` resets the database, and with it the link.
- The ADR-0010 consequence "SRP is not exercised locally" now reads "not
  by default".

## Related

- [ADR-0010](0010-local-sign-in-uses-password-auth.md): local sign-in
  uses password auth.
- [ADR-0021](0021-qrcode-react-for-totp-enrolment.md): the enrolment QR
  code.
- Constitution Principle IV (no mock code in production).
- SCRUM-104; SCRUM-196 (AWS Emulator as the local Cognito).
