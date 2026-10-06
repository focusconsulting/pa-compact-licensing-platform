# ADR-0004: JWT AuthClaims as the Canonical User Identity for Secured Requests

## Status

Accepted

## Date

2026-04-17

## Context

Secured API endpoints need to know which user is making the request in order to:

1. Enforce authorization (does this user have permission to perform the action?).
2. Stamp audit columns (`created_by`, `updated_by`) on mutated rows.

The API already validates a Cognito ID token on every secured route and materialises the claims into an `AuthClaims` object (`sub: UUID`, `email: str`). The `sub` field is the Cognito subject — a stable, globally-unique identifier that is also stored as `users.public_id` in the database.

Two design questions arose:

- **A.** Should query helpers accept the user's `public_id` UUID directly (from `AuthClaims.sub`), or should they accept the internal integer `users.id` (which requires a separate DB round-trip to resolve before the mutation can run)?
- **B.** Where should permission data be cached, and what key should be used?

## Decision Drivers

- Avoid unnecessary database round-trips on every secured request.
- Keep query helpers simple and side-effect-free (no implicit lookups inside a helper).
- Use a key that is stable, already available at request time, and meaningful across all services for caching permissions.
- Align with the existing pattern: `AuthClaims` is already injected into every secured route handler as a FastAPI dependency.

## Considered Options

### Option 1: Pass `AuthClaims.sub` (public UUID) directly to queries; resolve to integer ID inside the DB

Query helpers that stamp `created_by` / `updated_by` accept the user's `public_id` UUID. The caller (route handler) reads it from `claims.sub`. The query itself resolves `public_id → users.id` via a subquery or correlated expression, so `created_by` / `updated_by` columns remain integer FKs — no schema changes required. The entire operation (resolve + mutate) is a single network round-trip to the database.

**Pros:**

- One DB call over the network per mutation — resolve and write happen in the same query.
- `created_by` / `updated_by` remain integer FK columns; no schema changes.
- Route handlers stay clean: read `claims.sub`, pass it through, done.

**Cons:**

- Mutation queries are slightly more complex (subquery to resolve `public_id → id`), though this is an indexed lookup on a unique column.

### Option 2: Resolve to internal integer `users.id` before querying

Route handlers call `get_user_by_public_id` first, then pass the resulting `users.id` integer to mutation helpers.

**Pros:**

- Integer FK joins are marginally faster at large scale.
- Consistent with tables that already use integer PKs for FKs.

**Cons:**

- Every secured mutating request pays an extra `SELECT` to resolve `public_id → id`.
- Increases latency and connection pool pressure with no functional benefit at current scale.
- Makes route handlers responsible for an ID-resolution step that is boilerplate.

### Option 3: Embed user lookup inside query helpers

Mutation helpers accept the full `AuthClaims` object and look up the user internally.

**Pros:**

- Call-site is simple.

**Cons:**

- Hidden DB side-effects inside query helpers make them harder to test and reason about.
- Cannot be called without a live DB session even in unit tests.

## Decision

**Chosen option:** Option 1 — query helpers that need to identify the acting user accept `user_public_id: UUID` as an explicit argument, sourced directly from `AuthClaims.sub` in the route handler.

`AuthClaims` is the single source of truth for user identity on secured requests. Audit columns (`created_by`, `updated_by`) remain integer FK references to `users.id` — no schema changes are proposed. Instead, mutation queries are written to resolve `public_id → users.id` internally (e.g., via a subquery on the indexed `users.public_id` column), so the resolve and write happen in a single database call over the network.

For permission caching: permissions will be stored in Redis using `AuthClaim.sub` (the Cognito subject UUID) as the key suffix (e.g., `permissions:{sub}`). This key is stable, already available at the start of every request, and meaningful across services without a DB lookup.

## Consequences

### Positive

- Secured mutation endpoints incur no extra DB query for user identity resolution.
- Query helpers remain pure functions of their arguments — easier to unit-test.
- Redis permission cache keys are stable and do not depend on internal integer PKs that could change across environments.
- Consistent pattern: every route handler that needs the acting user reads `claims.sub`.

### Negative

- Mutation queries that stamp audit columns are slightly more complex — they include a subquery to resolve `public_id → users.id` rather than receiving the integer ID directly — Mitigation: this is an indexed lookup on a unique column; the complexity is contained within the query helper and invisible to callers.
- Permission cache invalidation must key on `sub`, so any permission change must explicitly evict `permissions:{sub}` from Redis — Mitigation: cache writes are centralised; eviction is straightforward.

## Related

- GitHub Issue: N/A
- Beads Task: N/A
- ADR-0003: `0003-users-table-schema-and-auth-design.md` (established `public_id` as the external identifier)

## Notes

`AuthClaims.sub` maps to the Cognito subject claim (`"sub"` in the JWT payload). It is typed as `uuid.UUID` after `AuthClaims.model_validate(claims)` runs in `get_auth_claims` (`auth.py:67-73`). Route handlers receive it as `claims.sub` with no additional parsing needed.
