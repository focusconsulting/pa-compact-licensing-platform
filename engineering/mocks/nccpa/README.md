# NCCPA mock

[WireMock](https://wiremock.org/docs/) answering the two NCCPA calls the API
makes, so the app and its tests run with no NCCPA account
([`engineering/docs/nccpa.md`](../../docs/nccpa.md)). It is local tooling and
is never deployed.

It accepts only the local credentials in
[`engineering/api/.env.example`](../../api/.env.example) and issues the bearer
`local-nccpa-token`.

## PAs

`POST /CertificationStatus` with `{"id": "<PA ID>"}`:

| PA ID | Response |
|---|---|
| `1000020` | `Certified`, with no certification or expiration date |
| `1000029` | `Not Certified - Revoked` |
| `1000033` | `503`: system under maintenance |
| `1000044` | `429`: too many requests |
| any other number ending `0` | `Certified` until 2028-12-31, with `paId` echoing the request |
| any other number ending `9` | `Not Certified`: lapsed on 2024-12-31 |
| any other number | `404` |
| anything else | `400` |

A request without the bearer gets `401`, as NCCPA answers. NCCPA does not
document what it answers for a PA it doesn't know; `404` is our assumption
(see the open questions in `nccpa.md`).

To add a PA, copy a `status-*.json` file in [`mappings/`](mappings/) and
rebuild with `just infra`. Every `200` must follow NCCPA's OpenAPI document;
[`test_nccpa_openapi.py`](../../api/tests/test_nccpa_openapi.py) checks it.
