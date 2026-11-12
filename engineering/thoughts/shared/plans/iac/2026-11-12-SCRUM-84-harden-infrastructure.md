# Harden the Infrastructure Implementation Plan

## Overview

Put the security controls the contract and the constitution require around the running system: TLS on every hop, security headers, a web firewall with rate limits, a customer-managed key and a protected database, an audit trail, a test that fails on a non-US region, a clean Checkov run that gates pull requests, and an OWASP ASVS 5.0 mapping. Six pull requests.

## Related

- **Spec**: epic 3 in [MVP epics and tickets](../../../../../product/backlog/mvp-jira-tickets.md) and F-10 in the [MVP ticket breakdown](../../../../../product/backlog/mvp-ticket-breakdown.md)
- **Flows**: none directly
- **Compact rules**: [Rule 4 §4.5](../../../../../product/context/research-corpus/sources/rule-4-compact-data-system--confidentiality-information-sharing.md) (confidentiality). Contract: [SOW §2](../../../../../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md#2-scope-of-work) (United States only), [SOW §5.2](../../../../../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md#52-quality-standards) (QASP "Secure Code", ASVS 5.0)
- **Decisions**: Q-28 (US-only; its default is US regions and a geo-restricted CDN). On SCRUM-69, 2026-10-28: every Checkov finding is fixed, not baselined. In this plan's session, 2026-11-12 (Michael Kalish):
  - Checks with no sensible fix are skipped inline with a reason and a row in the false-positive register.
  - The load balancer to API hop uses a certificate the container generates at start; one CA-issued certificate on every hop is SCRUM-192, for production.
  - `script-src` allows `'unsafe-inline'`, since a static export cannot use nonces.
  - ZAP runs after each deploy and on a manual trigger, not on a nightly schedule.
  - Staging is spun up and torn down by design and holds nothing that must survive, so no phase preserves its data or plans around its downtime, and whatever blocks a teardown is a per-environment setting.
- **Scanning this plan builds on**: [PR #181](https://github.com/focusconsulting/pa-compact-licensing-platform/pull/181) (SCRUM-75, Stephen Jordan), open and unreviewed on 2026-11-12, and its decisions of 2026-11-06:
  - Any medium, high, or critical finding fails a pull request, on every pull request with no path filter.
  - Checkov is report-only until this ticket, which is named as the owner of its findings in `scan-iac`, `SECURITY.md`, and the register.
  - ZAP's two mediums (10038, 10020) are ignored until this ticket.
  - Accepted findings live in `engineering/docs/security/false-positives.md`, one row each, with a reason and an end date.
- Jira: SCRUM-84, under SCRUM-69. Blocks SCRUM-139 and SCRUM-143. Follow-ups: SCRUM-192 (one certificate on every hop), SCRUM-193 (SES API), SCRUM-194 (a USWDS not-found page).
- ADRs: [ADR-0015](../../../../adrs/0015-opentofu-for-infrastructure.md), [ADR-0014](../../../../adrs/0014-email-templates-and-smtp.md), [ADR-0018](../../../../adrs/0018-pyjwt-for-cognito-token-verification.md); a new ADR in Phase 1
- **Area**: iac, with a small API change (Phase 1) and CI and docs (Phase 6)

## Constitution Check

- **I, Idiomatic Python.** The API imports `cryptography` directly to generate its certificate. The package is already installed through `pyjwt[crypto]` (ADR-0018); Phase 1's ADR records the direct use, and it joins `pyproject.toml` and the README dependency table.
- **III, Test coverage.** `licensing_api/serve.py` and the new settings are covered to 100% line and branch.
- **IV, No mock code in production.** `DB_CA_FILE` is configuration, as `SMTP_STARTTLS` is: local Postgres has no TLS, so it is empty in `.env.example`. No code path swaps behavior on `ENVIRONMENT`.
- **VII, Zero trust.** This plan implements the Encryption paragraph. The certificate on the load balancer to API hop is self-signed, which the paragraph allows (it requires TLS, not a CA); the ADR records it and SCRUM-192 replaces it for production. Security-group egress and the task role's policy are narrowed to what the tasks use.
- **VIII, Maximum observability.** WAF logs, load balancer, CloudFront, and S3 access logs, and CloudTrail are new signals; rate-limit blocks alarm to the existing Slack topic.
- **IX.** Links above. Rule 4 §4.5 is cited once, in `audit.tf`, where document reads are recorded.
- **XI, Prose earns its keep.** `engineering/docs/security/` gains the ASVS mapping and an infrastructure page; `architecture.md` and the infrastructure README change with the code.
- **XII.** `.env.example`, the README, and the infrastructure README's prerequisites change in the PR that needs them.
- **XIV.** No database migration. Resource replacements are under Migration Notes.
- **XV.** Six PRs, each under 600 hand-written lines.

## Current State Analysis

Staging is not a standing environment: it is spun up and torn down by design. When it is up (as on 2026-11-12) it serves no security headers. Checkov 3.3.30 over the module with PR #173 applied reports 65 failures across 45 checks.

- **TLS.** CloudFront reaches the load balancer over HTTP (`cdn.tf:23`, `ecs.tf:242-251`); the load balancer reaches the API over HTTP (`ecs.tf:253-270`); gunicorn serves plain HTTP (`engineering/api/Dockerfile:52`). Postgres forces TLS (`main.tf:90`), but the three engines (`__main__.py:89`, `worker.py:49`, `jobs.py:101`) and yoyo (`migrations.py:16`) do not verify the server's certificate. `acm_certificate_arn` (`variables.tf:67-71`) is unused.
- **Headers.** The distribution has no response headers policy. PR #181's `.zap/rules.tsv` ignores ZAP 10038 and 10020 until this ticket.
- **WAF.** None. Sign-in does not pass through CloudFront: the browser calls Cognito directly (`engineering/client/src/lib/auth.ts`), so only a web ACL on the user pool can rate-limit it. No `/api/public/*` route exists yet (SCRUM-139).
- **Database.** `deletion_protection = false`, `skip_final_snapshot = true`, AWS-owned key, no log export, no Performance Insights (`rds.tf:28-62`). `backup_retention_period` is declared and set in tfvars but never passed to the cluster.
- **Keys.** No customer-managed key except the documents bucket's own (PR #173). Secrets, log groups, the SNS topic, and the SSM parameter use AWS-owned keys.
- **Audit.** No CloudTrail in this repository or the account's bootstrap repo. Whether a Focus organization trail covers the account is unchecked.
- **Logs.** No access logs on the load balancer, CloudFront, or S3. Log groups keep 30 days.
- **Network and IAM.** All three security groups allow all egress (`networking.tf`). The task role's telemetry policy has `Resource = "*"` on log and metric writes (`ecs.tf:86-124`).
- **US only.** CloudFront is geo-restricted to the US (`cdn.tf:209-214`). Nothing rejects a non-US region.
- **Scanning (PR #181).** Its five predecessors have merged; it is one commit, needs a rebase, and has no review yet. What it adds that this plan touches:
  - `just scan-iac`: Checkov 3.3.30 over the whole repository for three frameworks (`terraform`, `github_actions`, `dockerfile`) with `--soft-fail`, written to the job summary by the `Infrastructure (Checkov, report only)` job. It is not part of `just security`.
  - Outside OpenTofu it reports three findings, all accepted in the register with "none (report-only)" as their ignore: `CKV_GHA_7` (`deploy.yml`), `CKV_DOCKER_2` (`engineering/api/Dockerfile`), `CKV_DOCKER_3` (`engineering/mocks/cognito/Dockerfile`).
  - The register's bulk row "61 OpenTofu checks" (65 once PR #173 adds the documents bucket) and its closing paragraph, which assigns ZAP's missing-header lows to this ticket.
  - `zap.yml`: a nightly baseline of the staging URL, gated at medium by `scripts/security/findings-gate.py`, which ignores by plugin ID from `.zap/rules.tsv`. Its only automatic trigger is a nightly schedule, which assumes staging is always up.
  - Every pull request also gets CodeQL `security-extended`, pip-audit, `pnpm audit`, Trivy on the `app` image, and gitleaks over the history, so this plan's API and workflow changes must pass them.
- **Out of this ticket.** GuardDuty Malware Protection moved to SCRUM-81 (PR #173, decided 2026-11-05).

### Key Discoveries

- A VPC origin's certificate must match the origin domain or the forwarded `Host` header. Forwarding `Host` makes the wildcard certificate match with no new DNS record.
- An Application Load Balancer does not validate a target's certificate, self-signed or expired ([AWS](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html)).
- Cognito accepts a regional web ACL that inspects unauthenticated API calls such as `InitiateAuth`; the managed account-takeover rule group is not available there.
- Changing `kms_key_id` on an Aurora cluster replaces it. Changing a target group's protocol replaces it too.
- CloudFront's origin access identity cannot read an SSE-KMS bucket, and load balancer access logs accept only SSE-S3.
- The built client has five inline scripts per page and no inline styles.
- WAF logs carry request headers, so `Authorization` and `Cookie` must be redacted.

## Desired End State

- `just scan-iac` exits 0 without `--soft-fail`, and the Security workflow fails a pull request on a new finding. Every skip has a reason in the code and a row in `engineering/docs/security/false-positives.md`.
- securityheaders.com grades `https://site.dev-pacompact.aws.focusconsulting.io` A.
- CloudFront to load balancer, load balancer to API, and API to Postgres are TLS; the API verifies Postgres's certificate. No port 80 listener exists.
- Both web ACLs are attached, logging, and rate-limiting.
- Aurora is encrypted with the environment's key and keeps 7 days of backups in staging. Deletion protection and the final snapshot are on unless an environment turns them off; staging does, so it can still be torn down with `tofu destroy`.
- CloudTrail records management events and reads of the documents bucket.
- `just check` fails when any environment file or region argument names a non-US region.
- `engineering/docs/security/asvs-mapping.md` maps ASVS 5.0 to the system.

## What We're NOT Doing

- GuardDuty Malware Protection (SCRUM-81) or a GuardDuty detector.
- One CA-issued certificate on every hop (SCRUM-192).
- `prod` or any new environment's files; the code stays environment-agnostic.
- Cognito advanced security or the WAF account-takeover rule group (backlog: not at pilot).
- Cross-region replication, CloudFront origin failover, secret-rotation Lambdas, IAM database authentication, AWS Backup, or KMS on ECR and the client bucket: skipped with reasons (Phase 6).
- The ASVS level 2 walk with evidence, and the ZAP active scan (SCRUM-143).
- Moving CloudFront's origin access identity to origin access control.
- Sending email through the SES API so the SMTP IAM user and its key can go (SCRUM-193).
- Hashing inline scripts into the CSP.
- Restricting an environment's web ACLs to an IP allowlist. Raised and set aside on 2026-11-12 until there is a more specific requirement.
- Changes to the account's bootstrap repo.

## Implementation Approach

Phases 1 to 4 branch from `main` and do not depend on each other's code, but merge in order so each staging deploy changes one thing. Phase 5 touches the documents bucket from PR #173, which merged on 2026-11-12. Phase 6 needs #181.

PR #181 and Phase 2 meet in `.zap/rules.tsv` and the register. Whichever merges second carries the edit: if #181 is on `main` when Phase 2 is ready, Phase 2 makes it; if not, ask Stephen to swap the two ignores for 10055 in #181 before it merges, since from the day the headers deploy ZAP reports 10055 instead of 10038 and 10020.

Once #181 is on `main`, its Checkov job summary on each phase's pull request shows the failure count dropping; that is the reviewer's check that a phase cleared what it claims.

Run `just scan-iac` after each phase (before #181 merges: `uvx checkov==3.3.30 --directory . --framework terraform github_actions dockerfile --skip-path node_modules --skip-path .terraform --compact --quiet`); the failure count only goes down. Each phase lists the check IDs it clears.

Nothing is applied from a laptop. Each PR's CI plan is reviewed. The manual checks in each phase run against staging the next time it is up, deployed by the `Deploy` workflow; a phase's checks may be done together with the next phase's when staging is down in between. Because CI plans against whatever state exists, a plan shows everything being added when staging is down.

---

## Phase 1: TLS on every hop

### Overview

HTTPS from CloudFront to the load balancer and from the load balancer to the API; the API verifies Postgres. Security groups allow only the ports in use. Clears CKV_AWS_2, 103, 131, 150, 378, 260, 23, 382, CKV2_AWS_20.

### Changes Required

#### 1. ADR: TLS between the load balancer and the API

**File**: `engineering/adrs/0019-tls-between-load-balancer-and-api.md`
**Changes**: the API serves TLS with a certificate generated at start, because the load balancer does not validate target certificates; `cryptography` is imported directly; SCRUM-192 replaces the certificate for production. Links this plan.

#### 2. The API serves TLS

**File**: `engineering/api/licensing_api/serve.py` (new)
**Changes**: `main()` writes an EC P-256 key and a self-signed certificate (subject alternative name `localhost`, 365 days) to `<tmp>/licensing-api-tls/`, then `os.execvp`s gunicorn with `--certfile` and `--keyfile`. The directory is fixed, not from `mkdtemp`, because the container health check in `ecs.tf` has to name the certificate it trusts. `--worker-tmp-dir /dev/shm` waits for Phase 5, which is what makes the root filesystem read-only.

**File**: `engineering/api/Dockerfile`
**Changes**: the `app` stage's `CMD` becomes `["python", "-m", "licensing_api.serve"]`. The `dev` stage and `just dev` are unchanged.

**File**: `engineering/api/pyproject.toml`, `engineering/api/README.md`
**Changes**: `cryptography` as a direct dependency (no lockfile version change) and a row in the dependency table.

#### 3. The API verifies Postgres

**File**: `engineering/api/licensing_api/config.py`
**Changes**: `db_ca_file: str | None = None`; a `db_connect_args` property returning `{'ssl': ssl.create_default_context(cafile=...)}` when it is set and `{}` otherwise; `sync_db_url` appends `?sslmode=verify-full&sslrootcert=...` when it is set.

**File**: `engineering/api/licensing_api/__main__.py`, `worker.py`, `jobs.py`
**Changes**: `create_async_engine(settings.db_url, pool_pre_ping=True, connect_args=settings.db_connect_args)`.

**File**: `engineering/api/certs/rds-global-bundle.pem` (new, not hand-written)
**Changes**: AWS's RDS certificate bundle. The PR names the command: `curl -o certs/rds-global-bundle.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem`.

**File**: `engineering/api/.env.example`
**Changes**: `DB_CA_FILE=` with a comment that local Postgres has no TLS.

#### 4. Load balancer and target group

**File**: `engineering/infrastructure/iac/components/app/opentofu/ecs.tf`
**Changes**:

- `aws_lb.api_alb`: `drop_invalid_header_fields = true`, `enable_deletion_protection = var.deletion_protection`.
- `aws_lb_listener.api_listener`: port 443, `HTTPS`, `ssl_policy = "ELBSecurityPolicy-TLS13-1-2-2021-06"`, `certificate_arn = var.acm_certificate_arn`.
- `aws_lb_target_group.api_target_group`: `protocol = "HTTPS"`, health check `HTTPS`, renamed `${env}-${app}-api-https` with `create_before_destroy`, since the protocol change replaces it while the listener still points at it.
- The container health check requests `https://localhost:8000/api/health/live` and verifies it against the generated certificate.
- `DB_CA_FILE=/app/certs/rds-global-bundle.pem` in the API's environment.

**File**: `engineering/infrastructure/iac/components/app/opentofu/worker.tf`
**Changes**: `DB_CA_FILE` in `worker_environment`.

**File**: `engineering/infrastructure/iac/components/app/opentofu/variables.tf`
**Changes**: `acm_certificate_arn` becomes required (it has a default of `null` and nothing reads it today): the ARN of the certificate the load balancer's listener presents, covering `dns_name`. Each environment sets it in its tfvars (decided 2026-11-12), so which certificate, and in which region, is written down per environment and not found by a lookup. A validation rejects an ARN whose region is not `aws_region`, since a load balancer can use only a certificate from its own region; the mistake fails at plan with that message, not at apply. CloudFront's certificate is still looked up in `us-east-1` (`dns.tf`), unchanged. Add `deletion_protection` (bool, default `true`): the one switch for everything that blocks a teardown. The default is the safe value, which is also what lets Checkov resolve it; staging's `app.tfvars` sets `false`.

**File**: `engineering/infrastructure/iac/environments/staging/us-east-1/app.tfvars`
**Changes**: `acm_certificate_arn` set to staging's wildcard certificate in `us-east-1` (`aws acm list-certificates --profile dev-pacompact --region us-east-1`), and `deletion_protection = false`. The ARN holds the account ID, which this file already shows in `repo_name`.

#### 5. CloudFront origin

**File**: `engineering/infrastructure/iac/components/app/opentofu/cdn.tf`
**Changes**: `origin_protocol_policy = "https-only"`. The `/api/*` behavior replaces `forwarded_values` with the managed `CachingDisabled` cache policy and `AllViewer` origin request policy, which forwards `Host` so the wildcard certificate matches.

#### 6. Security groups

**File**: `engineering/infrastructure/iac/components/app/opentofu/networking.tf`
**Changes**: each group's allow-all egress is replaced by the ports in use, every rule gets a description, and the CloudFront ingress moves to 443. Rules stay inline.

| Group | Ingress | Egress |
|---|---|---|
| Load balancer | 443 from CloudFront's group | 8000 to the VPC's CIDR |
| Tasks | 8000 from the load balancer; all from the jumpbox, if any | 5432 to the VPC's CIDR; 443 and 587 to anywhere (AWS APIs, Cognito, ECR, SES SMTP) |
| Database | 5432 from the tasks; 5432 from the jumpbox, if any | none (`egress = []`) |

Found while implementing: standalone rule resources, as first planned, do not work on an environment that already exists. A group whose inline blocks are removed from the code keeps its rules in AWS, so the allow-all egress would have survived unseen and the new rules that duplicate old ones would have failed the apply. Inline rules are authoritative: the plan against running staging shows the old egress removed. The cost is that two egress rules name the VPC's CIDR, not the receiving group, because two groups cannot name each other inline; the receiving group's ingress rule still names the sender.

The other scanners see this phase too. Trivy scans the `app` image with its new start command and certificate bundle. CodeQL reads `serve.py`. gitleaks reads the history, so tests generate their key at run time and no key or certificate with a private key is ever committed; the RDS bundle holds public certificates only.

#### 7. Documentation

**File**: `engineering/infrastructure/iac/README.md`
**Changes**: in the `app` variable table, `acm_certificate_arn`'s row changes from "not yet used" to required, with staging's value, and `deletion_protection` gets a row saying prod leaves it on. "Adding an environment" says to issue a certificate covering `dns_name` in the environment's own region and put its ARN in `app.tfvars`; outside `us-east-1` that is a second certificate beside the one CloudFront needs.

**File**: `engineering/docs/architecture.md`
**Changes**: none. The container diagram draws CloudFront to the API as one HTTPS edge, which this phase makes true.

### Success Criteria

#### Automated Verification

- [x] `cd engineering/api && just infra && just test-coverage` passes at 100% (429 tests)
- [x] `cd engineering/api && just lint`
- [x] `cd engineering/infrastructure && just check`
- [x] The plan for `app` succeeds against running staging (run locally, 2026-11-12; CI repeats it on the PR): 4 to add, 12 to change, 4 to destroy. The target group and the three task definitions are replaced; the listener, security groups, VPC origin, and distribution change in place
- [x] `docker build --target app -t licensing-api:tls engineering/api && docker run --rm -d -p 8000:8000 licensing-api:tls`, then `curl -k https://localhost:8000/api/health/live` returns 200; plain HTTP gets no answer, and the health check command from `ecs.tf` passes inside the container
- [x] Checkov no longer reports the IDs in the overview

#### Manual Verification

- [ ] On a deployed staging, `https://site.dev-pacompact.aws.focusconsulting.io/api/health/ready` returns 200 and sign-in works
- [ ] The target group shows healthy HTTPS targets and the load balancer has no port 80 listener
- [ ] The Worker is running and the hourly heartbeat job succeeds, so both verify Postgres
- [ ] A task cannot reach an arbitrary host on port 80 (ECS Exec, or by reading the applied rules)

**Implementation Note**: after the automated checks pass, pause for confirmation of the manual checks before Phase 2.

---

## Phase 2: Response headers

### Overview

One CloudFront response headers policy on every behavior. Clears CKV2_AWS_32 and ZAP 10038 and 10020.

### Changes Required

#### 1. The policy

**File**: `engineering/infrastructure/iac/components/app/opentofu/headers.tf` (new)
**Changes**: `aws_cloudfront_response_headers_policy.security`.

| Header | Value |
|---|---|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains`, overriding the origin |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=()` |
| `Cross-Origin-Opener-Policy` | `same-origin` |
| `Cross-Origin-Resource-Policy` | `same-origin` |
| `Content-Security-Policy` | below |
| `Server` | removed |

```text
default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self';
img-src 'self' data:; font-src 'self';
connect-src 'self' https://cognito-idp.<region>.amazonaws.com <documents bucket hosts>;
form-action 'self' <documents bucket hosts>;
frame-ancestors 'none'; base-uri 'self'; object-src 'none'
```

The documents bucket has two hosts in the policy: `<bucket>.s3.amazonaws.com` and `<bucket>.s3.<region>.amazonaws.com`. Found while implementing: boto3 signs presigned links for the global host in `us-east-1` and the regional host everywhere else, so naming only the regional one, as first planned, would have blocked every upload in staging. The client posts uploads with `fetch`, which `connect-src` governs. A comment on `script-src` says why `'unsafe-inline'` is there.

Tested on 2026-11-12 by serving a build of the client behind this exact policy and loading it in headless Chromium: `/` and `/login` log no violation. Next's built-in not-found page does: it styles itself with an inline `<style>` element and `style` attributes, which `style-src 'self'` drops, so it shows its text unstyled. That page is replaced by a USWDS one in SCRUM-194; `style-src` stays `'self'`.

**File**: `engineering/infrastructure/iac/components/app/opentofu/cdn.tf`
**Changes**: `response_headers_policy_id` on the default behavior and all four ordered behaviors.

#### 2. ZAP

**File**: `.zap/rules.tsv`, `engineering/docs/security/false-positives.md` (from PR #181)
**Changes**: not in this phase's PR. PR #181 was not on `main` when it was written, so these files did not exist; by the rule under Implementation Approach, the edit goes into #181 before it merges, or into Phase 6.

- Remove the 10038 and 10020 ignores and their rows.
- Add 10055, accepted permanently: `script-src 'unsafe-inline'`, because a static export has no server to issue nonces and hashing at deploy was declined on 2026-11-12. The gate ignores by plugin, and 10055 is every CSP-quality alert, so the row says the ignore would also hide a wildcard directive and that the policy in `headers.tf` is the thing to review.
- Rewrite the register's closing paragraph: the header lows it assigns to this ticket (HSTS, Permissions-Policy, X-Content-Type-Options, cross-origin isolation, `Server`) are now sent or removed. `Cross-Origin-Embedder-Policy` is not sent, since it would block any future third-party embed for no gain here; if ZAP still reports it as a low, the paragraph says so.

### Success Criteria

#### Automated Verification

- [x] `cd engineering/infrastructure && just check`
- [x] The plan shows one policy added and the distribution updated in place (run locally against staging, 2026-11-12; CI repeats it)
- [x] Checkov no longer reports CKV2_AWS_32
- [x] A build of the client behind the policy logs no violation on `/` or `/login` in headless Chromium
- [ ] On a deployed staging, `curl -sI https://site.dev-pacompact.aws.focusconsulting.io/` shows all eight headers and no `Server`
- [ ] With staging up, a manual run of `zap.yml` passes with the two ignores removed (needs #181 on `main`)

#### Manual Verification

- [ ] securityheaders.com grades the staging site A
- [ ] With the browser console open: sign in, load each persona's pages, and upload and download a document (once SCRUM-81 is deployed). No CSP violation is logged
- [ ] The Playwright suite passes against staging

**Implementation Note**: if `style-src 'self'` logs a violation from USWDS on a deployed staging, add `'unsafe-inline'` to `style-src` only, and add its ZAP row to the register. The not-found page's violations are expected until SCRUM-194. Pause for confirmation before Phase 3.

---

## Phase 3: Web firewall

### Overview

A CloudFront web ACL and a regional one on the Cognito user pool, both logging. Clears CKV_AWS_68, CKV2_AWS_47.

### Changes Required

#### 1. Web ACLs

**File**: `engineering/infrastructure/iac/components/app/opentofu/waf.tf` (new)
**Changes**:

| Web ACL | Scope | Rules, in order |
|---|---|---|
| `cloudfront` (provider `aws.us_east_1`) | `CLOUDFRONT` | Rate: 300 per 5 minutes per IP on `/api/public/`. Rate: 2,000 per 5 minutes per IP on `/api/`. Managed: `AmazonIpReputationList`, `CommonRuleSet`, `SQLiRuleSet`, `KnownBadInputsRuleSet`; `AnonymousIpList` in count mode |
| `cognito` | `REGIONAL` | Rate: 200 per 5 minutes per IP. Managed: `AmazonIpReputationList`, `KnownBadInputsRuleSet` |

- `AnonymousIpList` was not in the first plan. Checkov's CKV2_AWS_47 requires it by name beside `KnownBadInputsRuleSet`. It matches VPNs, proxies, Tor, and hosting providers, so blocking with it would shut out a PA on a consumer VPN, a state office behind a cloud-hosted gateway, and the ZAP scan's GitHub runner. It is attached with its action overridden to count: it blocks nothing and its metric shows how much real traffic it would. Whether to block is SCRUM-143's decision, with that number. Both groups are written out as rules, not generated, because Checkov cannot see inside a dynamic block.
- Default action allow. Rate limits are `locals`, with a comment that SCRUM-139 tunes the public one against the verification page.
- `aws_wafv2_web_acl_association` to `aws_cognito_user_pool.main`; `web_acl_id` on the distribution.
- One `aws-waf-logs-*` log group per ACL (the CloudFront one in `us-east-1`), 365 days, with `redacted_fields` for the `authorization` and `cookie` headers, and a log resource policy each that lets WAF's log delivery write to it. The two log groups add CKV_AWS_158 (no KMS key) until Phase 4.
- An alarm per ACL on its rate rules' `BlockedRequests` (100 in 5 minutes) to `aws_sns_topic.api_alerts`. CloudFront's metrics exist only in `us-east-1`, so that alarm is created only when the environment's region is `us-east-1`; the comment says so.

**File**: `engineering/infrastructure/iac/components/app/opentofu/cdn.tf`
**Changes**: `web_acl_id = aws_wafv2_web_acl.cloudfront.arn`.

### Success Criteria

#### Automated Verification

- [x] `cd engineering/infrastructure && just check`
- [x] The plan adds two ACLs, one association, two log groups with their resource policies and logging configurations, and three alarms, and updates the distribution in place (run locally against staging, 2026-11-12; CI repeats it)
- [x] Checkov reports no `CKV_AWS_68`, `CKV2_AWS_47`, `CKV_AWS_192`, or `CKV2_AWS_31`

#### Manual Verification

- [ ] The full Playwright suite passes against staging: no managed rule blocks a real request, including the longest form
- [ ] 2,100 requests to `/api/health/live` from one IP inside 5 minutes end in 403s, and the alarm reaches Slack
- [ ] 250 failed sign-ins from one IP end in Cognito refusing the request
- [ ] A sampled WAF log record shows the `Authorization` header as `REDACTED`

**Implementation Note**: if a managed rule blocks a legitimate request, override that one rule to count, name it in the PR, and add it to the register. Pause for confirmation before Phase 4.

---

## Phase 4: Key and database

### Overview

One customer-managed key per environment for the database, secrets, logs, and alerts; the database protected and backed up. Clears CKV_AWS_139, 149, 158, 26, 297, 313, 324, 327, 338, 353, 118, 226, CKV2_AWS_27, CKV2_AWS_34.

### Changes Required

#### 1. The key

**File**: `engineering/infrastructure/iac/components/app/opentofu/kms.tf` (new)
**Changes**: `aws_kms_key.data` with rotation and an alias. Its policy lets the account administer it and delegate through IAM, lets CloudWatch Logs use it for this environment's log groups (conditioned on the encryption context), and lets CloudWatch alarms publish to the encrypted topic. The documents bucket keeps its own key from PR #173.

Found while implementing: staging's cluster is encrypted today with the account's AWS-managed `aws/rds` key, not unencrypted; moving to the environment's key still replaces it. The Postgres log group is created here, encrypted with 365-day retention, before the cluster exports to it: RDS would otherwise create it unencrypted and keep it forever. The three query-logging parameters are written out in the parameter group, not in the `locals` map with the rest, because Checkov cannot see inside a dynamic block.

#### 2. What uses it

**File**: `rds.tf`, `secrets.tf`, `ses.tf`, `ecs.tf`, `worker.tf`, `alerting.tf`, `scheduler.tf`, `waf.tf`
**Changes**:

- The three secrets: `kms_key_id`. The execution role gains `kms:Decrypt` on the key.
- The four ECS log groups and the Cognito web ACL's log group: `kms_key_id`, `retention_in_days = 365`. The CloudFront web ACL's log group is in `us-east-1` whatever the environment's region, and a log group can use only a key from its own region: it uses `aws_kms_key.data` when the environment is in `us-east-1`, and otherwise is skipped for CKV_AWS_158 with that reason (it holds request metadata, with session headers redacted).
- `aws_sns_topic.api_alerts`: `kms_master_key_id`.
- `aws_ssm_parameter.adot_config`: `SecureString` with `key_id`.
- `aws_scheduler_schedule.job`: `kms_key_arn`; the scheduler role gains `kms:Decrypt`.

#### 3. The database

**File**: `engineering/infrastructure/iac/components/app/opentofu/rds.tf`
**Changes**:

```hcl
kms_key_id                      = aws_kms_key.data.arn
deletion_protection             = var.deletion_protection
skip_final_snapshot             = !var.deletion_protection
final_snapshot_identifier       = var.deletion_protection ? "${local.cluster_identifier}-final" : null
backup_retention_period         = var.backup_retention_period
copy_tags_to_snapshot           = true
enabled_cloudwatch_logs_exports = ["postgresql"]
```

The instance gets `auto_minor_version_upgrade = true`, Performance Insights with the key, and enhanced monitoring at 60 seconds with its role.

**File**: `engineering/infrastructure/iac/components/app/opentofu/main.tf`
**Changes**: `log_statement` leaves the `locals` map; it, `log_min_duration_statement = 1000`, and `log_parameter_max_length = 0` are set in `rds.tf`, so a logged slow statement never carries bound values, which may be PII.

**File**: `variables.tf`, `environments/staging/us-east-1/app.tfvars`, `iac/README.md`
**Changes**: `backup_retention_period` loses its default and is validated to 7 through 35; staging sets 7. The README table follows, and says prod sets 35.

#### 4. Documentation

**File**: `engineering/docs/security/infrastructure.md` (new)
**Changes**: what the key encrypts, what the database logs and keeps, and what `deletion_protection` guards and how an environment that has it on is retired (turn it off in a reviewed PR, apply, then destroy).

### Success Criteria

#### Automated Verification

- [x] `cd engineering/infrastructure && just check`
- [x] The plan succeeds; against a running staging it replaces the cluster and its instance and changes everything else in place (run locally, 2026-11-12; CI repeats it)
- [x] Checkov no longer reports the IDs in the overview: 28 OpenTofu findings remain, from 52
- [x] `pre-commit run --files engineering/docs/security/infrastructure.md`

#### Manual Verification

- [ ] On a deployed staging: the cluster shows the key and 7-day backups, with deletion protection off; the API is ready
- [ ] `tofu destroy` of staging still completes, and a fresh `just deploy staging` after it succeeds (no name left behind blocks the second create)
- [ ] With `deletion_protection` left at its default, the plan shows protection and a final snapshot on the cluster and protection on the load balancer
- [ ] An alarm still reaches Slack through the encrypted topic (set one to `ALARM` by hand)
- [ ] Postgres logs appear in CloudWatch and a slow statement shows no bound values

**Implementation Note**: if staging is up when this deploys, its cluster is replaced and starts empty, which is acceptable by decision. Pause for confirmation before Phase 5.

---

## Phase 5: Logs, audit trail, and least privilege

### Overview

Access logs, CloudTrail, bucket lifecycles, a narrower task role, and read-only containers. Needs PR #173 merged. Clears CKV_AWS_18, 21, 86, 91, 290, 336, 355, CKV2_AWS_61.

### Changes Required

#### 1. Logs bucket

**File**: `engineering/infrastructure/iac/components/app/opentofu/logs.tf` (new)
**Changes**: `${env}-licensing-logs`: public access blocked, versioned, SSE-S3 (the load balancer cannot write to SSE-KMS), objects expire after 400 days, `force_destroy = !var.deletion_protection` so a teardown can empty it. Its policy refuses non-TLS requests and admits only the load balancer, S3 server access logging, CloudFront, and CloudTrail log delivery, each to its own prefix.

**File**: `ecs.tf`, `cdn.tf`, `documents.tf`
**Changes**: `access_logs` on the load balancer; `logging_config` on the distribution; `aws_s3_bucket_logging` for the client and documents buckets. The client bucket gets versioning and a lifecycle (noncurrent versions expire after 30 days). The documents bucket's lifecycle only aborts incomplete multipart uploads: how long a document is kept is a records decision, not this ticket's.

#### 2. CloudTrail

**File**: `engineering/infrastructure/iac/components/app/opentofu/audit.tf` (new)
**Changes**: `aws_cloudtrail.account`: multi-region, global service events, log file validation, encrypted with `aws_kms_key.data` (the key policy gains CloudTrail's statement), delivered to the logs bucket and a CloudWatch log group. A data event selector records reads and writes of the documents bucket, so access to uploaded documents is audited outside the application too (Rule 4 §4.5).

**File**: `variables.tf`, `app.tfvars`, `iac/README.md`
**Changes**: `cloudtrail_management_events` (bool, required). Before this PR, run `aws cloudtrail describe-trails --profile dev-pacompact`: staging sets `false` if a Focus organization trail already records the account's management events, `true` otherwise. The README row says how to decide.

#### 3. Least privilege

**File**: `engineering/infrastructure/iac/components/app/opentofu/ecs.tf`
**Changes**: in `ecs_task_otel`, log writes are scoped to the metrics log group and `cloudwatch:PutMetricData` is conditioned on the ADOT namespace. X-Ray's actions take no resource and keep `*`.

**File**: `ecs.tf`, `worker.tf`
**Changes**: `readonlyRootFilesystem = true` on the API, Worker, jobs, and ADOT containers, with a task-scoped volume mounted at `/tmp` for the API's certificate.

### Success Criteria

#### Automated Verification

- [ ] `cd engineering/infrastructure && just check`
- [ ] The CI plan succeeds; against a running staging it adds the bucket, trail, and log group, and replaces nothing
- [ ] Checkov no longer reports the IDs in the overview

#### Manual Verification

- [ ] On a deployed staging, the API, Worker, and a job run with read-only root filesystems, and traces still reach X-Ray
- [ ] Within an hour the logs bucket has objects under each prefix
- [ ] Downloading a document produces a `GetObject` data event in the trail
- [ ] `aws cloudtrail validate-logs` passes for the trail

**Implementation Note**: if the ADOT image cannot run read-only, drop the flag from that one container, skip `CKV_AWS_336` on its task definition with the reason, and add the register row. Pause for confirmation before Phase 6.

---

## Phase 6: US-only test, the Checkov gate, and the ASVS mapping

### Overview

The remaining findings are fixed or skipped with reasons, Checkov gates pull requests, a test fails on a non-US region, and the documents are written. Needs PRs #173 and #181 merged.

### Changes Required

#### 1. US only

**File**: `components/app/opentofu/variables.tf`, `components/ecr/opentofu/variables.tf`
**Changes**: `aws_region` validated with `startswith(var.aws_region, "us-")`, citing SOW §2.

**File**: `components/app/opentofu/tests/us_only.tftest.hcl`, `components/ecr/opentofu/tests/us_only.tftest.hcl` (new)
**Changes**: a `plan` run with `aws_region = "eu-west-1"` and `expect_failures = [var.aws_region]`, under a mock provider so it needs no credentials.

**File**: `scripts/check-us-only.sh` (new), `engineering/infrastructure/justfile`
**Changes**: the script fails when an `environments/<env>/<region>/` directory, a `region` or `aws_region` value in its files, or a literal `region = "..."` in any `.tf` file does not start with `us-`. `just check` runs it and `tofu test`, so `iac.yml` does too.

#### 2. Remaining findings

**File**: `components/ecr/opentofu/ecr.tf`, `variables.tf`, `environments/staging/us-east-1/ecr.tfvars`, `iac/README.md`
**Changes**: `image_tag_mutability = "IMMUTABLE"` and `scan_on_push = true` are set in the resource, and leave the `repositories` variable: Checkov cannot see through the variable, and no environment should choose otherwise. Clears CKV_AWS_51 and 163.

**Inline skips** (`#checkov:skip=<ID>:<reason>` on the resource), each with a row in the register:

| Check | Where | Reason |
|---|---|---|
| CKV_AWS_144 cross-region replication | all three buckets | One US region by design; a replica is a second copy of PII to protect. Versioning and Aurora backups cover loss. |
| CKV_AWS_310 origin failover | distribution | No second origin exists to fail over to. |
| CKV2_AWS_62 event notifications | all three buckets | Nothing consumes them; GuardDuty watches the documents bucket through EventBridge. |
| CKV2_AWS_57 automatic rotation | three secrets | `cognito-config` holds no credential. The database and SMTP credentials rotate by the documented `tofu apply -replace`; SCRUM-143 drills it. The SMTP secret goes away with SCRUM-193. |
| CKV_AWS_273 IAM user | SES SMTP user | SMTP needs an access key (ADR-0014); it may send only from the no-reply address. Until SCRUM-193 sends through the SES API with the task role and removes the user. |
| CKV_AWS_162 IAM database auth | cluster | The app signs in with the generated password from Secrets Manager; 15-minute IAM tokens do not fit a connection pool. |
| CKV2_AWS_8 AWS Backup | cluster | Aurora's automated backups hold the required retention. |
| CKV_AWS_136 KMS on ECR | repository | The image is built from this public repository and holds no data; AES-256 at rest. |
| CKV_AWS_145 KMS on S3 | client and logs buckets | The client bucket holds the public site and its origin access identity cannot read SSE-KMS; load balancer logs accept only SSE-S3. |
| CKV_AWS_18 access logging | logs bucket | It is the log destination. |
| CKV_AWS_259 HSTS preload | response headers policy | The check wants `preload`. It asks browser vendors to hard-code the domain as HTTPS-only, which is slow to undo and is the Commission's call for its production domain; `max-age` and `includeSubDomains` are set. Found in Phase 4. |

Any check that Checkov still reports after these, and that this plan did not foresee, is fixed if it has a fix and otherwise added to this table in the PR.

#### 3. The gate

This is the hand-back PR #181 set up: its `scan-iac` comment, `SECURITY.md`, and register all say Checkov gates once SCRUM-84 lands. Checkov has no severity levels without a platform key, so every finding fails, which is stricter than #181's medium floor and matches the acceptance criterion.

**File**: `justfile` (from PR #181)
**Changes**: `scan-iac` drops `--soft-fail`, and its comment drops "reported, never failing, until SCRUM-84". It joins the `security` recipe. Its scope stays the whole repository and all three frameworks.

**File**: `.github/workflows/security.yml` (from PR #181)
**Changes**: the `iac` job is renamed `Infrastructure (Checkov)` and fails on a finding; it still writes the summary. If the Security jobs are already required checks, a repository admin swaps the old job name for the new one in the same hour the PR merges, or every pull request waits on a check that no longer reports.

**File**: `.github/workflows/deploy.yml`, `engineering/api/Dockerfile`, `engineering/mocks/cognito/Dockerfile`
**Changes**: `CKV_GHA_7`, `CKV_DOCKER_2`, and `CKV_DOCKER_3` get inline `checkov:skip` comments carrying the reasons the register already gives. `CKV_DOCKER_2`'s reason is updated: the container health check is now HTTPS.

**File**: `.github/workflows/zap.yml` (from PR #181)
**Changes**: the `schedule` trigger goes; `workflow_call` is added beside `workflow_dispatch`. The header comment and the issue it keeps open stop saying "nightly". Staging is torn down between uses, so a schedule would fail on every night it is down.

**File**: `.github/workflows/deploy.yml`
**Changes**: a `zap` job that `needs: deploy`, runs only when the environment is `staging`, and calls `zap.yml` with `contents: read` and `issues: write`. A failed scan turns the Deploy run red after the deploy has finished; it does not roll anything back. `prod` is not scanned: `zap.yml` targets the staging URL, and scanning production is SCRUM-143's decision.

**File**: `.github/workflows/release.yml`
**Changes**: its call to `deploy.yml` grants `issues: write`, since a called workflow gets no more than its caller grants.

If Stephen makes these changes in #181 before it merges, drop them here.

**File**: `engineering/docs/security/false-positives.md`
**Changes**: the bulk "61 OpenTofu checks" row and the "Checkov is report-only" paragraph go. Every skip above gets its own row in the register's columns: "Ignored in" names the file with the inline comment, and "Until" is `permanent` except CKV2_AWS_57 on the database secret (until SCRUM-143's rotation drill decides whether to automate) and the SES SMTP user and its secret (CKV_AWS_273, CKV2_AWS_57; until SCRUM-193). The three non-OpenTofu rows change "none (report-only)" to their files.

**File**: `SECURITY.md` (from PR #181)
**Changes**: Checkov moves into the table of scans that fail a pull request (`just scan-iac`), and the "without failing ... until SCRUM-84" sentence goes. The ZAP sentence says the scan runs after each staging deploy and on a manual trigger.

#### 4. Documents

**File**: `engineering/docs/security/asvs-mapping.md` (new)
**Changes**: one section per ASVS 5.0 chapter (V1 to V17). Each requirement the infrastructure meets is listed by ID with where it is met (file, ADR, or document): V3 web frontend security (the headers), V11 cryptography, V12 secure communication, V13 configuration, V14 data protection, V16 logging. Chapters the application meets name the ADR or document that does and are marked for SCRUM-143's evidence. Level 2 throughout. The file states its source, ASVS 5.0.0, and its licence (CC BY-SA 4.0).

**File**: `engineering/docs/security/infrastructure.md`
**Changes**: the controls as built: hops and their certificates (with SCRUM-192), headers, web ACLs and their limits, what is logged where and for how long, the US-only checks.

**File**: `engineering/docs/architecture.md`
**Changes**: the container diagram gains the web ACLs, the key, CloudTrail, and the logs bucket.

**File**: `AGENTS.md`
**Changes**: the `just security` line PR #181 adds now names the infrastructure scan; the infrastructure section says `just check` runs the US-only test.

### Success Criteria

#### Automated Verification

- [ ] `just scan-iac` exits 0 with no `--soft-fail`
- [ ] `just security` exits 0, with `scan-iac` in it
- [ ] Every job in the Security workflow passes on the PR, including CodeQL over the edited workflows
- [ ] `cd engineering/infrastructure && just check` passes, including `tofu test` and `scripts/check-us-only.sh`
- [ ] Changing `aws_region` to `eu-west-1` in `environments/staging/us-east-1/app.tfvars` makes `just check` fail; so does renaming the directory to `eu-west-1`; so does adding `region = "eu-west-1"` to a resource
- [ ] `pre-commit run --files` on every changed Markdown file
- [ ] The CI plan for `ecr` shows no change, and for `app` only the region validation

#### Manual Verification

- [ ] A scratch pull request that sets `storage_encrypted = false` on the cluster fails the `Infrastructure (Checkov)` job, and one that touches no infrastructure file still runs it
- [ ] Running the `Deploy` workflow for staging runs ZAP after the deploy and the scan passes; `zap.yml` has no schedule and still runs from `workflow_dispatch`
- [ ] Required checks name the renamed job
- [ ] Every skip in the code has a register row, and every register row has a skip
- [ ] The ASVS mapping names a real file or ADR for each requirement it marks met
- [ ] securityheaders.com still grades A

---

## Testing Strategy

### API Tests

- `serve.main()` writes a certificate and key that load into an `ssl.SSLContext`, the certificate names `localhost`, and gunicorn is exec'd with them (`os.execvp` patched).
- `Settings` with `db_ca_file` set returns an SSL context in `db_connect_args` and the verify-full parameters in `sync_db_url`; unset, it returns neither.
- The existing suite runs unchanged against local Postgres with `DB_CA_FILE` empty.

### E2E Tests

No new flow. The existing Playwright suite is run against staging after Phases 1, 2, and 3, since each can break a real request.

### Infrastructure Tests

- `tofu test`: a non-US region fails validation in both components.
- `scripts/check-us-only.sh`: the three failing cases in Phase 6.
- Checkov: zero failures across all three frameworks, in the Security workflow on every pull request.
- PR #181's other scans (CodeQL, pip-audit, Trivy, gitleaks) pass on every phase's pull request.

### Manual Testing Steps

1. Whenever staging is brought up on a new phase: health, sign-in, the Worker, a job.
2. securityheaders.com after Phase 2.
3. The rate-limit drills after Phase 3.
4. The database checks after Phase 4.
5. Log and trail delivery after Phase 5.

## Security Impact Assessment

- **Data involved.** Everything the system holds: PII in Aurora and the documents bucket (States and Commission tier; SSN restricted), credentials in Secrets Manager, and request metadata in logs. This plan adds no field and exposes none; it changes how the data is protected in transit, at rest, and in audit.
- **In transit.** Browser to CloudFront and CloudFront to the load balancer use the ACM wildcard certificate, validated. Load balancer to API is encrypted with a certificate nobody validates: an attacker would need to intercept traffic inside the VPC, which AWS authenticates at the packet level. SCRUM-192 closes this for production. API to Postgres is validated against the RDS bundle.
- **At rest.** One key per environment for Aurora, its snapshots, secrets, and logs; documents keep their own key. Key policies delegate to IAM, so access is granted by the roles in the module.
- **New places data lands.**
  - WAF logs: request lines and headers. `Authorization` and `Cookie` are redacted; query strings are logged, and the API takes no PII in a query string.
  - CloudFront and load balancer access logs: IP addresses and paths.
  - Postgres logs: DDL and slow statements without bound values.
  - CloudTrail: who called which AWS API, and which documents were read.
  All are in the environment's account, in US regions, private, and expire (365 to 400 days).
- **What could go wrong.**
  - A managed WAF rule blocks a legitimate submission: the Playwright run after Phase 3 and the alarm catch it.
  - A rate limit blocks a state office behind one IP: limits are per 5 minutes and logged; tune from the logs.
  - The CSP breaks a page: the console check after Phase 2.
  - The key is scheduled for deletion: Aurora and its backups become unreadable. The default 30-day deletion window stands, and the apply role is the only one that can schedule it.
  - `deletion_protection = false` reaches an environment that holds real data: the variable defaults to `true`, so only an explicit line in that environment's tfvars, reviewed in a PR, turns it off.

## Dates and Deadlines

Not applicable. Retention periods here (backups, logs, HSTS) are infrastructure settings, not compact deadlines, and no application code computes a date.

## Migration Notes

No database migration.

Staging is spun up and torn down by design, so nothing here is sequenced around its uptime or its data. Applied to a running environment, Phase 1 replaces the listener and target group (the new image serves only TLS and the new target group only speaks it, and both arrive in the same apply) and Phase 4 replaces the Aurora cluster, which starts empty. A freshly created environment sees neither: it is built hardened.

Teardown must keep working. Everything that would block `tofu destroy` (cluster deletion protection, the final snapshot, load balancer deletion protection, non-empty versioned buckets) hangs off `deletion_protection`, which staging turns off. Phase 4's destroy-and-redeploy check is what proves it, and it also catches any new name (key alias, log group, trail) that survives a destroy and blocks the next create.

## Documentation Updates

- New: the Phase 1 ADR; `engineering/docs/security/asvs-mapping.md`; `engineering/docs/security/infrastructure.md`.
- Changed: `engineering/docs/architecture.md`; `engineering/infrastructure/iac/README.md` (variables, prerequisites); `engineering/api/README.md` (dependency table, `DB_CA_FILE`); `engineering/docs/security/false-positives.md`; `SECURITY.md`; `AGENTS.md`.
- Docstrings on `serve.main` and the new settings.
- Third-party materials: `cryptography` (Apache-2.0 or BSD-3-Clause) is already in the SBOM; the RDS certificate bundle is named in the PR for the SOW §7.5 register.

## Performance Considerations

- TLS to the API adds a handshake per load balancer connection, which keep-alive amortizes.
- WAF adds single-digit milliseconds at the edge.
- Cost per environment per month, approximately: two web ACLs with rules $25 plus $0.60 per million requests; one key $1; Performance Insights at 7 days free; enhanced monitoring and logs a few dollars at pilot volume; a second management-event trail, if needed, $2 per 100,000 events.

## References

- Original issue: SCRUM-84; follow-ups SCRUM-192 and SCRUM-193
- Related plans: `engineering/thoughts/shared/plans/iac/2026-10-28-SCRUM-83-deploy-pipeline.md`, `engineering/thoughts/shared/plans/cross-cutting/2026-11-05-SCRUM-81-documents.md`
- Open PRs this plan builds on: #173 (documents bucket and GuardDuty), #181 (security scanning; its plan is `engineering/thoughts/shared/plans/cross-cutting/2026-11-06-SCRUM-75-security-scanning.md` on that branch)
- Handoff: `engineering/thoughts/shared/handoffs/SCRUM-83/2026-10-28_17-50-01_pipeline-built-dev-undeployed-next-security-baseline.md`
- AWS: [target groups do not validate target certificates](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html); [a web ACL on a user pool](https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-waf.html); [origin certificate matching](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/http-502-bad-gateway.html)
