---
category: architecture
status: proposed
date: 2026-11-06
---

# ADR-0017: PyJWT for Cognito Token Verification

## Status

Proposed

## Date

2026-11-06

## Context

The API verifies every Cognito ID token's RS256 signature against the
pool's JWKS ([`auth.py`](../api/licensing_api/auth.py)). It did so with
`python-jose`, which the constitution's stack named.

`python-jose` 3.5.0 carries a critical advisory (PYSEC-2026-4298,
algorithm confusion) and its `ecdsa` dependency a high one
(PYSEC-2026-1325); neither had a fixed release as of this ADR's date, and
SCRUM-75's scanners fail a PR on either. The API's call pins
`algorithms=['RS256']` and passes an RSA JWK, and an HS256 token keyed
with the public key is rejected by both libraries, so the advisory was not
exploitable through this call, but it still fails the gate.

## Decision

The API verifies tokens with [PyJWT](https://pyjwt.readthedocs.io/)
(`pyjwt[crypto]`). The call keeps its shape: header parsed unverified to
find the `kid`, the matching JWKS entry loaded as a `PyJWK`, `RS256` the
only accepted algorithm, `aud` checked against the client ID, then
`token_use` checked for `id`.

## Pros and cons

### PyJWT (chosen)

- Pro: maintained, with no open advisories; uses `cryptography`, already
  in the lock, and drops `ecdsa`, `pyasn1`, and `rsa`.
- Pro: a near drop-in for this call; the change is the import, the
  exception type, and wrapping the JWK.
- Con: none for this use.

### joserfc / Authlib

- Pro: maintained, broader JOSE coverage (JWE).
- Con: a different API for no need the API has; nothing here encrypts
  tokens.

### Keep python-jose with an accepted-risk entry

- Con: the exception has to be maintained, and it keeps `ecdsa`, `rsa`,
  and `pyasn1` installed, dependencies our app never uses; `ecdsa`
  carries a high advisory of its own (PYSEC-2026-1325).

## Consequences

- `python-jose` is removed; `pyjwt[crypto]` is a direct dependency, listed
  in the API README.
- A test asserts an HS256 token keyed with the RSA public key is rejected.

## Related

- [ADR-0004](0004-jwt-auth-claims-as-user-identity.md): the claims the
  verified token provides.
- Constitution Principle I (dependency changes need an ADR).
- SCRUM-157, SCRUM-75.
