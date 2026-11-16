# End-to-end tests

Playwright tests of the whole system: the client, the API, and the local
mocks, signing in through cognito-local with password auth, which locally
replaces SRP ([ADR-0010](../adrs/0010-local-sign-in-uses-password-auth.md)).
Every page a test visits is scanned with axe for WCAG 2.1
A and AA, colour contrast included (constitution Principle V).

```bash
just up     # in one terminal, from the repo root
just e2e    # in another
```

`E2E_BASE_URL` points the tests elsewhere (default `http://localhost:3000`).
CI runs them on every pull request that touches `engineering/`, against the
same local stack, in [`e2e.yml`](../../.github/workflows/e2e.yml); the test
step must finish in 5 minutes.

## Writing tests

- One spec per user flow in [`product/context/flows/`](../../product/context/flows/),
  golden path and at least one error path.
- `test.describe`, `test`, and `test.step` titles are written for a
  non-technical reader; the product manager reviews them at story acceptance.
- Import `test` and `expect` from [`tests/fixtures.ts`](tests/fixtures.ts) and
  call `expectAccessible(page)` on every page the test reaches.
- Sign in as a user from
  [`engineering/mocks/cognito/db/local_licensing.json`](../mocks/cognito/db/local_licensing.json).
  `signIn(page, demoPa("sam.submitted"))` signs in as a practitioner from
  `just seed demo` ([`docs/demo.md`](../docs/demo.md) lists them), which CI
  loads. Locally, run `just seed demo` once `just up` is running.
- A spec that changes a demo practitioner, as `application.spec.ts` does to
  Ned Bar-Ended, needs a fresh seed: `just infra` in `engineering/api`, then
  `just migrate`, `just seed`, and `just seed demo`.
