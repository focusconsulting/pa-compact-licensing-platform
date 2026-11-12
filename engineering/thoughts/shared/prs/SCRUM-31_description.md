## Summary

This PR adds a client for the one FSMB Physician Data Center (PDC) call we need, `GET /v1/rosters/{customerKey}/members/{fid}`. It also adds a WireMock stand-in, so the client runs locally and in CI without FSMB credentials, and wires FSMB's demo server into staging and its production server into prod. The Commission expects a PA's record to start from FSMB and NCCPA data (SCRUM-31); this is the FSMB building block. No route, handler, or table calls the client yet.

## Related

- Jira: [SCRUM-31](https://focusdigital.atlassian.net/browse/SCRUM-31)
- ADR: [ADR-0020: The FSMB Client and Its Local Mock](engineering/adrs/0020-fsmb-client-and-mock.md)
- FSMB docs: [pdc-api](https://github.com/fsmb/pdc-api), [api-docs](https://github.com/fsmb/api-docs)

## Changes

### Local FSMB (`engineering/mocks/fsmb`)

- A pinned `wiremock/wiremock:3.13.2` image with JSON stubs, run by Compose as `fsmb-mock` on port 8083. `just infra`, `just up`, and CI start it.
- `POST /connect/token` issues a bearer only for the local credentials in `.env.example`.
- Members by FID:

  | FID | Response |
  |---|---|
  | `999999907` | Cleared (FSMB's own sample) |
  | `999999915` | Alerted (FSMB's own sample) |
  | `999999923` | Unknown, report failed |
  | `999999931` | Unknown, report pending |
  | `999999949` | `503` |
  | any other 9 digits | `404` |
  | anything else | `400` |

  A request without the bearer gets `401`.
- `just fsmb-docs` (repo root) opens Swagger UI on <http://localhost:8084>, reading FSMB's OpenAPI document live from the demo server.

### Client (`licensing_api/fsmb.py`)

- OAuth2 client credentials with scope `pdc.member_read`. The bearer is cached per client and fetched again a minute before it expires, or once after a `401`. A lock makes concurrent callers share one grant.
- `get_member(fid)` returns `FsmbMember`, or `None` on `404`. It raises `ValueError` for an FID that isn't nine digits, before any call. Any other failure raises `FsmbError`.
- Pydantic models reject unknown fields (Principle VII). A validation error names the fields, never their values, and drops the cause, so PII and the bearer stay out of tracebacks.
- Each call logs `FSMB call` with `operation`, `status_code`, `outcome`, and `duration_ms`. The FID, name, and birth date are never logged.
- Settings: `FSMB_API_URL`, `FSMB_CLIENT_ID`, `FSMB_CLIENT_SECRET`, `FSMB_CUSTOMER_KEY` (`me`).

### Logging (`logging_config.py`)

- The `httpx` logger is raised to `WARNING`, because httpx logs every request's full URL at INFO and an FSMB URL contains the FID. This applies app-wide, so the Cognito key fetch's INFO lines disappear too.

### Infrastructure

- New variable `fsmb_api_url`, which must be FSMB's demo or production URL. Staging's `app.tfvars` sets the demo server.
- New secret `<environment>-fsmb-credentials`, created with empty values so the Worker still starts. The real values are set by hand with `aws secretsmanager put-secret-value` and never enter state.
- Only the Worker and jobs get `FSMB_API_URL`, `FSMB_CLIENT_ID`, and `FSMB_CLIENT_SECRET`, because Principle VI keeps calls to other services out of requests. The execution role can read the new secret.

### Docs

- `engineering/docs/fsmb.md`: the call, environments, settings, how to set the credentials, local curl, client usage, and the error table.
- `engineering/docs/architecture.md`: FSMB in the context and container diagrams and the "Locally" table.
- The root README and AGENTS.md service lists include the FSMB mock.

## How to Test

### Automated

```bash
cd engineering/api
just infra                     # now includes fsmb-mock
just test tests/test_fsmb.py   # 23 tests: the mock for FSMB's answers, a stub transport for bearer expiry and retry
just check
cd ../infrastructure && just check
```

### Manual

1. `just fsmb-docs` from the repo root, then open <http://localhost:8084>. FSMB's PDC API renders.
2. Call the mock directly. The second call returns the Alerted member:

   ```bash
   FSMB_BEARER=$(curl -s -X POST localhost:8083/connect/token \
     -d 'grant_type=client_credentials&client_id=local-fsmb-client&client_secret=local-fsmb-secret&scope=pdc.member_read' \
     | jq -r .access_token)
   curl -s localhost:8083/v1/rosters/me/members/999999915 -H "Authorization: Bearer $FSMB_BEARER"
   ```

3. Copy the FSMB block from `.env.example` into an existing `.env`.

## Checklist

- [x] API tests pass: 478 passed, 100% line and branch coverage
- [x] Type checking passes (pyright: 0 errors)
- [x] Linting passes (ruff check and format)
- [x] IaC passes `tofu fmt -check` and `tofu validate`
- [x] pre-commit passes, including gitleaks and markdownlint
- [x] Documentation updated
- [x] Manual testing: every stub exercised with curl, and `just fsmb-docs` serves FSMB's document
- [ ] Mermaid diagrams rendered with mermaid-cli (not run locally)

## Notes for Reviewers

- **Size (Principle XV):** about 570 hand-written non-test lines. That's `fsmb.py` (193), about 300 lines of WireMock stub JSON, about 35 of OpenTofu, and about 40 of settings, Compose, and justfiles. The rest is tests and docs.
- **Unknown fields fail the call.** If FSMB adds a response field, lookups fail until `FsmbMember` gains it. ADR-0020 records this as the cost of Principle VII.
- **Applying to staging creates a secret with empty values.** Lookups fail with "refused the client credentials" until FSMB issues demo credentials, but nothing calls the client yet. Nothing has been applied.
- **Third-party material (SOW §7.5):** `wiremock/wiremock` (Apache-2.0) and `swaggerapi/swagger-ui` (Apache-2.0) are local tooling only and never ship. They are named here for the Commission's consent. No new Python dependency; `httpx` was already one.
- **No plan file:** this was built in one session from a direct request, so there is no plan to embed.
