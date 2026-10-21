---
category: architecture
status: proposed
date: 2026-10-14
---

# ADR-0009: Route Authorization and Change Context

## Status

Proposed

## Date

2026-10-14

## Context

Epic 2's contract step (SCRUM-77) fixes how every feature records a change and how every route declares who may call it. Two earlier decisions pull in different directions:

- ADR-0004 identifies the caller by `AuthClaims.sub` and writes `created_by` and `updated_by` through a subquery on `users.public_id`, so a write needs no prior lookup. It also proposed caching permissions in Redis.
- Backlog decision D5 reads permissions from the database on every request, with no cache at pilot scale.

Checking permissions per request means every authenticated request loads the caller's `users` row anyway, which removes ADR-0004's reason for the subquery.

## Decision

1. **Routes name permissions, never roles.** `require(permission=None, *, state_param=None)` is the dependency every authenticated route declares, and yields the caller's `User`. A role is a named set of permissions, fixed in code (`ROLE_PERMISSIONS`); staff also hold per-state grants in `users.permissions[<state>]` (D5). A caller passes when they hold `permission` through their role or in the route's state: the path parameter named by `state_param`, or their own `state_code` when there is none.
   - Role permissions: `licensee` has `manage_own_record`; `state_staff` and `state_admin` have `read_general`; `compact_admin` and `admin` have `read_general`, `read_private`, and `compact_admin`.
   - Per-state grants: `read_private`, `read_ssn`, `write`, `admin`.
   - Unknown user `403 USER_NOT_FOUND`; inactive `403 USER_INACTIVE`; missing permission `403 FORBIDDEN`. `require()` with no permission admits any active user.
   - Commission users reach state data only through the permissions their role grants: `read_private` lets them read any state's records; nothing in their role lets them write a state's records (constitution Principle VII).
2. **`public()`** is the declaration for a route with no caller check. A test fails when an `/api` route declares neither.
3. **First sign-in.** `current_user`, the dependency `require` and `change_context` share, finds the user by the token's `sub`. When none has it, it links the active user with the token's email, so the link does not depend on which route a user calls first. It links only a user with no `sub` yet: a user already linked to another `sub` (the same email in the other Cognito pool, D4) is not this caller, and gets `403 USER_NOT_FOUND`.
4. **`ChangeContext(user_id, request_id)`** is passed explicitly to every write helper. `user_id` is the `users.id` of the user `current_user` loaded, so audit columns, history, events, and the audit log record it with no further lookup. The Worker builds a context for the system user (ADR-0005). This supersedes ADR-0004's subquery.
5. **History records changes; the audit log records access.** A write records its rows, a history row, and an event. `audit_log` is for what history cannot hold: staff reads of private data (an SSN reveal, a document download) and security events (a permission change, a deactivation, an expungement).
6. **Request ID.** Middleware reads `X-Request-ID` when it is a short token, otherwise generates a UUID, returns it on the response, and writes it to the request log line. `ChangeContext.request_id` carries it into `domain_events` and `audit_log`.

## Consequences

- Every authenticated request reads one `users` row. At pilot scale that is cheaper than running a cache, and a permission change takes effect on the next request.
- A route that forgets its declaration fails CI instead of shipping open.
- Changing what a role may do is a change to `ROLE_PERMISSIONS`, not to every route that role uses.
- Feature code never resolves a user's numeric id to write; it passes the context.
- A mutation writes no audit row, so the audit log stays a record of who looked at what.
- Domain-record scoping (returning `404` for a record outside the caller's state) stays in each route's query: `require` decides who may call a route, not which rows they see (constitution Principle II).
- F-04 (epic 5) builds on `require`: MFA enforcement, the permission matrix test, the staff CLI, and where a Commission user's `read_ssn` grant is held.
