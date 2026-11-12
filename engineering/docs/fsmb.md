# FSMB integration

The system reads a practitioner's current report from the Federation of State
Medical Boards' Physician Data Center (PDC) API: identity, education,
licenses, NPI, certifications, DEA registrations, and board orders. The client
is [`licensing_api/fsmb.py`](../api/licensing_api/fsmb.py). Why it is built
this way, and why the local stand-in is WireMock, is in
[ADR-0020](../adrs/0020-fsmb-client-and-mock.md).

FSMB's own documentation:

- [Get Current Report Data](https://github.com/fsmb/pdc-api/blob/main/docs/members-v1/get-current-report-data.md)
  and the [PDC report definition](https://github.com/fsmb/pdc-api/blob/main/docs/definitions/report.md)
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
GET {FSMB_API_URL}/v1/rosters/{customerKey}/members/{fid}/reports/current/data
Authorization: Bearer {access_token}
```

- `fid` is the Federation ID: exactly nine digits. The client refuses anything
  else before calling.
- `customerKey` is `me`, the roster the client credentials belong to.
- FSMB answers only for members of the Commission's roster. A `404` means
  "not on our roster, or no report", not "no such physician". Adding members
  to the roster and generating reports (`pdc.member_write`) are not built.
- The bearer comes from `POST {FSMB_API_URL}/connect/token`, a form with
  `grant_type=client_credentials`, the client ID and secret, and
  `scope=pdc.member_read`.

### The report

`FsmbReport` models every section FSMB documents. A section FSMB leaves out
is `None`.

| Field | Holds | Rule it informs |
|---|---|---|
| `fid`, `report_id`, `as_of_date_time_utc` | Which report this is, and when FSMB generated it | |
| `board_action_status` | `Cleared` (no board actions) or `Alerted` (one or more) | ML §4.A.7–8 |
| `board_orders` | Each disciplinary order: the board, its dates, and its actions (code, prejudicial, term, stayed, comments) and bases | ML §4.A.7–8 |
| `names.legal`, `names.other` | Legal name and other names | Rule 4 §4.3(c)(1)–(2) |
| `birth_date` | Month, day, and year, any of which may be missing; `full_date` only when all three are known | §4.3(c)(4) |
| `medical_education` | School (with CIBIS code), graduation year, and degree, each with whether FSMB verified it | §4.3(c)(9) |
| `licenses` | Each license: issuing board, type, status, number, issue and expiration dates | §4.3(c)(11), ML §4.A.6 |
| `npi` | NPI numbers | |
| `abms`, `aoa` | Specialty board certifications | |
| `dea` | DEA registrations: number, expiration, schedules, location | ML §4.A.4 |

Every report section carries the `report_date` on which FSMB received it.

FSMB sends calendar dates as midnight date-times (`2010-07-01T00:00:00`). The
client turns them into `date` and rejects one with any other time of day
(constitution Principle XIII). `as_of_date_time_utc` is an instant; a value
without a zone is taken as UTC.

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
| `FSMB_API_URL` | Base URL for both the token and report calls |
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
Its reports and answers are listed in
[`engineering/mocks/fsmb/README.md`](../mocks/fsmb/README.md). To call it by
hand:

```bash
FSMB_BEARER=$(curl -s -X POST localhost:8083/connect/token \
  -d 'grant_type=client_credentials&client_id=local-fsmb-client&client_secret=local-fsmb-secret&scope=pdc.member_read' \
  | jq -r .access_token)

curl -s localhost:8083/v1/rosters/me/members/999999915/reports/current/data \
  -H "Authorization: Bearer $FSMB_BEARER"
```

## Use the client

```python
from licensing_api.config import settings
from licensing_api.fsmb import REPORT_NOT_READY, BoardActionStatus, create_fsmb_client

fsmb = create_fsmb_client(settings)  # one per process: it caches the bearer
report = await fsmb.get_current_report('999999915')
if report is REPORT_NOT_READY:
    ...  # FSMB has the member but no report yet: ask again later
elif report is None:
    ...  # not on the Commission's roster
elif report.board_action_status is BoardActionStatus.ALERTED:
    ...  # report.board_orders says what the boards did
await fsmb.aclose()
```

| Outcome | What the client does |
|---|---|
| `200` | Returns `FsmbReport` |
| `204` | Returns `REPORT_NOT_READY` |
| `404` | Returns `None` |
| `401` | Fetches a new bearer and retries once; a second `401` raises `FsmbError` |
| Credentials refused, any other status, or a connection failure (after two connection retries) | Raises `FsmbError` |
| A body with a missing, malformed, or unknown field | Raises `FsmbError` naming the fields, never their values |
| An FID that is not nine digits | Raises `ValueError` with no call |

## Security impact assessment

- **Data and tier.** A report is PII (name, other names, birth date, NPI, DEA
  number and location, license numbers) and confidential disciplinary
  information (board orders, with free-text comments). Board orders, and
  anything derived from them that is not a public adverse action, are in the
  States and Commission tier: never shown to the PA or the public.
- **Flow.** FSMB → the Worker or a job, over TLS with a bearer scoped to
  `pdc.member_read`. Nothing calls the client yet. The ticket that does decides
  which fields are stored, and stores no more than the uniform data set and
  eligibility checks need.
- **Protection.** The client ID and secret live in Secrets Manager, readable
  only by the ECS execution role. The bearer is held in memory and never
  logged.
- **Logging.** Each call logs `FSMB call` with `operation`
  (`grant` or `get_current_report`), `status_code`, `outcome`
  (`ok`, `not_ready`, `missing`, `failed`), and `duration_ms`. The FID and
  report contents are never logged. `httpx`'s request log includes URLs, so it
  is raised to `WARNING`. A rejected body raises an error that names the
  fields, not their values, and drops the Pydantic error that would carry them.
- **What could go wrong.** FSMB adds a field, and lookups fail until the model
  gains it: the cost of rejecting unknown fields (Principle VII). A report for
  the wrong person is avoided because the FID addresses the member directly;
  matching an applicant to an FID is the caller's job.
