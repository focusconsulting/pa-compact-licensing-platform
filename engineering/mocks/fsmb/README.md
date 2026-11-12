# FSMB mock

[WireMock](https://wiremock.org/docs/) answering the two FSMB Physician Data
Center calls the API makes, so the app and its tests run with no FSMB account
([`engineering/docs/fsmb.md`](../../docs/fsmb.md)). It is local tooling and is
never deployed.

It accepts only the local credentials in
[`engineering/api/.env.example`](../../api/.env.example) and issues the bearer
token `local-fsmb-token`.

## Members

Any customer key works, including `me`.

| FID | Response |
|---|---|
| `999999907` | Cleared, report succeeded (FSMB's own sample) |
| `999999915` | Alerted, report succeeded (FSMB's own sample) |
| `999999923` | Unknown, report failed |
| `999999931` | Unknown, report pending, no report date |
| `999999949` | `503` |
| any other 9 digits | `404` |
| anything else | `400` |

A request without the token gets `401`. To add a member, copy a
`member-*.json` file in [`mappings/`](mappings/) and rebuild with `just infra`.
