# SCRUM-75: Security scanning (F-08)

Ticket: [SCRUM-75](https://focusdigital.atlassian.net/browse/SCRUM-75).
Contract: [SOW §7.5](../../../../../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md#75-intellectual-property-and-open-source)
(third-party register); QASP (no medium or high findings).
No flows are touched.

## Decisions (2026-11-06, Stephen)

- **Gate**: a medium, high, or critical finding in any dependency, shipped
  or dev-only, fails the PR. Dev tooling runs in CI beside secrets.
- **Checkov is report-only** until SCRUM-84 (infrastructure hardening)
  fixes the 61 OpenTofu findings; it uploads SARIF and never fails a PR.
- **Next 16 and React 19.** The constitution's Next 14 / React 18 pins
  are removed; the client moves to Next 16 and React 19 to clear Next's
  critical advisories.
- **Fixes land as separate PRs** before the scanning PR, which merges last
  so it is green on arrival. No PR is pushed without Stephen's approval.
- **ZAP targets staging** (`site.dev-pacompact.aws.focusconsulting.io`);
  it is the only deployed environment.

## Baseline (2026-11-06, `main` at f355c8f)

| Scanner | Findings |
|---|---|
| pip-audit (API, no dev) | 47 in 11 packages; python-jose and ecdsa have no fix |
| Trivy, API image | 35 Python; msgpack, urllib3, setuptools are pip's vendored copies |
| pnpm audit (client) | 99: 6 critical, 43 high; Next and postcss ship, the rest are dev tooling |
| pnpm audit (e2e) | 0 |
| Checkov, OpenTofu | 61 (SCRUM-84) |
| Checkov, workflows | 5 top-level permissions, 1 `workflow_dispatch` input (deploy, by design) |
| Checkov, Dockerfiles | HEALTHCHECK (ECS checks health), no USER (cognito mock, local only) |

## Pull requests, in merge order

1. **`fix/SCRUM-75-api-dependencies`**: upgrade the vulnerable API
   packages in `uv.lock`; drop pip (and its vendored urllib3, msgpack,
   setuptools) from the production image.
2. **`fix/SCRUM-157-pyjwt`**, stacked on 1: replace python-jose with
   PyJWT (removes ecdsa); ADR-0017; constitution's stack line. Stacked
   because both rewrite `uv.lock`, and resolving that conflict by taking
   one side silently drops the other's upgrades.
3. **`feature/SCRUM-75-next-16`**: Next 16.4.3, React 19; builds stay on
   webpack (the USWDS theme's Sass function can't cross into Turbopack).
   Carries Stephen's constitution edit removing the Next 14 / React 18 pins.
4. **`fix/SCRUM-75-client-dev-dependencies`**, stacked on 3: vitest 4,
   overrides for compression and webpack-dev-middleware, and a time-boxed
   audit ignore for minimatch (GHSA-g3hv-75wg-m249) until minimatch 11.0.1
   clears the 14-day release age on 2026-11-10.
5. **`fix/SCRUM-75-workflow-permissions`**: `contents: read` by default in
   every workflow; third-party actions pinned to SHAs (CodeQL
   `actions/unpinned-tag`).
6. **`feature/SCRUM-75-security-scanning`**: the scanners.
   - Root `justfile` recipes with pinned tool versions (`audit-api`,
     `audit-client`, `scan-image`, `scan-secrets`, `scan-iac`, `sbom`;
     `security` runs the gating ones). CI calls the same recipes.
   - `security.yml` on every PR, push to `main`, and daily: CodeQL
     (`security-extended`, Python, TypeScript, Actions) gated at
     security-severity ≥ 4.0 by `scripts/security/findings-gate.py`;
     the recipes; Checkov report-only to the job summary; SBOMs and the
     third-party register as an artifact.
   - `zap.yml`: nightly ZAP baseline of staging, gated at medium by the
     same script, honouring `.zap/rules.tsv` IGNOREs (ZAP itself still
     writes ignored alerts to its JSON).
   - `SECURITY.md`; `engineering/docs/security/false-positives.md`.
   - gitleaks pre-commit hook moves to v8.30.1, the version CI runs.

## Success criteria

- [x] Each fix PR: the scanner it targets is clean of medium+ locally;
      the component's lint, typecheck, and coverage gates pass.
- [x] All six merged together (scratch worktree, 2026-11-06): `just
      security` exits 0; on `main` it fails (pip-audit).
- [x] The register generated from the SBOMs lists every shipped
      component with its licence, or "not declared" (43 client
      platform-specific binaries not installed on the scanning host, and
      USWDS, whose package.json has no `license` field).
- [x] ZAP against staging triaged: two mediums (CSP, anti-clickjacking)
      belong to SCRUM-84 and are in the register; lows are SCRUM-84's
      headers or noise.
- [ ] CI green on each PR once pushed.
- [ ] Repository settings (admin): private vulnerability reporting on;
      CodeQL default setup off, or it rejects this workflow's uploads.
