# Demo Data

`just seed demo` fills a migrated local database with a practitioner in every application, privilege request, privilege, and license status ([FLOW-06](../../product/context/flows/06-state-machines.md)), so sprint reviews and later epics can show screens before the features that create the data exist. It is local tooling: never a migration, never in the image (constitution Principle IV).

```bash
just infra          # reset the local services (deletes local data)
cd engineering/api
just migrate
just seed           # the team's admin logins
just seed demo
```

Dates count from the compact's today, so every status holds whenever the seed runs. Rows get history but no events, so no email goes out. A second run is refused; `just infra` resets. `tests/test_demo_seed.py` checks every status below against the status views.

## Who to sign in as

Every login uses the password `Local-Passw0rd!` against the local Cognito mock.

| Email | Role | For |
|---|---|---|
| `kansas.staff@demo.example` | KS `state_staff`, with `read_private` and `write` in KS | Kansas applicants and licenses |
| `kansas.admin@demo.example` | KS `state_admin`, with `read_private` and `admin` in KS | Kansas, and its staff and settings |
| `oklahoma.staff@demo.example` | OK `state_staff`, with `read_private` and `write` in OK | Privileges in Oklahoma, the remote state |
| `avery.active@demo.example` | `licensee` | A PA with an active privilege |
| `lex.license-action@demo.example` | `licensee` | A PA barred by an adverse action |

The team's own logins from `just seed` are `admin` and see everything.

## The compact

KS, OK, MO, and CO are members and live, each with a $100 privilege fee; the Commission's participation fee is $50.

## Practitioners

Each practitioner's surname names what they show. Kansas is the state of qualifying license (SQL) unless noted.

| Practitioner | Application | Privilege requests and privileges | Qualifying license | Compact eligibility |
|---|---|---|---|---|
| Dana Draft | `draft` | | `expired` | not barred |
| Sam Submitted | `submitted` | | `active` | not barred |
| Ira Info | `info_requested` | | `active`; a CO license `terminated` | not barred |
| Dee Denied | `denied` (NCCPA not current) | | `inactive` | not barred |
| Wren Withdrawn | `withdrawn` | | `lapsed` | not barred |
| Sol Superseded | `superseded`, then `eligible` for a change of SQL to MO | | `active` in KS and MO | not barred |
| Avery Active | `eligible` | OK `issued`, privilege `active`; MO `submitted`; CO `pending_payment` | `active` | not barred; a closed SII report from MO |
| Pia Expired | `eligible` | OK `issued`, privilege `expired`; MO `denied`; CO `withdrawn` | `active` | not barred |
| Enzo Encumbered | `eligible` | OK `issued`, privilege `encumbered` by an OK suspension in force | `active` | not barred; an open SII report from OK |
| Eli Withdrawn-Eligibility | `eligibility_withdrawn` | OK privilege `inactive` (eligibility withdrawn) | `active` | not barred |
| Lex License-Action | `eligible` | OK privilege `inactive` (license adverse action) | `encumbered` by a KS suspension in force | barred, with no end date |
| Bea Barred-Until | | | `active`; a KS suspension ended a year ago | barred until two years after it ended |
| Ned Bar-Ended | | | `active`; a KS suspension ended three years ago | no longer barred |

## Sprint review

1. Sign in as `avery.active@demo.example`: the dashboard shows a signed-in PA.
2. Sign in as `kansas.staff@demo.example`: a state staff member, scoped to Kansas.
3. Show the statuses the views compute, which each epic's screens will read:

   ```bash
   docker compose -p pa-compact exec postgres psql -U licensing -d licensing -c \
     "SELECT p.legal_first_name, p.legal_last_name, s.status, s.status_reason
        FROM v_privilege_status s
        JOIN privileges v ON v.id = s.privilege_id
        JOIN practitioners p ON p.id = v.practitioner_id
       ORDER BY 2"
   ```

As each epic adds its screens, add the step that shows them here.
