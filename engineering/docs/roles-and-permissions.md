# Roles and Permissions

Who can do what in the PA Compact Data System, and how the API checks it. The capabilities each role needs come from the backlog ([`mvp-ticket-breakdown.md`](../../product/backlog/mvp-ticket-breakdown.md) §2.4, decision D5); the design is [ADR-0009](../adrs/0009-route-authorization-and-change-context.md); the code is `engineering/api/licensing_api/permissions.py`.

## How a check works

A user has one **role** (`users.role`) and, if they are staff, **grants** for particular states (`users.permissions`). A route asks for one **permission**. The user passes when they hold it:

```text
held in state S = the permissions their role holds everywhere
                + the permissions granted to them in S
```

S is the state in the route's path, such as `KS` in `/states/KS/applications`, or the user's own `state_code` when the path names none.

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

A value that names no permission matches nothing, so a typo denies rather than allows. Grants are read on every request, so a change takes effect on the user's next request. The F-04 staff CLI will create staff and change their grants, writing each change to `audit_log` as a security event.

## What the client sees

`GET /api/me` returns `permissions`: everything the user holds in their own state. The client shows each portal's navigation from it ([`navigation.ts`](../client/src/lib/navigation.ts)) and never from `role`. Hiding a link is not a check; the route still is.

## What a permission does not decide

A permission decides whether a user may call a route, not which rows they see. A `state_staff` user with `read_private` in Kansas sees only the PAs connected to Kansas (Rule 5 §5.6(a)), and a licensee sees only their own record. The route's query applies that scope, and a record outside it returns `404` (constitution Principle II).

## Namespaces

Every `/api` route outside `/api/health` sits under the namespace of the people who call it. `licensing_api/routes/__init__.py` assigns each resource router to one, and `tests/test_route_access.py` fails a route that breaks its namespace's rule.

| Namespace | Who calls it | Rule |
|---|---|---|
| `/me` | A PA, for their own record; any user, for their own account | Signed in |
| `/public` | Anyone: verification and published configuration | `public()` |
| `/states/{state_code}` | One state's staff, in the state the path names | `state_param='state_code'` |
| `/commission` | Commission staff, across every state | `compact_admin` |
| `/admin` | The system operator | `system_admin` |

`/commission` routes need `compact_admin`, not `read_private`: with no state in the path, `read_private` is checked in the caller's own state, so a state staff member's grant would pass.

## Declaring a route

```python
caller: Annotated[User, require(Permission.WRITE, state_param='state_code')]
```

`require()` with no permission admits any active user; `public()` declares a route anyone may call. A route that declares neither fails `tests/test_route_access.py`. The [platform contract](platform-contract.md#declaring-a-route) has the signatures and error codes.

## Changing roles and permissions

- **What a role may do:** edit `ROLE_PERMISSIONS` and the Roles table above.
- **A new permission:** add it to `Permission`, describe it in the Permissions table above, and grant it through a role or a per-state grant.
- **A new role:** a migration extending the `chk_users_role` constraint, a `Role` member, and an entry in `ROLE_PERMISSIONS`.

`tests/test_permissions.py` fails when these tables and the code disagree. A change to a role or permission is a platform change and needs the tech lead's review.
