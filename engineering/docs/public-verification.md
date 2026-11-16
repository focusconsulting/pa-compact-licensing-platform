# Public verification

Anyone, signed in or not, can confirm that a PA holds a compact privilege (SOW
§2.1; [SCRUM-139](https://focusdigital.atlassian.net/browse/SCRUM-139)). The
routes are `GET /api/public/privilege-holders` and
`GET /api/public/privilege-holders/{id}`, in
`licensing_api/routes/public_verification.py`.

## What the public sees

The responses are an allow-list. Rule 4 §4.5(b) makes two things public: the
names of participating PAs, and the states where they hold a qualifying license
or a privilege. The Commission's default for the rest (backlog Q-12) adds each
privilege's number, status, and dates.

| Field | From | Why it is public |
|---|---|---|
| `first_name`, `last_name`, `name_suffix` | `practitioners.legal_first_name`, `legal_last_name`, `name_suffix` | Rule 4 §4.5(b)(1) |
| `state_of_qualifying_license` | `practitioners.current_sql_state_code` | Rule 4 §4.5(b)(2) |
| `privilege_states`, `privileges[].state` | `privileges.remote_state_code` | Rule 4 §4.5(b)(2) |
| `privileges[].number` | `privileges.privilege_number` | Q-12 |
| `privileges[].status` | `v_privilege_status`, collapsed as below | Q-12; SOW §2.1 |
| `privileges[].issued_on` | `privileges.issued_at`, as a day in the reference time zone (ADR-0006) | Q-12 |
| `privileges[].expires_on` | `privileges.expires_on` | Q-12 |
| `id` | `practitioners.public_id` | A random key for the holder's page; it says nothing about the PA |

To add a field, add its row here first. `tests/test_public_verification.py`
pins each response model to this list and fails when one grows.

Never public: middle and other names, date of birth, NPI, contact details,
license number and status, compact eligibility, why a privilege is not active,
and anything about an adverse action or an investigation, public or not.

## Status

The public sees three statuses. A privilege that is not active carries no
reason and no date for the change (FLOW-05).

| Computed status ([data model](data-model.md#computed-status)) | Public status |
|---|---|
| `active` | `active` |
| `expired` | `expired` |
| `inactive` | `inactive` |
| `encumbered` | `inactive` |

An encumbered privilege is `inactive` whether or not the action behind it is
public (Rule 4 §4.5(c)). Were only the sealed ones collapsed, the status itself
would tell the two apart.

## Search

- By `first_name` and `last_name` together, or by `privilege_number` alone.
  Anything else is a `422`, as is a parameter the search does not take.
- Names match in full, ignoring case and surrounding spaces. There is no
  prefix or partial match, so the register cannot be listed by guessing letters.
- Only a PA who holds a privilege, active or not, is found. A PA with none is a
  `404` on the holder route, the same as an unknown id.
- No match is `200` with an empty list.

## Limits

The web firewall allows one address 300 requests to `/api/public/` in five
minutes, then answers `429` with the API's error body and `Retry-After`
([infrastructure security](security/infrastructure.md)). The API documents the
`429` and never sends it; locally there is no limit.

Privilege numbers run in sequence within a state, so the number search can be
walked. Everything it returns is public by rule, and the limit bounds the pace
from one address. A crawl from many addresses is not prevented.

Each search logs its mode and result count, never the name or number searched.
Those reach the CloudFront, firewall, and load-balancer access logs in the
query string.
