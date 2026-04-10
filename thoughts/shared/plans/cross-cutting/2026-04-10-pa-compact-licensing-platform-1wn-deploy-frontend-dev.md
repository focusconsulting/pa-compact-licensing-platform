# Deploy Front-End to DEV — Implementation Plan

## Overview

Add a `deploy` job to `.github/workflows/client.yml` that builds the Next.js static export, syncs it to S3, and invalidates the CloudFront cache on every merge to `main` that touches `client/**`. Deploy is gated on `lint` and `test` passing. No Docker image or ECS is needed — Next.js is configured for static export (`output: "export"`), so the build produces plain HTML/CSS/JS files that are served directly from S3 via CloudFront.

## Related

- GitHub Issue: N/A
- Beads Task: pa-compact-licensing-platform-1wn
- ADRs: N/A
- **Area**: cross-cutting

## Current State Analysis

- `.github/workflows/client.yml` has `lint` and `test` jobs triggered on push to `main` and PRs touching `client/**`. A `deploy` job has been added (see Phase 1 below — already implemented).
- `client/next.config.js` sets `output: "export"`, which means `pnpm build` emits a fully static directory at `client/out/` — no Node.js server needed at runtime.
- All AWS infrastructure (S3 bucket, CloudFront distribution, ALB, ECS) is already provisioned in `infrastructure/iac/components/app/terraform/`.
- CloudFront routes `/api/*` to the internal ALB and everything else to the S3 bucket. Both the frontend and API share the same CloudFront domain, so CORS is not needed.
- The S3 bucket is fully private; CloudFront accesses it via an OAI. The deploy job syncs files directly to S3 using the OIDC IAM role, then invalidates CloudFront so users get fresh assets immediately.
- The workflow-level `defaults: run: working-directory: client` must be overridden to `.` in the deploy job, since `aws s3 sync` and `pnpm build` output paths reference `client/out/` from the repo root.

## Desired End State

On every push to `main` that touches `client/**`:
1. `lint` and `test` jobs run (existing behaviour).
2. On success, `deploy` job:
   - Builds the Next.js static export to `client/out/`.
   - Authenticates to AWS via OIDC.
   - Syncs `client/out/` to the S3 client assets bucket (with `--delete` to remove stale files).
   - Invalidates the CloudFront distribution cache (`/*`) so users immediately receive the new assets.
3. PRs touching `client/**` run only `lint` and `test` — deploy never runs on PRs.

**Verification**: After a merge to `main`, the GitHub Actions run shows all three jobs green. The S3 bucket contains the new build artifacts. The CloudFront domain serves the updated frontend.

## What We're NOT Doing

- Not creating any AWS infrastructure (already provisioned).
- Not using ECS or Docker — static export eliminates the need for a runtime server.
- Not adding CORS to the API — CloudFront serves both frontend and API from the same domain.
- Not adding staging/prod deployment stages.
- Not configuring S3 lifecycle policies or CloudFront cache policies beyond what Terraform already defines.

## Implementation Approach

Append a `deploy` job to `.github/workflows/client.yml` that:

1. Builds the Next.js static export using pnpm.
2. Authenticates to AWS via OIDC (same `AWS_ROLE_ARN` secret used by the API deploy).
3. Syncs `client/out/` to S3 using the AWS CLI (`aws s3 sync --delete`).
4. Invalidates the CloudFront distribution so CDN edge caches are flushed immediately.

---

## Phase 1: Add Deploy Job to client.yml

### Overview

Append the `deploy` job to `.github/workflows/client.yml`. The job overrides the workflow-level `working-directory` default to `.` (repo root) and uses per-step `working-directory: client` for the pnpm install and build steps.

**Status: Implemented** — committed on branch `feature/pa-compact-licensing-platform-1wn-deploy-frontend-to-dev-aws`.

### Changes Made

#### 1. `.github/workflows/client.yml`

Added `workflow_dispatch` trigger and the following `deploy` job:

```yaml
  deploy:
    name: Deploy to DEV
    runs-on: ubuntu-latest
    needs: [lint, test]
    if: github.event_name == 'push' || github.event_name == 'workflow_dispatch'
    permissions:
      id-token: write
      contents: read
    defaults:
      run:
        working-directory: .

    steps:
      - uses: actions/checkout@v4

      - uses: pnpm/action-setup@v4
        with:
          package_json_file: client/package.json

      - uses: actions/setup-node@v4
        with:
          node-version: "24"
          cache: pnpm
          cache-dependency-path: client/pnpm-lock.yaml

      - name: Install dependencies
        working-directory: client
        run: pnpm install --frozen-lockfile

      - name: Build
        working-directory: client
        run: pnpm build

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Deploy to S3
        run: aws s3 sync client/out/ s3://${{ vars.CLIENT_S3_BUCKET }}/ --delete

      - name: Invalidate CloudFront cache
        run: |
          aws cloudfront create-invalidation \
            --distribution-id ${{ vars.CLOUDFRONT_DISTRIBUTION_ID }} \
            --paths "/*"
```

---

## Phase 2: Configure GitHub Actions Variables

### Overview

Set the two new repository variables needed by the deploy job. Values come from Terraform outputs after `terraform apply` has run for the DEV environment.

### Changes Required

#### 1. GitHub Repository Variables

Set in **GitHub → repository Settings → Secrets and variables → Actions → Variables**:

| Name | Where to find the value | Example |
|---|---|---|
| `CLIENT_S3_BUCKET` | Terraform output `client_assets_bucket` | `dev-licensing-client-assets` |
| `CLOUDFRONT_DISTRIBUTION_ID` | AWS Console → CloudFront → Distributions, or `terraform output` | `E1ABCDEF2GHIJK` |

To retrieve values from Terraform:

```bash
cd infrastructure/iac/components/app/terraform
terraform output client_assets_bucket
# Then get the distribution ID from the AWS console or:
aws cloudfront list-distributions --query "DistributionList.Items[?Origins.Items[?DomainName!=null]].Id"
```

#### 2. Existing variables already in place (shared with API deploy)

| Type | Name | Notes |
|---|---|---|
| Secret | `AWS_ROLE_ARN` | OIDC IAM role — already set for API deploy |
| Variable | `AWS_REGION` | Already set for API deploy |

#### 3. Required IAM permissions on `AWS_ROLE_ARN`

The existing role needs these additional permissions (S3 and CloudFront):

```
s3:PutObject
s3:DeleteObject
s3:ListBucket
cloudfront:CreateInvalidation
```

### Success Criteria

#### Automated Verification

- [ ] On a PR touching `client/**`: only `lint` and `test` jobs appear — no `deploy` job
- [ ] On merge to `main` touching `client/**`: all three jobs (`lint`, `test`, `deploy`) run and turn green
- [ ] S3 bucket contains the new build artifacts after the deploy job completes
- [ ] CloudFront invalidation appears in the distribution's invalidation history

#### Manual Verification

- [ ] Visiting the CloudFront domain in a browser loads the frontend
- [ ] The `/api/health/ready` endpoint is reachable from the browser via the same CloudFront domain

**Implementation Note**: After completing Phase 2 and automated verification passes, confirm manual testing before closing the beads task.

---

## Testing Strategy

### Manual Testing Steps

1. Create a trivial change in `client/` (e.g. update a string) and open a PR — confirm only `lint` and `test` appear, no `deploy`.
2. Merge the PR to `main` — watch the Actions run progress through `lint` → `test` → `deploy`.
3. Check S3: bucket contains the updated files.
4. Check CloudFront invalidation history: new invalidation for `/*` present.
5. Visit the CloudFront domain in a browser — updated content visible.
6. Open browser devtools and verify `/api/health/ready` returns `{"db": true, "cache": true}` from the same domain (no CORS errors).

## References

- Beads task: pa-compact-licensing-platform-1wn
- Existing deploy plan (API): `thoughts/shared/plans/cross-cutting/2026-04-09-pa-compact-licensing-platform-90d-deploy-api-dev.md`
- Client workflow: `.github/workflows/client.yml`
- CloudFront + S3 Terraform: `infrastructure/iac/components/app/terraform/cdn.tf`
- Terraform outputs: `infrastructure/iac/components/app/terraform/outputs.tf`
