# NCCPA integration

The system reads a PA's current board certification from NCCPA's Board
Certification Status API: whether they are certified, and since and until
when. The client is
[`licensing_api/nccpa.py`](../api/licensing_api/nccpa.py). Why it is built
this way is in [ADR-0021](../adrs/0021-nccpa-client-and-mock.md).

NCCPA's own documentation:

- [API documentation](https://api.nccpa.net/Help), which renders the
  [OpenAPI document](https://api.nccpa.net/help/docs/public/swagger.json)
- [API security](https://api.nccpa.net/Security): OAuth2 client credentials
- [FAQs](https://api.nccpa.net/Faq) and [support](https://api.nccpa.net/Support)
  (`apisupport@nccpa.net`, weekdays 8:30–5:00 ET)

No AWS environment reaches NCCPA yet: NCCPA has not issued credentials or the
sandbox URL. Until then the client runs against the local mock only.

## Browse the API

```bash
just nccpa-docs       # from the repo root; then open http://localhost:8085
```

Swagger UI shows the vendored document,
[`tests/nccpa_openapi.json`](../api/tests/nccpa_openapi.json). NCCPA's server
sends no CORS headers, so Swagger UI can't read the live one; `just
nccpa-openapi` refreshes the copy. The document also covers the CME API and
the certification search and PDF report, none of which the system calls.

## The one call

```http
POST {NCCPA_API_URL}/CertificationStatus
Authorization: Bearer {access_token}
Content-Type: application/json

{"id": "1234560"}
```

- `id` is the PA's NCCPA PA ID, sent as a string. NCCPA also accepts an SSN
  there; the client never sends one. It takes the PA ID as an `int` and
  refuses anything outside a positive 32-bit integer (the document's `paId`
  is `int32`) before calling.
- The bearer comes from `POST {NCCPA_API_URL}/oauth/token`, a form with
  `grant_type=client_credentials` and the client ID and secret. No scope is
  documented, so none is sent. It lasts an hour.

### The response

`NccpaCertificationStatusResponse` mirrors the document's
`CertificationStatusResponse`: the same six fields, none required, the same
nullability and types, and any other field rejected.

| Field | Holds |
|---|---|
| `pa_id` | The PA ID NCCPA matched |
| `first_name`, `last_name` | The PA's name as NCCPA holds it |
| `certification_status` | `Certified`, `Not Certified`, or `Not Certified - Revoked` |
| `certification_date`, `expiration_date` | When the current certification began and ends; NCCPA leaves both out "for certain PAs" |

The schema types `certificationStatus` as a plain string. The model holds it
to the three values the 200 response's description lists, so a value NCCPA
adds later fails loudly instead of being read as certified or not.
[`test_nccpa_openapi.py`](../api/tests/test_nccpa_openapi.py) re-reads the
values from the description.

The dates are `date-time`. The document gives no example; we expect midnight
with no zone, as FSMB sends. Code that stores one takes `.date()`
(constitution Principle XIII).

### When real responses differ from the document

As with FSMB ([`fsmb.md`](fsmb.md#the-document-is-the-starting-point-real-reports-the-final-word)):
a response that doesn't fit raises `NccpaError` and logs `NCCPA body
rejected` with each field's path and reason, never its value. To check one PA
by hand against the sandbox, point a local env file at it and run:

```bash
cd engineering/api
just nccpa-check 1234560 .env.nccpa-sandbox   # says whether the response fits; prints no PA data
```

Then change the field in `nccpa.py`, add it to `DEVIATIONS` in
`test_nccpa_openapi.py` with the evidence (environment, PA ID, what NCCPA sent,
date), make the mock send the real shape, and tell `apisupport@nccpa.net`.
When NCCPA changes the document, `just nccpa-openapi` and `just test
tests/test_nccpa_openapi.py` say what changed.

## Open questions for NCCPA

What the documentation site does not answer. Each answer may change the
client, the mock, or both.

| # | Question | What we assumed |
|---|---|---|
| 1 | What are the sandbox's API and token URLs? The FAQ says a sandbox "will be provided". | Nothing: no environment reaches NCCPA. |
| 2 | Is production's base URL `https://api.nccpa.net`, with no version prefix? The document has no `servers`. | Yes. An unauthenticated `POST https://api.nccpa.net/CertificationStatus` answers `401` with `WWW-Authenticate: Bearer`, so the path exists there. |
| 3 | Does the client credentials grant need a `scope`? None is documented. | No scope. |
| 4 | What does `/CertificationStatus` answer for a PA NCCPA doesn't know? Only `200`, `429`, and `503` are documented; `/CertificationStatus/Report` answers `400`. | `404`, read as "no such PA". A `400` or an empty `200` would raise `NccpaError`. |
| 5 | What body do errors carry, and does a `429` send `Retry-After`? What is the rate limit? | No body is read. Any status but `200`, `401`, and `404` raises. |
| 6 | Is the PA ID a PA gives us (their "NCCPA ID" or certification number, `practitioner.nccpa_certification_number`) the `paId` this call takes? | Yes. |
| 7 | How does NCCPA tell a 9-digit PA ID from an SSN in `id`? | We send only PA IDs, so it doesn't matter to us unless PA IDs reach 9 digits. |
| 8 | Are `Certified`, `Not Certified`, and `Not Certified - Revoked` every value of `certificationStatus`? | Yes; any other is rejected. |
| 9 | Which PAs have no certification or expiration date, and what time zone are the dates in? | Dates may be absent; they are calendar dates. |
| 10 | The security page recommends requesting a new token each time you need the API, rather than storing it. Is holding it in memory for its hour acceptable? | Yes: it is never persisted. |
| 11 | Does the sandbox have test PAs, with known IDs and statuses, to mirror in the mock? | The mock's PA IDs are our own. |

## Environments

| Environment | `NCCPA_API_URL` | Credentials |
|---|---|---|
| Local and CI | `http://localhost:8082`, the `nccpa-mock` container | `local-nccpa-client` / `local-nccpa-secret` in [`.env.example`](../api/.env.example) |
| Staging | NCCPA's sandbox, once NCCPA gives its URL | Not yet issued |
| Prod | `https://api.nccpa.net` (question 2) | Not yet issued |

| Setting | Purpose |
|---|---|
| `NCCPA_API_URL` | Base URL for both the token and certification calls |
| `NCCPA_CLIENT_ID`, `NCCPA_CLIENT_SECRET` | Client credentials from NCCPA's developer portal |

When the credentials and sandbox URL arrive, the AWS wiring follows FSMB's: an
`nccpa_api_url` OpenTofu variable, an `<environment>-nccpa-credentials` secret
created empty and set by hand, and the three settings on the Worker and jobs
only (constitution Principle VI).

## Run locally

`just infra` (or `just up`) starts `nccpa-mock` with the other local services.
Its PAs and answers are listed in
[`engineering/mocks/nccpa/README.md`](../mocks/nccpa/README.md): a PA ID
ending `0` is certified and one ending `9` has lapsed. To call it by hand:

```bash
NCCPA_BEARER=$(curl -s -X POST localhost:8082/oauth/token \
  -d 'grant_type=client_credentials&client_id=local-nccpa-client&client_secret=local-nccpa-secret' \
  | jq -r .access_token)

curl -s -X POST localhost:8082/CertificationStatus \
  -H "Authorization: Bearer $NCCPA_BEARER" -H 'Content-Type: application/json' \
  -d '{"id": "1234560"}'
```

## Use the client

```python
from licensing_api.config import settings
from licensing_api.nccpa import CertificationStatus, create_nccpa_client

nccpa = create_nccpa_client(settings)  # one per process: it caches the bearer
status = await nccpa.get_certification_status(1234560)
if status is None:
    ...  # NCCPA has no such PA
elif status.certification_status is CertificationStatus.CERTIFIED:
    ...
await nccpa.aclose()
```

| Outcome | What the client does |
|---|---|
| `200` | Returns `NccpaCertificationStatusResponse` |
| `404` | Returns `None` |
| `401` | Fetches a new bearer and retries once; a second `401` raises `NccpaError` |
| `429`, `503` (maintenance), credentials refused, any other status, or a connection failure (after two connection retries) | Raises `NccpaError` |
| A body with a missing, malformed, or unknown field, or an unlisted status | Raises `NccpaError` naming the fields, never their values |
| A PA ID that is not a positive 32-bit integer | Raises `ValueError` with no call |

## Security impact assessment

- **Data and tier.** A response is PII: the PA's name and NCCPA PA ID, with
  their certification status and dates. Whether a status is shown to the PA
  or the public is decided by the ticket that stores it. The request carries
  only the PA ID; the client never sends an SSN, though NCCPA accepts one.
- **Flow.** NCCPA → the Worker or a job, over TLS with an hour-long bearer.
  Nothing calls the client yet.
- **Protection.** The client ID and secret will live in Secrets Manager,
  readable only by the ECS execution role. The bearer is held in memory and
  never logged or stored.
- **Logging.** Each call logs `NCCPA call` with `operation` (`grant` or
  `get_certification_status`), `status_code`, `outcome` (`ok`, `missing`,
  `failed`), and `duration_ms`. The PA ID and response are never logged; the
  PA ID travels in the body, not the URL. A rejected body raises an error that
  names the fields, not their values, and drops the Pydantic error that would
  carry them.
- **What could go wrong.** NCCPA's real answers differ from its document
  (questions 4, 5, 8), and lookups fail until the model follows. A status for
  the wrong person is avoided because the PA ID addresses the PA directly;
  comparing NCCPA's name with the applicant's is the caller's job (SCRUM-155).
