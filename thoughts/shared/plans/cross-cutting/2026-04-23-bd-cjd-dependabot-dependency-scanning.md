# Dependabot Dependency Scanning Implementation Plan

## Overview

Add `.github/dependabot.yml` so GitHub automatically opens PRs when newer stable versions are available across all ecosystems in the monorepo.

## Related

- GitHub Issue: N/A
- Beads Task: pa-compact-licensing-platform-cjd
- Area: cross-cutting

## Current State Analysis

No `.github/dependabot.yml` exists. Dependencies are managed per-ecosystem but never automatically checked for newer versions.

### Key Discoveries:
- `client/` uses pnpm with `package.json` (caret ranges like `^14.2.35`) — `npm` ecosystem
- `api/` uses uv with `pyproject.toml` (`>=` constraints) + `uv.lock` — `pip` ecosystem covers uv projects
- `infrastructure/iac/components/app/terraform/` has `.terraform.lock.hcl` pinning `hashicorp/aws@5.100.0`
- `infrastructure/iac/components/ecr/terraform/` has `.terraform.lock.hcl` pinning `hashicorp/aws@5.100.0`
- `.github/workflows/` uses `actions/checkout@v4`, `pnpm/action-setup@v4`, etc. — worth keeping pinned actions updated

## Desired End State

`.github/dependabot.yml` is present and active. GitHub opens weekly PRs for outdated packages across npm, pip, terraform (×2), and github-actions. Verify via **Settings → Code security → Dependabot version updates** — all 5 ecosystems listed.

## What We're NOT Doing

- No auto-merge rules
- No custom scan workflow or Step Summary reports
- No ignore rules or pinning strategies (can be added later)

## Implementation

### Changes Required:

#### 1. New file: `.github/dependabot.yml`
**File**: `.github/dependabot.yml`

```yaml
version: 2
updates:
  # JavaScript (client/)
  - package-ecosystem: npm
    directory: /client
    schedule:
      interval: weekly
      day: monday
    open-pull-requests-limit: 10

  # Python / uv (api/)
  - package-ecosystem: pip
    directory: /api
    schedule:
      interval: weekly
      day: monday
    open-pull-requests-limit: 10

  # Terraform providers — app component
  - package-ecosystem: terraform
    directory: /infrastructure/iac/components/app/terraform
    schedule:
      interval: weekly
      day: monday
    open-pull-requests-limit: 5

  # Terraform providers — ecr component
  - package-ecosystem: terraform
    directory: /infrastructure/iac/components/ecr/terraform
    schedule:
      interval: weekly
      day: monday
    open-pull-requests-limit: 5

  # GitHub Actions
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
      day: monday
    open-pull-requests-limit: 10
```

**Notes:**
- `pip` ecosystem covers uv-managed projects — Dependabot reads `pyproject.toml` and `uv.lock`
- GitHub Actions ecosystem keeps `uses:` pins up to date
- All schedules are Monday so PRs land together and can be batch-reviewed

## Success Criteria

### Automated Verification:
- [x] Valid YAML: `npx js-yaml .github/dependabot.yml` — parsed successfully, 5 ecosystems, 5 directories, 5 schedules confirmed (2026-04-23)

### Manual Verification:
- [ ] Push to main and check **Insights → Dependency graph → Dependabot** — all 5 ecosystems active
- [ ] Navigate to **Settings → Code security → Dependabot version updates** — shows "Enabled"
- [ ] Optionally trigger a manual Dependabot check via the GitHub UI
