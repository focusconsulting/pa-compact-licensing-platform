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
4. **A mock server from the API's examples, outside the client.** `just mock-api` runs [Prism](https://github.com/stoplightio/prism) in Docker against the committed document. It answers each route with its success status and the examples on the API's response models, which `tests/test_openapi.py` requires; the `Data` and `Paged` envelopes are built around them. The client reaches it through its production code, pointed at `http://localhost:4010` by `NEXT_PUBLIC_API_BASE_URL`, so no mocking code is committed in the client.
5. **One command, one check.** `just generate` writes the document and the types. The client's CI regenerates the types from the committed document and fails on any difference in `src/api`.

## Pros and cons

### openapi-typescript + openapi-fetch + Prism (chosen)

- Pro: the types are a `.d.ts` file, so nothing generated runs in the browser.
- Pro: openapi-fetch is about 6 kB with no dependencies and uses the platform `fetch`, so `authFetch`'s behaviour carries over.
- Pro: mock bodies are the examples the API documents, so a reviewer reads the same data in the docs and the running mock.
- Pro: Prism is a separate server, like the other local stand-ins (Principle IV): the client runs its production code against it, and no mock code or dependency enters the client.
- Pro: Prism checks each request against the document, and rejects a call with no bearer token as the API does.
- Con: every response model needs a hand-written example; the test makes forgetting one fail.
- Con: FastAPI drops `null` values from examples, so `scripts/export_openapi.py` puts them back before writing the document.
- Con: the image is amd64-only (emulated on Apple silicon) and needs `-m false` to start.
- Con: unit tests and Storybook need the server running, or their own stubs, to reach an API.
- Con: no React hooks are generated; pages call the client directly.

### openapi-typescript + openapi-fetch + generated MSW handlers

- Pro: tests and Storybook answer API calls in-process, with no server to start.
- Con: a generator of ours (about 80 lines) and the handlers it writes are committed in the client, alongside the `msw` dependency.
- Con: the generator knows the `Data` and `Paged` envelopes and fills dropped `null`s itself.
- Con: MSW 3 needs Storybook 9 for its addon, so MSW stays pinned to 2.

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

- New client dependencies: `openapi-fetch`; dev `openapi-typescript` (listed in the client README). Prism is a pinned Docker image, `stoplight/prism:5.15.10`, run by the root `justfile`.
- A route's model change shows up as a diff in `openapi.json` and `schema.d.ts` in the same PR. These are generated files (Principle XV); review the model, not them.
- A PR that changes only the API's document still runs the client's CI, which catches a change the client no longer compiles against.
- `scripts/export_openapi.py` fills a required field an example leaves out with `null`; a test fails if that field is not nullable.
- Every `/api` route documents its `422` as `ErrorResponse`, the body the API sends, in place of FastAPI's default `HTTPValidationError`, so the generated error type is right.
