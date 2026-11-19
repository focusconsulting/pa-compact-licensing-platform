# Roles and Permissions

Who can do what in the PA Compact Data System, and how the API checks it. The capabilities each role needs come from the backlog ([`mvp-ticket-breakdown.md`](../../product/backlog/mvp-ticket-breakdown.md) §2.4, decision D5); the design is [ADR-0009](../adrs/0009-route-authorization-and-change-context.md); the code is `engineering/api/licensing_api/permissions.py`.

## How a check works

A user has one **role** (`users.role`) and, if they are staff, **grants** for particular states (`users.permissions`). A route asks for one **permission**. The user passes when they hold it:

```text
held in state S = the permissions their role holds everywhere
                + the permissions granted to them in S
```

S is the state in the route's path, such as `KS` in `/states/KS/applications`, or the user's own `state_code` when the path names none. A user with no `state_code` (the Commission roles) holds their `*` grants there.

In a `/states/{state_code}` path the user must first have **standing** in S: S is their `state_code`, or they hold a grant there. Without it they are refused whatever their role holds, so a Kansas user cannot use Missouri's routes, and Commission users read states only through `/commission` ([ADR-0020](../adrs/0020-state-standing-and-relationship-scoping.md)).

Routes never check a role. To change what a role may do, change `ROLE_PERMISSIONS`, not the routes.

## Roles

| Role | Who | `state_code` | Holds everywhere |
|---|---|---|---|
| `licensee` | A PA. Manages their own profile, applications, payments, and privileges | NULL: a PA signs up before naming a state (FLOW-01) | `manage_own_record` |
| `state_staff` | A state licensing board employee. What they may do in their state comes from their grants | Their state | `read_general` |
| `state_admin` | State staff who also manage their state's users and settings | Their state | `read_general` |
| `compact_admin` | Commission staff. Read every state, configure the compact, override a privilege | NULL | `read_general`, `read_private`, `compact_admin` |
| `admin` | The system operator: Focus during the pilot, then Commission IT | NULL | `read_general`, `read_private`, `compact_admin`, `system_admin` |

`state_staff` and `state_admin` hold the same permissions from their role; a `state_admin` is given the `admin` grant for their state. No role holds `write`: a state's records change only through a grant for that state, so Commission users can read any state but change none (constitution Principle VII).

## Permissions

| Permission | Lets the user | Comes from |
|---|---|---|
| `manage_own_record` | Act on their own practitioner record | Role |
| `read_general` | See the non-private fields of practitioners, licenses, and privileges | Role |
| `compact_admin` | Configure the compact: fees, which states are live, report lists, privilege overrides | Role |
| `system_admin` | Operate the system: the `/admin` routes | Role |
| `read_private` | See private fields: date of birth, address, the SSN's last four digits | Grant, or a Commission role |
| `read_ssn` | Reveal a full SSN; every reveal is audited (ADR-0007) | Grant |
| `write` | Change the state's records: licenses, eligibility decisions, privileges, adverse actions | Grant |
| `admin` | Manage the state's staff users, their grants, and the state's settings | Grant |

The [confidentiality tiers](data-model.md#confidentiality-tiers) map onto these: private fields need `read_private`, the full SSN needs `read_ssn`.

## Grants

`users.permissions` maps a state code to the permissions held there. A user may hold grants in more than one state:

```json
{"KS": ["write", "read_private"], "MO": ["read_private"]}
```

A `compact_admin` user who may reveal SSNs holds `{"*": ["read_ssn"]}`. `*` is the only key a Commission user holds, `read_ssn` is the only permission granted under it, and it gives no standing in any state. Only a `compact_admin` may hold it.

A value that names no permission matches nothing, so a typo denies rather than allows. So does a permission the role may not be granted (`GRANTABLE`): staff are granted only `read_private`, `read_ssn`, `write`, and `admin` under state codes, and a `compact_admin` only `read_ssn` under `*`. A role's own permissions, such as `compact_admin`, are never granted. Grants are read on every request, so a change takes effect on the user's next request. The F-04 staff CLI (SCRUM-105) will create staff and change their grants, writing each change to `audit_log` as a security event; no route does. `admin` and `compact_admin` may use it in any state, and a holder of the `admin` grant in a state may use it in that state.

## What the client sees

`GET /api/me` returns `permissions`: everything the user holds in their own state. The client shows each portal's navigation from it ([`navigation.ts`](../client/src/lib/navigation.ts)) and never from `role`. Hiding a link is not a check; the route still is.

## What a permission does not decide

A permission decides whether a user may call a route, not which rows they see. [Documents](documents.md#who-may-see-a-document) lists the scope for each kind of document. A `state_staff` user with `read_private` in Kansas sees only the PAs related to Kansas (Rule 5 §5.6(a)), and a licensee sees only their own record. The route's query applies that scope with the [relationship predicates](platform-contract.md#relationships), and a record outside it returns `404` (constitution Principle II). Which role reaches which route family is the [permission matrix](#permission-matrix).

## Namespaces

Every `/api` route outside `/api/health` sits under the namespace of the people who call it. `licensing_api/routes/__init__.py` assigns each resource router to one, and `tests/test_route_access.py` fails a route that breaks its namespace's rule.

| Namespace | Who calls it | Rule |
|---|---|---|
| `/me` | A PA, for their own record; any user, for their own account | Signed in |
| `/public` | Anyone: [verification](../../product/context/flows/08-public-verification.md) and published configuration | `public()` |
| `/states/{state_code}` | One state's staff, in the state the path names | `state_param='state_code'` |
| `/commission` | Commission staff, across every state | `compact_admin` |
| `/admin` | The system operator | `system_admin` |

The health checks under `/api/health` are public for the load balancer, so they say only whether the API and database answer. `GET /api/admin/status` gives the system operator the deployed version, environment, uptime, database latency, and newest migration.

`/commission` routes need `compact_admin`, not `read_private`: with no state in the path, `read_private` is checked in the caller's own state, so a state staff member's grant would pass.

## Permission matrix

What each role reaches, by route family, decided in [ADR-0020](../adrs/0020-state-standing-and-relationship-scoping.md). A `/states/{st}` row applies only to a caller with **standing** in `st`: `st` is their `state_code`, or they hold a grant there. Without standing the route returns `403 FORBIDDEN`, whatever the role. **✓** means the role alone passes; **grant** means the user also needs that permission granted in the state (in `*` for a Commission user); **own** means only their own record. SCRUM-104's role × endpoint test is driven from this table.

| Route family | Declares | Rows the query returns | `licensee` | `state_staff` | `state_admin` | `compact_admin` | `admin` |
|---|---|---|---|---|---|---|---|
| `/me`: the caller's account | `require()` | The caller | ✓ | ✓ | ✓ | ✓ | ✓ |
| `/me/...`: profile, applications, privilege requests, payments | `manage_own_record` | The caller's practitioner | own | — | — | — | — |
| `/public/...`: verification, live states, fees | `public()` | Public tier only | Anyone, signed in or not | | | | |
| `/states/{st}/practitioners/...`: search, profile, history, documents | `read_general` | [`related_to(st)`](platform-contract.md#relationships) | — | ✓ | ✓ | — | — |
| The private fields in those responses | `read_private` in `st` | Same | — | grant | grant | — | — |
| `/states/{st}/practitioners/{id}/ssn`: reveal, audited | `read_ssn` | `related_to(st)` | — | grant | grant | — | — |
| `/states/{st}/applications`: SQL queue and case view | `read_general` | `sql_state_code = st`, once the state has received it ([FLOW-06](../../product/context/flows/06-state-machines.md)) | — | ✓ | ✓ | — | — |
| `/states/{st}/applications/{id}/...`: verify, request information, decide, withdraw eligibility | `write` | Same | — | grant | grant | — | — |
| `/states/{st}/qualifying-licenses`, `/license-ingestions`: enter, update, upload | `write` | `state_code = st` | — | grant | grant | — | — |
| `/states/{st}/privilege-requests`: remote-state queue and case view | `read_general` | `remote_state_code = st`, once the state has received it ([FLOW-06](../../product/context/flows/06-state-machines.md)) | — | ✓ | ✓ | — | — |
| `/states/{st}/privilege-requests/{id}/...`, `/privileges/{id}/...`: issue, deny, change status | `write` | `remote_state_code = st` | — | grant | grant | — | — |
| `/states/{st}/adverse-actions`, `/sii-reports`: read | `read_general` | The practitioner is `related_to(st)` | — | ✓ | ✓ | — | — |
| The same: report, update, lift, close | `write` | Reported by `st` | — | grant | grant | — | — |
| `/states/{st}/settings`: fees, proofs, contacts, practice requirements | `admin` | The state itself | — | grant | grant | — | — |
| `/states/{st}/member-contacts`, `/reports`, `/dashboard` | `read_general` | The state's own figures; every member state's contacts | — | ✓ | ✓ | — | — |
| `/commission/...`: every state's records, reports, member contacts, audit log | `compact_admin` | Every state | — | — | — | ✓ | ✓ |
| `/commission/practitioners/{id}/ssn`: reveal, audited | `compact_admin`, then `read_ssn` | Every state | — | — | — | grant | — |
| `/commission/settings`, `/commission/states/{st}`, `/commission/privileges/{id}/deactivate` | `compact_admin` | Every state | — | — | — | ✓ | ✓ |
| `/admin/...` | `system_admin` | | — | — | — | — | ✓ |

## Declaring a route

```python
caller: Annotated[User, require(Permission.WRITE, state_param='state_code')]
```

`require()` with no permission admits any active user; `public()` declares a route anyone may call. A route that declares neither fails `tests/test_route_access.py`. The [platform contract](platform-contract.md#declaring-a-route) has the signatures and error codes.

## Changing roles and permissions

- **What a role may do:** edit `ROLE_PERMISSIONS` and the Roles table above.
- **A new permission:** add it to `Permission`, describe it in the Permissions table above, and give it to a role in `ROLE_PERMISSIONS` or make it grantable in `GRANTABLE`.
- **A new role:** a migration extending the `chk_users_role` constraint, a `Role` member, and entries in `ROLE_PERMISSIONS` and `GRANTABLE`.

`tests/test_permissions.py` fails when these tables and the code disagree. A change to a role or permission is a platform change and needs the tech lead's review.
