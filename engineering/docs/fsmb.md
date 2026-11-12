# FSMB integration

The system reads a practitioner's board-action status from the Federation of
State Medical Boards' Physician Data Center (PDC) API. The client is
[`licensing_api/fsmb.py`](../api/licensing_api/fsmb.py). Why it is built this
way, and why the local stand-in is WireMock, is in
[ADR-0020](../adrs/0020-fsmb-client-and-mock.md).

FSMB's own documentation:

- [PDC API](https://github.com/fsmb/pdc-api): resources, models, and samples
- [Getting started](https://github.com/fsmb/api-docs): authentication, errors, terminology
- [OpenAPI document](https://services-pdc-demo.fsmb.org/swagger/v1/swagger.json)

## Browse the API

```bash
just fsmb-docs        # from the repo root; then open http://localhost:8084
```

Swagger UI reads FSMB's document from the demo server each time, so it shows
what FSMB publishes today. "Try it out" calls FSMB's demo server and needs
FSMB-issued credentials. To try calls with no credentials, use the mock (below).

## The one call

```http
GET {FSMB_API_URL}/v1/rosters/{customerKey}/members/{fid}
Authorization: Bearer {access_token}
```

- `fid` is the Federation ID: exactly nine digits. The client refuses anything
  else before calling.
- `customerKey` is `me`, the roster that the client credentials belong to.
- FSMB answers only for members on the Commission's roster. A `404` means
  "not on our roster", not "no such physician". Adding members to the roster
  (`pdc.member_write`) is not built.
- The bearer comes from `POST {FSMB_API_URL}/connect/token`, a form with
  `grant_type=client_credentials`, the client ID and secret, and
  `scope=pdc.member_read`.

The response, as `FsmbMember`:

| Field | Meaning |
|---|---|
| `fid`, `full_name`, `birth_date` | FSMB's record of the member |
| `board_action_status` | `Cleared` (no board actions), `Alerted` (one or more), or `Unknown` (no succeeded report yet) |
| `current_report.report_status` | `Pending`, `Succeeded`, or `Failed` |
| `current_report.report_date_utc` | When the report was generated; absent while it is pending |

## Environments

| Environment | `FSMB_API_URL` | Credentials |
|---|---|---|
| Local and CI | `http://localhost:8083`, the `fsmb-mock` container | `local-fsmb-client` / `local-fsmb-secret` in [`.env.example`](../api/.env.example) |
| Staging | `https://services-pdc-demo.fsmb.org` | FSMB's demo credentials, in `staging-fsmb-credentials` |
| Prod | `https://services-pdc.fsmb.org` | FSMB's production credentials, in `prod-fsmb-credentials` |

The URL is the `fsmb_api_url` OpenTofu variable, set in each environment's
`app.tfvars`. Only the Worker and scheduled jobs get FSMB settings: calls to
other services run outside requests (constitution Principle VI).

| Setting | Purpose |
|---|---|
| `FSMB_API_URL` | Base URL for both the token and member calls |
| `FSMB_CLIENT_ID`, `FSMB_CLIENT_SECRET` | Client credentials FSMB issues; from Secrets Manager in AWS |
| `FSMB_CUSTOMER_KEY` | The roster path segment; `me` |

### Setting the credentials in AWS

OpenTofu creates `<environment>-fsmb-credentials` with empty values and never
holds the real ones. When FSMB issues credentials (contact `pdc@fsmb.org`):

```bash
aws secretsmanager put-secret-value --secret-id staging-fsmb-credentials \
  --secret-string '{"client_id":"...","client_secret":"..."}'
```

Then force a new Worker deployment so its tasks read the new value.

## Run locally

`just infra` (or `just up`) starts `fsmb-mock` with the other local services.
Its members and answers are listed in
[`engineering/mocks/fsmb/README.md`](../mocks/fsmb/README.md). To call it by
hand:

```bash
FSMB_BEARER=$(curl -s -X POST localhost:8083/connect/token \
  -d 'grant_type=client_credentials&client_id=local-fsmb-client&client_secret=local-fsmb-secret&scope=pdc.member_read' \
  | jq -r .access_token)

curl -s localhost:8083/v1/rosters/me/members/999999915 \
  -H "Authorization: Bearer $FSMB_BEARER"
```

## Use the client

```python
from licensing_api.config import settings
from licensing_api.fsmb import BoardActionStatus, create_fsmb_client

fsmb = create_fsmb_client(settings)  # one per process: it caches the bearer
member = await fsmb.get_member('999999915')
if member is not None and member.board_action_status is BoardActionStatus.ALERTED:
    ...
await fsmb.aclose()
```

| Outcome | What the client does |
|---|---|
| `200` | Returns `FsmbMember` |
| `404` | Returns `None` |
| `401` | Fetches a new bearer and retries once; a second `401` raises `FsmbError` |
| Credentials refused, any other status, or a connection failure (after two connection retries) | Raises `FsmbError` |
| A body with a missing, malformed, or unknown field | Raises `FsmbError` naming the fields, never their values |
| An FID that is not nine digits | Raises `ValueError` with no call |

## Data and logging

The response holds PII: name and birth date. Each call logs `FSMB call` with
`operation` (`grant` or `get_member`), `status_code`, `outcome`, and
`duration_ms`. The FID, name, birth date, and bearer are never logged, and
`httpx`'s request log, which includes URLs, is raised to `WARNING`.
