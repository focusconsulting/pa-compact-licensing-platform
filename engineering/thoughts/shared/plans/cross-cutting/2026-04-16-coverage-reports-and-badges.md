# Coverage Reports and Badges Implementation Plan

## Overview

Add test coverage reporting to CI for both the API (Python/pytest) and client
(Next.js/vitest), publish results to Codecov with per-component flags, and
display separate coverage badges on the root README.

## Related

- GitHub Issue: N/A
- Beads Task: pa-compact-licensing-platform-tv3
- ADRs: N/A
- **Area**: cross-cutting (API CI + Client CI)

## Current State Analysis

- **API**: Already runs `coverage.py` with `--branch` in CI (`coverage run … -m
  pytest` + `coverage report`), but the `.coverage` SQLite file is never uploaded
  anywhere. No XML export.
- **Client**: Runs `vitest run` in CI with zero coverage configuration.
  `@vitest/coverage-v8` not installed. `vitest.config.ts` has no `coverage` block.
- **README**: No badges of any kind in `/README.md`, `api/README.md`, or
  `client/README.md`.

### Key Discoveries

- `.github/workflows/api.yml:71-74` — existing coverage run; only missing `coverage xml` and upload step.
- `.github/workflows/client.yml:58-59` — `pnpm test` maps to `vitest run`; no `--coverage`.
- `client/vitest.config.ts:7-13` — `test` block present, no `coverage` key.
- `client/package.json:10` — `"test": "vitest run"`; `"test:coverage"` script absent.
- Codecov supports **flags** (`api`, `client`) for separate badge URLs from a single repo.

## Desired End State

- Both CI workflows upload coverage to Codecov on every push and PR.
- Codecov dashboard at `codecov.io/gh/focusconsulting/pa-compact-licensing-platform`
  shows two flag graphs (`api` / `client`).
- Root `README.md` shows two live coverage badges immediately below the title.
- PRs receive Codecov bot comments with diff coverage breakdown.

### Verification

- Open a PR touching `api/**` → API CI uploads coverage; Codecov comment appears.
- Open a PR touching `client/**` → Client CI uploads coverage; Codecov comment appears.
- Both badges in README render with a percentage (not "unknown").

## What We're NOT Doing

- Coverage enforcement thresholds (can add Codecov `codecov.yml` in a follow-up).
- Coverage badges per sub-README (`api/README.md`, `client/README.md`).
- Self-hosted or gist-based badge approach (Codecov chosen).
- HTML coverage report artifacts in GitHub Actions.

---

## Manual Prerequisites (one-time, before CI will succeed)

1. Go to **codecov.io** and sign in with GitHub.
2. Add the repository `focusconsulting/pa-compact-licensing-platform`.
3. Copy the **CODECOV_TOKEN** from the Codecov dashboard.
4. Add it as a GitHub Actions secret:
   GitHub → repo → Settings → Secrets and variables → Actions → New repository secret
   Name: `CODECOV_TOKEN`
5. **If repo is private**: the badge URLs need a `?token=<graphing-token>` suffix.
   Get the graphing token from Codecov → Settings → Badge, then update `README.md`.

---

## Phase 1: API Coverage Upload

### Overview

Generate an XML coverage report after the existing pytest run and upload it to
Codecov with `flags: api`.

### Changes Required

#### 1. `.github/workflows/api.yml` — test job

**Before** (lines 71-74):

```yaml
- name: Run tests with coverage
  run: |
    uv run --env-file .env.example coverage run --branch --source=licensing_api -m pytest
    uv run coverage report
```

**After**:

```yaml
- name: Run tests with coverage
  run: |
    uv run --env-file .env.example coverage run --branch --source=licensing_api -m pytest
    uv run coverage report
    uv run coverage xml

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v5
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    flags: api
    files: api/coverage.xml
    fail_ci_if_error: true
```

### Success Criteria

#### Automated Verification
- [ ] `coverage xml` generates `api/coverage.xml` (run locally: `uv run coverage xml`)
- [ ] Codecov action step completes without error in GitHub Actions logs

#### Manual Verification
- [ ] Codecov dashboard shows `api` flag with a coverage percentage
- [ ] PR Codecov comment includes API diff coverage

---

## Phase 2: Client Coverage Collection and Upload

### Overview

Install `@vitest/coverage-v8`, configure vitest to collect lcov coverage, add a
dedicated `test:coverage` CI script, and upload to Codecov with `flags: client`.
The existing `pnpm test` script is unchanged so local watch mode is unaffected.

### Changes Required

#### 1. Install coverage package

```bash
cd client && pnpm add -D @vitest/coverage-v8@^3.2.1
```

Must match the `vitest@^3.x` major version already in use.

#### 2. `client/vitest.config.ts` — add coverage block

```ts
test: {
  environment: "jsdom",
  globals: true,
  setupFiles: ["./src/tests/setup.ts"],
  include: ["src/**/*.test.{ts,tsx}"],
  css: false,
  coverage: {
    provider: "v8",
    reporter: ["text", "lcov"],
    include: ["src/**/*.{ts,tsx}"],
    exclude: [
      "src/tests/**",
      "src/**/*.test.{ts,tsx}",
      "src/**/*.stories.{ts,tsx}",
      "src/**/*.d.ts",
    ],
  },
},
```

#### 3. `client/package.json` — add test:coverage script

```json
"test:coverage": "vitest run --coverage",
```

#### 4. `.github/workflows/client.yml` — test job

**Before** (line 58-59):

```yaml
- name: Run tests
  run: pnpm test
```

**After**:

```yaml
- name: Run tests with coverage
  run: pnpm test:coverage

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v5
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    flags: client
    files: client/coverage/lcov.info
    fail_ci_if_error: true
```

### Success Criteria

#### Automated Verification
- [x] `cd client && pnpm test:coverage` runs all tests and emits `coverage/lcov.info`
- [ ] Codecov action step completes without error in GitHub Actions logs

#### Manual Verification
- [ ] Codecov dashboard shows `client` flag with a coverage percentage
- [ ] PR Codecov comment includes client diff coverage

---

## Phase 3: README Badges

### Overview

Add two Codecov badge lines to the root `README.md` immediately below the title.

### Changes Required

#### `README.md`

```markdown
# PA Compact Licensing Platform

[![API Coverage](https://codecov.io/gh/focusconsulting/pa-compact-licensing-platform/branch/main/graph/badge.svg?flag=api)](https://codecov.io/gh/focusconsulting/pa-compact-licensing-platform)
[![Client Coverage](https://codecov.io/gh/focusconsulting/pa-compact-licensing-platform/branch/main/graph/badge.svg?flag=client)](https://codecov.io/gh/focusconsulting/pa-compact-licensing-platform)
```

> **Private repo note**: append `&token=<graphing-token>` to each badge URL.
> Graphing token is available under Codecov → repo → Settings → Badge.

### Success Criteria

#### Automated Verification
- [x] `README.md` contains both badge image links

#### Manual Verification
- [ ] Both badges render with a percentage on the GitHub repo page (not "unknown")
- [ ] Clicking a badge opens the Codecov dashboard for the correct flag

---

## Testing Strategy

### Automated Tests
No new unit or integration tests required — this is purely CI infrastructure.

### CI Verification Steps
1. Push this branch → GitHub Actions triggers both `API CI` and `Client CI`.
2. Confirm both `Upload coverage to Codecov` steps succeed in the Actions UI.
3. Open the Codecov dashboard and verify two separate flag entries.
4. Open a PR against main; verify the Codecov bot posts a coverage comment.

## References

- `.github/workflows/api.yml` — API CI pipeline
- `.github/workflows/client.yml` — Client CI pipeline
- `client/vitest.config.ts` — vitest configuration
- `client/package.json` — client scripts
- `README.md` — project README
- Codecov flags docs: https://docs.codecov.com/docs/flags
