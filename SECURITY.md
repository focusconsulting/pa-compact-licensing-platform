# Security

## Reporting a vulnerability

Report a vulnerability privately through GitHub's
[private vulnerability reporting](https://github.com/focusconsulting/pa-compact-licensing-platform/security/advisories/new),
not in a public issue. The data system holds practitioners' personal
information, so please don't test against a deployed environment.

## Scanning

Every pull request, every push to `main`, and a daily run on `main`
([`security.yml`](.github/workflows/security.yml)) fail on a medium, high,
or critical finding from:

| Scan | Tool | Local command |
|---|---|---|
| Python, TypeScript, and workflow code | CodeQL, `security-extended` | CI only |
| API dependencies, dev included | pip-audit | `just audit-api` |
| Client and end-to-end dependencies, dev included | `pnpm audit` | `just audit-client` |
| The API's production image | Trivy | `just scan-image` |
| Secrets in the git history | gitleaks | `just scan-secrets` |

`just security` runs all but CodeQL, with the versions CI uses.

Checkov reports on the OpenTofu, workflows, and Dockerfiles without failing
(`just scan-iac`) until SCRUM-84 hardens the infrastructure. A nightly OWASP
ZAP baseline scan of staging ([`zap.yml`](.github/workflows/zap.yml)) fails
on a medium or high alert and keeps one open issue with its latest report.

Findings the scans report but accept are in the
[false-positive register](engineering/docs/security/false-positives.md).

## Third-party materials

Each run of `security.yml` builds CycloneDX SBOMs of the API image and the
client's shipped dependencies, and from them the third-party register with
each component's licence (SOW §7.5), in its `sbom-and-third-party-register`
artifact. `just scan-image sbom` writes the same to `security-reports/`.
