# FSMB mock

[WireMock](https://wiremock.org/docs/) answering the two FSMB Physician Data
Center calls the API makes, so the app and its tests run with no FSMB account
([`engineering/docs/fsmb.md`](../../docs/fsmb.md)). It is local tooling and is
never deployed.

It accepts only the local credentials in
[`engineering/api/.env.example`](../../api/.env.example) and issues the bearer
`local-fsmb-token`.

## Reports

`GET /v1/rosters/{customerKey}/members/{fid}/reports/current/data`, for any
customer key, including `me`:

| FID | Response |
|---|---|
| `999999915` | Alerted: FSMB's own sample, plus a board order and a DEA registration, with `issuerName` as state codes to fit the OpenAPI document |
| `999999907` | Cleared: one license, an AOA certification, no orders |
| `999999923` | Cleared, with only what FSMB requires: a legal last name, a birth year, nulls elsewhere |
| `999999931` | `204`: no report yet |
| `999999949` | `503` |
| any other 9 digits | `404` |
| anything else | `400` |

A request without the bearer gets `401`. To add a report, copy a
`report-*.json` file in [`mappings/`](mappings/) and rebuild with `just infra`.
Every report must follow FSMB's OpenAPI document;
[`test_fsmb_openapi.py`](../../api/tests/test_fsmb_openapi.py) checks it.
