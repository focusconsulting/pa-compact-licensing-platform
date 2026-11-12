---
category: architecture
status: proposed
date: 2026-11-09
---

# ADR-0017: State Standing and Relationship Scoping

## Status

Proposed

## Date

2026-11-09

## Context

Epic 5's contract step (SCRUM-103) fixes the permission matrix every later route builds against. Three gaps in [ADR-0009](0009-route-authorization-and-change-context.md) show up once the matrix is written out:

- **Role permissions hold in every state.** `held_permissions` adds a role's permissions to whatever state the route names. A `/states/MO/...` route that requires `read_general` therefore admits a Kansas staff member, and `compact_admin` passes every `/states/{state_code}` route that asks for `read_general` or `read_private`.
- **A Commission user's `read_ssn` has nowhere to live.** It is a per-state grant, and a Commission user has no `state_code`, so on a `/commission` route no grant ever applies. ADR-0009 left this to epic 5.
- **"My state is the SQL for this PA" and "my state is a remote state for this PA" are undefined.** Constitution Principle II scopes state staff by that relationship, and Rule 4 §4.6(a) gives a state the uniform data set of "every applicant and licensee who holds a Qualifying License or Compact Privilege" there. No code or document says which rows establish it.

## Decision

1. **A state path needs standing.** Under `/states/{state_code}`, a caller passes `require` only when they belong to that state: their `state_code` is that state, or they hold at least one grant there. Without standing, the caller gets `403 FORBIDDEN` whatever permissions their role holds. Commission users read state data through `/commission` routes, never through `/states/{state_code}`. With standing, role permissions and that state's grants combine as ADR-0009 describes.
2. **Commission grants use the key `*`.** `users.permissions` may hold `{"*": ["read_ssn"]}` for a `compact_admin` user. When the caller has no `state_code` and the route names no state, `require` reads the `*` grants. The key gives no standing in any `/states/{state_code}` path, and `read_ssn` is the only permission granted under it. No role holds `read_ssn`: each Commission user who may reveal an SSN is granted it individually, and every reveal is audited ([ADR-0007](0007-ssn-storage.md)). The system operator (`admin`) is not given it (backlog §2.4).
3. **Relationships are SQL predicates in one module.** `licensing_api/repo/scope.py` defines, over `practitioners.id`:
   - `is_sql_for(state_code)`: a participation application names the state as `sql_state_code` and has left `draft`.
   - `is_remote_for(state_code)`: a privilege request names the state as `remote_state_code` and has left `pending_payment`. Every privilege comes from such a request, so this covers privileges too.
   - `holds_license_in(state_code)`: a qualifying license in the state is linked to the practitioner.
   - `related_to(state_code)`: any of the three.

   Routes compose these into their queries, and a record outside them returns `404`. An action on one record checks that record's own state column (`participation_applications.sql_state_code` for an eligibility decision, `privilege_requests.remote_state_code` for issuance), not the union.
4. **A relationship, once formed, persists.** A denied, withdrawn, or superseded application, and a denied or withdrawn request or an expired privilege, keep the state related to the PA. That state was a party to the record and needs it for appeals (Rule 3 §3.9(a)) and discipline. Drafts and unpaid requests never form a relationship, because no state has received them.

## Alternatives

- **No standing check; rely on query scoping alone.** This was rejected because a route that forgets its scope would then leak across states, and the permission check is the layer `tests/test_route_access.py` can see.
- **A per-state `read` grant on every state route.** This was rejected because every staff user would need an explicit grant to see anything, and `read_general` would mean nothing.
- **`read_ssn` as a `compact_admin` role permission.** This was rejected because every Commission user could reveal any SSN, against constitution Principle VII's opt-in permissions.
- **A `v_practitioner_state_relationships` view.** This was rejected for now because predicates compose into route queries without another platform-owned SQL object. A report that needs the relationship in SQL can wrap them in a view later.
- **Current relationships only** (open applications, active privileges, held licenses). This was rejected because a state would lose sight of its own decisions.

## Consequences

- SCRUM-104 adds the standing check and the `*` key to `require` and `held_permissions`, and adds `repo/scope.py` with tests. The permission matrix in the [platform contract](../docs/platform-contract.md#permission-matrix) is the table its role × endpoint test drives.
- A `/commission` route that also needs `read_ssn` declares `require(Permission.COMPACT_ADMIN)` on its router and `require(Permission.READ_SSN)` on the route. The namespace rule reads the router's declaration.
- A Commission user configuring one state uses a `/commission/states/{state_code}` route, not the state's own settings route.
- Search (epic 10), document downloads (SCRUM-81), and every state queue use the same predicates, so "who can see this PA" has one answer.
- Supersedes ADR-0009's open item on where a Commission user's `read_ssn` is held.
