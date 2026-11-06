# Accepted findings

Every finding the security scans report but don't fail on is listed here,
with why and until when. A scanner's own ignore file holds the ID; this
register holds the reason. Remove an entry, and its ignore, when its
condition clears or it expires; an expired entry is a defect.

Checkov is report-only until
[SCRUM-84](https://focusdigital.atlassian.net/browse/SCRUM-84) hardens the
infrastructure, so its findings are recorded in bulk below rather than
ignored one by one.

| Scanner | ID | Where | Why accepted | Ignored in | Until |
|---|---|---|---|---|---|
| pnpm audit | [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249) (moderate) | minimatch 10, under typescript-eslint (client, dev only) | The fix, minimatch 11.0.1, is younger than pnpm's 14-day minimum release age. minimatch here expands only ESLint's own configured globs, not user input. | `engineering/client/package.json` `pnpm.auditConfig.ignoreGhsas` | 2026-11-10: override to `^11.0.1` instead |
| ZAP | 10038 CSP header not set (medium) | staging, every page | CloudFront has no response headers policy yet; SCRUM-84 adds one. | `.zap/rules.tsv` | SCRUM-84 merges |
| ZAP | 10020 anti-clickjacking header missing (medium) | staging, every page | As above. | `.zap/rules.tsv` | SCRUM-84 merges |
| Checkov | 61 OpenTofu checks | `engineering/infrastructure/iac/` | Report-only; SCRUM-84 owns them. `just scan-iac` lists them. | none (report-only) | SCRUM-84 merges |
| Checkov | CKV_GHA_7 | `.github/workflows/deploy.yml` | The `environment` input selects a GitHub Environment from a fixed list, and that Environment's protection rules gate the run; it changes no build input. | none (report-only) | permanent |
| Checkov | CKV_DOCKER_2 | `engineering/api/Dockerfile` | ECS runs the container's health check (`/api/health/live`, `ecs.tf`), and the ALB checks readiness. | none (report-only) | permanent |
| Checkov | CKV_DOCKER_3 | `engineering/mocks/cognito/Dockerfile` | The Cognito mock is local tooling, never built for or deployed to AWS. | none (report-only) | permanent |

ZAP's low and informational alerts (missing HSTS, Permissions-Policy,
cross-origin isolation, and X-Content-Type-Options headers; the `Server`
header; timestamps in bundled scripts) don't fail the scan. The headers are
SCRUM-84's; the rest are triaged with each nightly report.
