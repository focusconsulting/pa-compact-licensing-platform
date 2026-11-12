---
category: architecture
status: proposed
date: 2026-11-12
---

# ADR-0020: The FSMB Client and Its Local Mock

## Status

Proposed

## Date

2026-11-12

## Context

The Commission expects a PA's record to start from FSMB and NCCPA data (SCRUM-31). Of FSMB's Physician Data Center (PDC) API ([pdc-api](https://github.com/fsmb/pdc-api)) the system needs one call, `GET /v1/rosters/{customerKey}/members/{fid}`: a roster member's name, birth date, and board-action status. FSMB authenticates it with OAuth2 client credentials ([api-docs](https://github.com/fsmb/api-docs/blob/master/docs/authentication.md)), and the bearer expires.

Principle IV requires a local stand-in that the app reaches through its production client, as maildev stands in for SES. FSMB has a demo server, but it needs FSMB-issued credentials, and they arrive only after the data-sharing agreement. Local runs and CI must have none. The stand-in has to:

- issue a bearer from `POST /connect/token`, and refuse other credentials;
- answer different FIDs differently: Cleared, Alerted, Unknown with a failed report, Unknown with a pending one;
- answer `404`, `400`, `401`, and a server error, so the client's handling of each is exercised.

FSMB's OpenAPI document has no examples and does not describe `/connect/token`.

## Decision

1. **A hand-written client over `httpx`** (`licensing_api/fsmb.py`), already a dependency. It caches the bearer, fetches it again before expiry or once after a `401`, and validates every body with Pydantic models that reject unknown fields (Principle VII).
2. **[WireMock](https://wiremock.org/docs/) as the local FSMB**, built from the pinned `wiremock/wiremock:3.13.2` image with JSON stubs in `engineering/mocks/fsmb/mappings/`. Docker Compose runs it as `fsmb-mock`, so `just infra`, `just up`, and CI start it.
3. **Settings decide which FSMB the client reaches**: `FSMB_API_URL` is the mock locally and in CI, FSMB's demo server in staging, and production in prod. The client ID and secret come from Secrets Manager in AWS.
4. **The Worker and jobs get the settings, and the API does not.** Principle VI keeps calls to other services out of requests.

## Pros and cons

### WireMock with JSON stubs (chosen)

- Pro: stubs match on form fields, headers, and path parameters, with priorities. That covers the token endpoint, per-FID members, and the `401`/`404`/`400` fallbacks with no code of ours.
- Pro: the stubs are data a reviewer reads as FSMB's answers; adding a member means copying a file.
- Pro: a multi-arch image (Prism's is amd64-only), with `wget` for the health check.
- Con: a JVM container, about 300 MB, and slower to start than the other stand-ins.
- Con: the stubs are written by hand from FSMB's documentation, so they drift if FSMB changes and nobody updates them. FSMB's own two samples (`999999907`, `999999915`) anchor them.
- Con: Apache-2.0 tooling the Commission consents to, although it never ships (SOW §7.5).

### Prism from FSMB's OpenAPI document

- Pro: already used for the API's own mock (ADR-0013); no new tool.
- Pro: follows FSMB's document as it changes.
- Con: the document has no examples, so Prism generates one body for every FID; per-FID scenarios are impossible.
- Con: no `/connect/token` in the document, so the client's credential flow could not run against it.

### A small FastAPI mock in `engineering/mocks/fsmb`

- Pro: any behaviour, in the team's own language.
- Con: code we maintain and test, for what WireMock does with data.

### Calling FSMB's demo server everywhere

- Pro: real responses, with no stand-in to drift.
- Con: needs credentials on every laptop and in CI, which Principles VII and XII forbid.

## Consequences

- New local tooling: `wiremock/wiremock:3.13.2`, pinned by digest in `engineering/mocks/fsmb/Dockerfile`. No new Python dependency.
- `just fsmb-docs` runs `swaggerapi/swagger-ui:v5.17.14` against FSMB's live document, so it shows what FSMB publishes now.
- Every FSMB call logs `FSMB call` with `operation`, `status_code`, `outcome` (`ok`, `missing`, `failed`), and `duration_ms` (Principle VIII). FIDs, names, and birth dates are never logged, and `httpx`'s own request logging is raised to `WARNING` because it logs URLs.
- A body with a field the models don't know fails the call. If FSMB adds a field, lookups fail until the model gains it. This is the price of Principle VII's gate.
- Staging needs FSMB's demo credentials in `staging-fsmb-credentials` before a lookup can succeed. Until then the secret holds empty values, so the Worker still starts.
