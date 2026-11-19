---
category: architecture
status: proposed
date: 2026-11-17
---

# ADR-0020: A Development-Only List of Users on the Sign-in Page

## Status

Proposed

## Date

2026-11-17

## Context

The local stack has 22 users in the Cognito mock, one for each state a
practitioner or a staff member can be in
([`demo.md`](../docs/demo.md)). Checking a change by hand means signing
in as several of them, each time typing an address such as
`eli.withdrawn-eligibility@demo.example` and the password they all
share. That cost is paid many times a day, and it grows with every
state the seed adds.

The constitution's
[Principle IV](../engineering-constitution.md#iv-no-mock-code-in-production)
forbids the obvious fix: no code path that changes behavior by
environment, and no seed data in code the client ships. Its reason is
that the code a developer runs should be the code production runs, and
that test data and test credentials must never reach a deployed
environment. An exception needs an ADR.

## Decision

1. **The sign-in page shows a list of the mock's users in a build that
   sets `NEXT_PUBLIC_DEV_SIGN_IN_PASSWORD`.** Choosing one fills the
   form with their address and that password, and submits it. Sign-in
   itself is unchanged: the same call, to the same identity provider,
   as typing the two values.

2. **A deployed build does not contain the list.** The setting is read
   at build time. Empty, the page's reference to the list is a constant
   `null`, and the bundler drops the module
   ([`DevSignIns.tsx`](../client/src/components/DevSignIns.tsx)) with
   it. `just deploy` sets it empty explicitly, as it does every other
   `NEXT_PUBLIC_*` value, so a laptop's settings cannot turn it on.

3. **No user and no password is written in the client.** The list is
   read from the mock when the page loads, with Cognito's own
   `ListUsers` call, which deployed Cognito refuses without AWS
   credentials. The password comes from the setting, and
   [`.env.example`](../client/.env.example) holds its local value, as
   it holds every other local-only value.

4. **A check proves it.**
   [`check-deployed-build.sh`](../client/scripts/check-deployed-build.sh)
   fails if a built client contains the list. The E2E workflow builds
   the client with the setting empty and runs the check, so every pull
   request is tested against the client a deploy would build.

## Pros and cons

### A list in the page, compiled out of deployed builds (chosen)

- Good: one click to sign in as any seeded user, where the developer
  already is.
- Good: nothing about it reaches a deployed environment, and a check
  fails the build if that stops being true.
- Good: the list cannot go stale: it is whatever the mock holds.
- Bad: the local build and the deployed build differ by this block. The
  E2E tests run the deployed shape, so they do not cover the block; unit
  tests do.
- Bad: it is a build-time switch, which Principle IV exists to prevent.
  The next one will cite this ADR.

### A separate page under `engineering/mocks`

- Good: the client is untouched, so no exception is needed.
- Bad: it cannot sign in for the developer without the client accepting
  a password from outside the form, such as in a link, which is worse
  than the switch it avoids.
- Bad: a second page to keep open.

### A runtime check of the environment

- Bad: the list, and the shared password with it, would be in every
  deployed bundle, hidden only by a condition.

### Nothing

- Good: no exception.
- Bad: the cost stays, and people work around it with browser password
  managers and scripts that nobody reviews.

## Consequences

- The block's strings are written in its component and not in an i18n
  file, so that they are compiled out with it. This is a second,
  narrower exception, to
  [Principle X](../engineering-constitution.md#x-leverage-uswds-exclusively):
  the block is for developers, and is never shown to a user.
- `backfill@example.com` has a different, temporary password
  ([Cognito mock](../mocks/cognito/README.md)). Choosing it from the
  list fails with the provider's message, and the form keeps what was
  tried.
- An environment that should have the list, such as a shared demo
  stack running the mock, turns it on by setting the value at build
  time. An environment that uses real Cognito gains nothing by setting
  it: the list would be empty, and the password would be published in
  the bundle. `just deploy` never sets it.
- A developer whose `.env` predates this adds the line from
  `.env.example` to get the list.
