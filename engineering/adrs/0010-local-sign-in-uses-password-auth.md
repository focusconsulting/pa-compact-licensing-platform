---
category: architecture
status: accepted
date: 2026-10-21
---

# ADR-0010: Local Sign-in Uses Password Auth

## Status

Accepted

## Date

2026-10-21

## Context

The browser signs in to Cognito with SRP through `amazon-cognito-identity-js`, and the deployed app client allows only `ALLOW_USER_SRP_AUTH` and `ALLOW_REFRESH_TOKEN_AUTH`. The local stack needs a Cognito stand-in that needs no AWS account, issues ID tokens the API verifies against a JWKS, and gives each user a UUID `sub`.

No emulator does real SRP with Cognito-shaped tokens:

| Emulator | SRP | Problem |
|---|---|---|
| cognito-local | None | — |
| moto | Fake: any password signs in | The `email` claim holds the user's ID |
| Magnito | Real | `sub` is a ULID, not a UUID |

Writing our own SRP server would work, but it is about 500 lines, SRP maths included, that we would maintain for local use only.

## Decision

1. **Locally, the client signs in with `USER_PASSWORD_AUTH` against cognito-local.** `signIn` passes `NEXT_PUBLIC_COGNITO_AUTH_FLOW` to `setAuthenticationFlowType`, defaulting to `USER_SRP_AUTH`. Only the local `.env` sets it.
2. **Deployed environments keep SRP.** Their builds leave the variable unset, and the deployed app client still does not allow password auth, so a misconfigured build fails to sign in rather than sending passwords.
3. **cognito-local runs from its published image, pinned by digest**, with the local users and app client baked in from `engineering/mocks/cognito/db/`.

## Consequences

- SRP is not exercised locally or in the end-to-end smoke test; it is exercised only against a deployed pool. A regression in the SRP flow shows up on DEV, not in CI.
- The rest of the sign-in path is shared: the same SDK calls, the `NEW_PASSWORD_REQUIRED` challenge, token refresh, and the API's JWKS verification.
- cognito-local's error types and messages differ from Cognito's in places (a wrong password is `InvalidPasswordException`, not `NotAuthorizedException`), so the client must not branch on them.
- We maintain no Cognito code of our own; Dependabot updates the image.

## Notes

### Recognizing an SRP failure on DEV and higher environments

Because client interacts directly with Cognito, API will have no failure logs. The browser's requests to `cognito-idp.<region>.amazonaws.com` will fail. There are two failure modes:

#### 1. Configuration adjustments

Mistakes in configuration may not trigger errors in local envs or CI checks. In both cases, the login page will show Cognito error messages on screen. Two examples:

| Scenario | Browser Error Message at Login page |
| --- | --- |
| Terraform config drops `ALLOW_USER_SRP_AUTH` | "USER_SRP_AUTH is not enabled for the client." |
| Client app tries to use `USER_PASSWORD_AUTH` | "USER_PASSWORD_AUTH flow not enabled for this client." |

#### 2. SRP computation breaks (SDK upgrade, `crypto` or `Buffer` bundling)

As SRP is not exercised locally or in CI, the DEV or higher user would see "Incorrect username or password." at login. A broken SRP computation gets the same error as a mistyped password, so it reads as user error, and repeated retries trigger Cognito's lockout ("Password attempts exceeded").

Both scenarios are recognizable from analysis of the browser network log, in its `cognito-idp.<region>.amazonaws.com` requests. To tell them apart:

- `InitiateAuth` fails: configuration. Check `AuthFlow` in the request body.
- `InitiateAuth` succeeds and `RespondToAuthChallenge` rejects a known-good password: the SRP computation.
- No request at all: look for a JS exception in the console.
