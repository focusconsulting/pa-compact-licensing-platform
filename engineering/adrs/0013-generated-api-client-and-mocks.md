---
category: architecture
status: proposed
date: 2026-10-23
---

# ADR-0013: Generated API Client and Mocks

## Status

Proposed

## Date

2026-10-23

## Context

The client describes each API response by hand (`client/src/app/page.tsx`'s `CurrentUser`), so a change to a route's model reaches the client only when someone notices. SCRUM-79 asks for a TypeScript client generated from the API's OpenAPI document, mocks from the same document so Storybook and tests run with no API, one command that regenerates both, and a CI check that fails when the committed document drifts from the code.

FastAPI already produces the document (`app.openapi()`). What remains is choosing the generators and the runtime client.

## Decision

1. **The document is committed.** `just openapi` writes `engineering/api/openapi.json` with sorted keys. `tests/test_openapi.py` fails while it differs from the code, so drift fails the API's existing test job.
2. **Types from [openapi-typescript](https://openapi-ts.dev/).** `pnpm generate` writes `src/api/schema.d.ts`: types only, no runtime code.
3. **Calls through [openapi-fetch](https://openapi-ts.dev/openapi-fetch/).** A typed `fetch` wrapper over those types; middleware adds the Cognito token (SCRUM-79 part 3).
4. **Mocks from the API's examples.** Every model a route returns carries an example, which `tests/test_openapi.py` requires. `scripts/generate-mocks.mjs` writes `src/api/mocks.ts`, one [MSW](https://mswjs.io/) handler per operation. Each handler answers with its success status and a body built from those examples; the `Data` and `Paged` envelopes are built around them.
5. **One command, one check.** `just generate` runs both steps. The client's CI regenerates from the committed document and fails on any difference in `src/api`.
6. **MSW 2.** [msw-storybook-addon](https://github.com/mswjs/msw-storybook-addon) 3 needs Storybook 9, and its version 2 needs MSW 2. MSW 3 waits for the Storybook upgrade.

## Pros and cons

### openapi-typescript + openapi-fetch + example-driven MSW handlers (chosen)

- Pro: the types are a `.d.ts` file. Nothing generated runs in the browser except the handlers, which run only in tests and Storybook.
- Pro: openapi-fetch is about 6 kB with no dependencies and uses the platform `fetch`, so `authFetch`'s behaviour carries over.
- Pro: mock bodies are the examples the API documents, so a reviewer reads the same data in the docs, the stories, and the tests.
- Pro: the mock generator is about 80 lines we can read and change (Principle I).
- Con: the mock generator is ours to maintain, and it knows the `Data` and `Paged` envelopes.
- Con: every response model needs a hand-written example; the test makes forgetting one fail.
- Con: no React hooks are generated; pages call the client directly.

### orval

- Pro: one tool generates types, a client (fetch, axios, or React Query hooks), and MSW handlers.
- Con: its mocks are random data from Faker, a further dependency, so stories and snapshots change unless seeded.
- Con: it generates runtime code per operation, a much larger generated surface to review on every API change.
- Con: its config file is another thing to learn when the output is wrong.

### hey-api (`@hey-api/openapi-ts`)

- Pro: generates types, an SDK of typed functions, and plugins for validators and query libraries.
- Con: it generates runtime code per operation, as orval does.
- Con: no MSW output; mocks would still be ours.

### msw-auto-mock (mocks only)

- Pro: generates MSW handlers from a document with no code of ours.
- Con: random Faker data, as with orval, and it does not read the examples the document carries.
- Con: a third generator beside the types and the client.

### Hand-written types and mocks (today)

- Pro: no dependencies.
- Con: nothing tells the client when the API changes; the drift SCRUM-79 asks CI to catch is invisible.

## Consequences

- New client dependencies: `openapi-fetch`; dev `openapi-typescript`, `msw`, `msw-storybook-addon` (listed in the client README).
- A route's model change shows up as a diff in `openapi.json`, `schema.d.ts`, and `mocks.ts` in the same PR. These are generated files (Principle XV); review the model, not them.
- A PR that changes only the API's document still runs the client's CI, which catches a change the client no longer compiles against.
- FastAPI drops `null` values from examples, so the mock generator fills a missing nullable field with `null`.
- Every `/api` route documents its `422` as `ErrorResponse`, the body the API sends, in place of FastAPI's default `HTTPValidationError`, so the generated error type is right.
