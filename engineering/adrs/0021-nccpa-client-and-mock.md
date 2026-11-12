---
category: architecture
status: proposed
date: 2026-11-12
---

# ADR-0021: The NCCPA Client and Its Local Mock

## Status

Proposed

## Date

2026-11-12

## Context

A PA's compact eligibility needs current NCCPA certification (SCRUM-101, SCRUM-154, SCRUM-161). Of NCCPA's [Board Certification Status API](https://api.nccpa.net/Help) the system needs one call, `POST /CertificationStatus` with a PA ID, which returns the PA's name, status (`Certified`, `Not Certified`, `Not Certified - Revoked`), and certification and expiration dates. NCCPA authenticates it with OAuth2 client credentials at `/oauth/token`, and the bearer lasts an hour ([API security](https://api.nccpa.net/Security)).

NCCPA has not yet issued credentials or the sandbox URL, so nothing can call NCCPA. Principle IV still requires a local stand-in reached through the production client. The stand-in has to issue a bearer and refuse other credentials, answer different PA IDs with each status, and answer `401`, `404`, `429`, `503`, and `400`. SCRUM-161 adds that a PA ID ending `0` is certified and one ending `9` has lapsed.

NCCPA's OpenAPI document has no examples, no `servers`, and no security scheme, and documents only `200`, `429`, and `503` for this call. [`docs/nccpa.md`](../docs/nccpa.md) lists what it leaves open.

## Decision

Follow [ADR-0020](0020-fsmb-client-and-mock.md) for FSMB:

1. **A hand-written client over `httpx`** (`licensing_api/nccpa.py`). It caches the bearer in memory, fetches it again before expiry or once after a `401`, and validates every body with a Pydantic model that mirrors the document's `CertificationStatusResponse`, rejecting any field it doesn't name (Principle VII). `certificationStatus` is held to the three values the document's description lists, though its schema says only `string`. The document is vendored in `tests/nccpa_openapi.json` and `tests/test_nccpa_openapi.py` fails when the model, or a response the mock serves, departs from it.
2. **The client sends only the PA ID**, though NCCPA's `id` also takes an SSN. The system never holds a PA's SSN for this.
3. **An unknown PA is `404`**, returned as `None`. The document doesn't say; this is to confirm with NCCPA.
4. **WireMock as the local NCCPA**, from the same pinned `wiremock/wiremock:3.13.2` image, with JSON stubs in `engineering/mocks/nccpa/mappings/`. Compose runs it as `nccpa-mock` on port 8082, the port SCRUM-161 reserved. Response templating echoes the requested PA ID, so any ID ending `0` or `9` answers.
5. **`NCCPA_API_URL` decides which NCCPA the client reaches.** The OpenTofu variable, secret, and Worker settings wait for the sandbox URL and credentials; they will follow ADR-0020's pattern, on the Worker and jobs only (Principle VI).

## Pros and cons

The tooling choice is ADR-0020's. What differs here:

### Echoing the PA ID with response templating (chosen)

- Pro: any PA ID ending `0` or `9` works, as SCRUM-161 asks, without a stub per ID.
- Con: a templated stub is a string, not JSON, so `test_nccpa_openapi.py` renders it before checking it.

### A stub per PA ID

- Pro: every stub is plain JSON.
- Con: only the listed IDs answer, which doesn't meet SCRUM-161.

### Caching the bearer for its hour (chosen) or fetching one per call

- Pro (caching): half the calls, and the same code as FSMB.
- Con (caching): NCCPA's security page recommends requesting a token "each time you need to access the API" rather than storing it. We read that as persisting it, which the client never does, and ask NCCPA to confirm.

## Consequences

- No new tool or dependency: WireMock and Swagger UI are already in use for FSMB.
- `just nccpa-docs` serves the vendored document, because NCCPA's server sends no CORS headers for the live one.
- Every NCCPA call logs `NCCPA call` with `operation`, `status_code`, `outcome` (`ok`, `missing`, `failed`), and `duration_ms` (Principle VIII). PA IDs and responses are never logged.
- Real responses may differ from the document; `DEVIATIONS` in `test_nccpa_openapi.py` and `just nccpa-check` work as FSMB's do.
- The architecture diagram's NCCPA call moves from the API to the Worker.
- Staging can't reach NCCPA until NCCPA issues the sandbox URL and credentials and the AWS wiring is added.
