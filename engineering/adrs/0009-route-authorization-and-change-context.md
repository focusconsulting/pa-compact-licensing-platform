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

Epic 2's contract step (beads `pa-compact-licensing-platform-4gi.2`) fixes how every feature records a change and how every route declares who may call it. Two earlier decisions pull in different directions:

- ADR-0004 identifies the caller by `AuthClaims.sub` and writes `created_by` and `updated_by` through a subquery on `users.public_id`, so a write needs no prior lookup. It also proposed caching permissions in Redis.
- Backlog decision D5 reads permissions from the database on every request, with no cache at pilot scale.

The write helpers (`emit`, `history.write`, `audit.write`, `notify`) need the actor and the request ID on every call, from routes and from the Worker, which has no token and writes as the system user (ADR-0005).

## Decision

1. **`require(*roles, permission=None, state_param=None)`** is the dependency every authenticated route declares. On each request it verifies the token, loads the caller's `users` row, and checks:
   - the user exists and is active (`403 USER_NOT_FOUND`, `403 USER_INACTIVE`);
   - the user's role is one of `roles` (`403 FORBIDDEN`);
   - when `permission` is given and the caller is state staff, `permission` is in `users.permissions[<state>]`, where the state is the path parameter named by `state_param`, or the caller's `state_code` when there is none (`403 FORBIDDEN`). `compact_admin` and `admin` pass this check only when the route lists their role (constitution Principle VII).

   Permissions are read from the database per request (D5). This supersedes ADR-0004's Redis permission cache.
2. **`public()`** is the declaration for a route with no caller check. A test fails when an `/api` route declares neither.
3. **First sign-in.** When no user has the token's `sub` as `public_id`, `require` links it to the active user with the token's email, as `/me` does today, so the link does not depend on which route a user calls first.
4. **`ChangeContext(actor, request_id)`** is passed explicitly to every write helper. `Actor` is a token `sub` or the system user. `actor_id(actor)` is a scalar subquery on `users.public_id` (or the system user's email), so audit columns are still resolved in the same statement as the write (ADR-0004, constitution Principle VI). Routes get the context from a dependency; the Worker builds one for the system user.
5. **Request ID.** Middleware reads `X-Request-ID` when it is a short token, otherwise generates a UUID, returns it on the response, and writes it to the request log line. `ChangeContext.request_id` carries it into `domain_events` and `audit_log`.

## Consequences

- Every authenticated request reads one `users` row. At pilot scale that is cheaper than running a cache, and a permission change takes effect on the next request.
- A route that forgets its declaration fails CI instead of shipping open.
- Feature code never resolves a user's numeric id to write; it passes the context.
- Domain-record scoping (returning `404` for a record outside the caller's state) stays in each route's query: `require` decides who may call a route, not which rows they see (constitution Principle II).
- F-04 (epic 5) builds on `require`: MFA enforcement, the permission matrix test, and the staff CLI.
