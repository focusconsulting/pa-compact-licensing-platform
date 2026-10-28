# Environments and Deploy Pipeline Implementation Plan

## Overview

Make deploying an environment one command and one tag: OpenTofu owns every deployed resource including the running image, CI plans on pull requests and applies to `dev` on merge, and a release workflow maps tags to environments. The first apply on merge creates `dev`, which is not deployed today. Only `dev` gets environment files; `test` and `prod` get the GitHub side (protected Environments, the release mapping) so adding either later is environment files plus a bootstrap repo for its account.

## Related

- **Spec**: epic 3 in [MVP epics and tickets](../../../../../product/backlog/mvp-jira-tickets.md) and F-09 in the [MVP ticket breakdown](../../../../../product/backlog/mvp-ticket-breakdown.md); card 3 in [Engineering tickets at a glance](../../../../../product/backlog/engineering-tickets-at-a-glance.md)
- **Flows**: none directly
- **Compact rules**: none. [SOW §4.2](../../../../../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md) (sprint demos in a live environment), QASP "Deployed System" (single-command build and deploy to dev, test, and production), [SOW §2](../../../../../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md#2-scope-of-work) (United States only)
- **Decisions**: recorded on SCRUM-69 on 2026-10-28 (dev only, reuse the state bucket, code stays environment-agnostic) and in this plan's planning session: pipeline first (the first apply on merge creates dev), OpenTofu owns the image tag, pipeline roles live in the account's bootstrap repo, branch protection on `main` is in scope, the apply role is Administrator gated by the GitHub Environment
- Jira: SCRUM-83, under SCRUM-69; blocked by SCRUM-82 and SCRUM-175 (PR #138)
- ADRs: [ADR-0015](../../../../adrs/0015-opentofu-for-infrastructure.md)
- **Area**: iac, with CI workflows and one `just` recipe in the API

## Constitution Check

- **VII, Zero trust.** CI reaches AWS through GitHub's OIDC provider; no long-lived keys. The plan role is read-only. The apply role is Administrator, which applying this module needs (it creates IAM roles, security groups, Aurora, CloudFront, Cognito, Chatbot, Scheduler), and least privilege is applied to *who may assume it*: only a job running in our repository's `dev` GitHub Environment, which only a merge to protected `main` reaches, after a plan was posted on the pull request. The same shape gives `prod` required reviewers. This is recorded in the runbook; if reviewers read it as a deviation from "every role grants the minimum needed", an ADR follows this plan.
- **XII, A fresh clone runs from the README.** `just deploy <env>` is documented and is what CI runs, so a person and the pipeline use one path. CI installs the versions in `.tool-versions`.
- **XIV, Migrations are safe to deploy.** Unchanged: the API applies migrations at startup. ECS rolling deploys keep the previous task definition serving while the new one starts, and the Worker and jobs deploy from the same apply.
- **XV, Pull requests stay reviewable.** Four pull requests, each under 600 hand-written lines; workflows, `just` recipes, and HCL all count.
- **Technology Stack.** OpenTofu, ECS Fargate, CloudFront, as stated. No new dependency.

## Current State Analysis

- **Dev is not deployed.** The app state is empty (182 bytes, 2026-05-21); `just plan app dev` reports 77 to add. ECR has the April images. The prerequisites the module reads exist: network state (VPC `vpc-0a520760a300eb3eb`, three private subnets with a NAT gateway route, three public), hosted zone `dev-pacompact.aws.focusconsulting.io`, issued wildcard certificate, `dev-slack-tfvar`, the Slack workspace authorized for AWS Chatbot. SES is in the sandbox.
- **The jumpbox does not exist.** No instance tagged `dev-pacompact-jumpbox`, and the security group in `dev-jumpbox-sgid-tfvar` (`sg-06585522644ca080c`) no longer exists. `app.tfvars` has `jumpbox_enabled = true`, so the first apply would fail on the ingress rules in `networking.tf`.
- **Account bootstrap lives in** [`focusconsulting/focus-aws-infrastructure-dev-pacompact`](https://github.com/focusconsulting/focus-aws-infrastructure-dev-pacompact): `terraform/account-access` (SSO policies, pipeline roles) and `terraform/network` (VPC, NAT, hosted zone, certificate, optional jumpbox), applied by that repo's workflow with the account's `BootstrapGitops` role on merge. Its README: pipelines in other repos get their roles defined there. The network module exports `jumpbox_security_group_id` (null when no jumpbox), which the dev state does not yet contain because the current code was applied before that output existed.
- **CI deploys through `PaCompactLicensingToolPipeline`** (`pipeline-roles.tf` there), trusted by any ref of our repo, with ECR push, ECS deploy, S3 and CloudFront, and Aurora Data API policies. It cannot read the state bucket or create infrastructure.
- **Our workflows**: `api.yml` and `client.yml` each have a `Deploy to DEV` job on push to `main` that renders ECS task definitions or syncs S3, reading repository-level variables (`ECS_CLUSTER`, `ECS_SERVICE`, `CLIENT_S3_BUCKET`, `CLOUDFRONT_DISTRIBUTION_ID`, and others) that name resources that do not exist, and the `AWS_ROLE_ARN` repository secret. `iac.yml` (PR #138) runs `just check` only. There are no GitHub Environments. `main` has no branch protection.
- **The module**: `ecs.tf` and `worker.tf` pin `image = "${var.repo_name}:latest"`, and both services `ignore_changes = [task_definition]` so CI could deploy independently. `scheduler.tf` runs the jobs task's latest revision. ECR is `MUTABLE` with no lifecycle policy. Outputs include the client bucket, distribution ID, Cognito pool and client IDs, and the Worker and jobs families.
- **Local tooling** (PR #138): `engineering/infrastructure/justfile` with `init`, `plan`, `apply`, `fmt`, `validate`, `check`; the API justfile has `build` (tags `pa-compact-api:latest` and the commit) but no push.

## Desired End State

- `just deploy dev` from `engineering/infrastructure`, with dev credentials: builds and pushes the API image tagged with the commit, applies `ecr` then `app` with that tag, builds the client against the Cognito outputs, syncs it to S3, and invalidates CloudFront. Idempotent: a second run with no changes pushes nothing and applies nothing.
- A pull request that touches `engineering/infrastructure/` gets one comment per component holding the plan, kept current on each push.
- A merge to `main` deploys `dev` through the `dev` GitHub Environment, serialized per environment.
- A `v*-rc` tag deploys `test` and a `v*` tag deploys `prod`, each through its Environment with required reviewers; until those environments have files, the job fails at `just init` with "backend config not found", not silently.
- `main` requires the lint, test, e2e, accessibility, IaC check, and IaC plan checks and one approving review.
- The infrastructure README's runbook takes a fresh AWS account to a running environment: bootstrap repo, pipeline roles, environment files, GitHub Environment, first deploy.

### Key Discoveries:
- `engineering/infrastructure/iac/components/app/opentofu/ecs.tf:155` and `worker.tf:51,77`: the three `:latest` references; `ecs.tf:297-306` and `worker.tf:116-119`: the `ignore_changes` to remove.
- `engineering/infrastructure/iac/components/app/opentofu/networking.tf:1-10`: the jumpbox secret read to replace with the network remote state output.
- `engineering/infrastructure/iac/components/app/opentofu/outputs.tf`: everything the client deploy needs is already an output.
- `focus-aws-infrastructure-dev-pacompact/terraform/account-access/pipeline-roles.tf`: the pattern for a role trusted by our repo's OIDC subject.
- GitHub user IDs for Environment reviewers: `mkalish` 1225895, `jalbinson` 1209453.

## What We're NOT Doing

- Creating `test` or `prod` AWS accounts, bootstrap repos, or environment files. The release workflow and their GitHub Environments are built; they deploy once those exist.
- Checkov, WAF, HTTPS to the ALB, backups, KMS, CloudTrail, GuardDuty, the ASVS mapping, or the US-only policy test (SCRUM-84).
- Retiring `PaCompactLicensingToolPipeline` and its policies. It stays until dev has deployed through the new path; a follow-up ticket removes it.
- Tightening the bootstrap repo's temporary `*:*` developer policy. Noted on that repo's PR.
- Recreating the jumpbox. If one is wanted, the bootstrap repo sets `create_jumpbox = true`, and our module picks it up from the remote state with no change.
- Rollback automation. ECS keeps the previous revision serving until the new one is healthy; a bad release is reverted by deploying the previous tag.
- Renaming the duplicate `lint` and `test` job names across `api.yml` and `client.yml`. Branch protection names them as they are; see Phase 4.

## Implementation Approach

Four pull requests in order. Phase 1 is in the bootstrap repo and must merge first, since every later phase's CI assumes the roles. Phases 2 to 4 stack on `feature/SCRUM-82-environment-contract-opentofu` (PR #138) in this repo, each its own PR, retargeted to `main` as their bases merge.

The first deployment of dev is Phase 3's first merge to `main`. Before that merge, Phase 2 is verified with `just plan app dev` from a laptop (77 to add, as today, with the new image tag), never `just apply`, so the pipeline creates dev exactly as it will maintain it.

The image tag is the full commit SHA, immutable in ECR. A pull request plan passes its head SHA, so a plan on a PR that changes nothing else still shows the three task definitions updating in place; that is accurate, since merging deploys that commit.

---

## Phase 1: Pipeline roles in the account's bootstrap repo

### Overview

Two roles in `focusconsulting/focus-aws-infrastructure-dev-pacompact`, applied by that repo's workflow on merge. No change to this repo.

### Changes Required:

#### 1. Roles for our repository's infrastructure pipeline
**File**: `terraform/account-access/pa-compact-infra-roles.tf` (new, in the bootstrap repo)
**Changes**: a plan role for pull requests and an apply role for the `dev` Environment. The subjects follow GitHub's OIDC claims: `pull_request` for PR runs, `environment:<name>` for jobs that declare an Environment.

```hcl
# Roles for focusconsulting/pa-compact-licensing-platform's infrastructure pipeline
# (engineering/infrastructure in that repo). Plan on pull requests, apply on merge
# through the "dev" GitHub Environment. See that repo's engineering/infrastructure/iac/README.md.

locals {
  pa_compact_repo         = "repo:focusconsulting/pa-compact-licensing-platform"
  pa_compact_state_bucket = "arn:aws:s3:::focus-dev-pacompact-terraform-state"
  github_oidc_sub         = "token.actions.githubusercontent.com:sub"
  github_oidc_aud         = "token.actions.githubusercontent.com:aud"
}

data "aws_iam_policy_document" "pa_compact_infra_plan_assume_role" {
  statement {
    sid     = "PullRequestsPlan"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github_actions.arn]
    }
    condition {
      test     = "StringEquals"
      variable = local.github_oidc_aud
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = local.github_oidc_sub
      values   = ["${local.pa_compact_repo}:pull_request"]
    }
  }
}

resource "aws_iam_role" "pa_compact_infra_plan" {
  name               = "PaCompactLicensingToolInfraPlan"
  description        = "tofu plan on pull requests in focusconsulting/pa-compact-licensing-platform"
  assume_role_policy = data.aws_iam_policy_document.pa_compact_infra_plan_assume_role.json
}

resource "aws_iam_role_policy_attachment" "pa_compact_infra_plan_read_only" {
  role       = aws_iam_role.pa_compact_infra_plan.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

# ReadOnlyAccess covers neither state locking nor Secrets Manager values; the
# module reads <env>-slack-tfvar as a data source during plan.
data "aws_iam_policy_document" "pa_compact_infra_plan_extra" {
  statement {
    sid       = "StateRead"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:ListBucket"]
    resources = [local.pa_compact_state_bucket, "${local.pa_compact_state_bucket}/*"]
  }
  statement {
    sid       = "StateLock"
    effect    = "Allow"
    actions   = ["s3:PutObject", "s3:DeleteObject"]
    resources = ["${local.pa_compact_state_bucket}/pacompact/*.tflock"]
  }
  statement {
    sid       = "TfvarValues"
    effect    = "Allow"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = ["arn:aws:secretsmanager:*:*:secret:*-tfvar-*"]
  }
}

resource "aws_iam_policy" "pa_compact_infra_plan_extra" {
  name   = "PaCompactLicensingToolInfraPlanExtra"
  policy = data.aws_iam_policy_document.pa_compact_infra_plan_extra.json
}

resource "aws_iam_role_policy_attachment" "pa_compact_infra_plan_extra" {
  role       = aws_iam_role.pa_compact_infra_plan.name
  policy_arn = aws_iam_policy.pa_compact_infra_plan_extra.arn
}

# Applying the app component creates IAM roles, security groups, Aurora, CloudFront,
# Cognito, Chatbot, and Scheduler resources, so the role is Administrator; what is
# controlled is who may assume it: only a job in the repo's "dev" Environment, which
# only a merge to protected main reaches.
data "aws_iam_policy_document" "pa_compact_infra_apply_assume_role" {
  statement {
    sid     = "DevEnvironmentApply"
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github_actions.arn]
    }
    condition {
      test     = "StringEquals"
      variable = local.github_oidc_aud
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = local.github_oidc_sub
      values   = ["${local.pa_compact_repo}:environment:dev"]
    }
  }
}

resource "aws_iam_role" "pa_compact_infra_apply" {
  name               = "PaCompactLicensingToolInfraApply"
  description        = "just deploy dev from focusconsulting/pa-compact-licensing-platform's dev Environment"
  assume_role_policy = data.aws_iam_policy_document.pa_compact_infra_apply_assume_role.json
}

resource "aws_iam_role_policy_attachment" "pa_compact_infra_apply_admin" {
  role       = aws_iam_role.pa_compact_infra_apply.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

output "pa_compact_infra_plan_role_arn" {
  value = aws_iam_role.pa_compact_infra_plan.arn
}

output "pa_compact_infra_apply_role_arn" {
  value = aws_iam_role.pa_compact_infra_apply.arn
}
```

#### 2. Note on that PR
The `*:*` statement in `user-roles.tf` is marked temporary until a pipeline exists; this PR is the pipeline's roles, so the note says the statement can be reviewed once dev deploys through them.

### Success Criteria:

#### Automated Verification:
- [x] That repo's `account-access` job validates on the PR and applies on merge.

#### Manual Verification:
- [x] `aws iam get-role --role-name PaCompactLicensingToolInfraPlan` and `...InfraApply` return the roles with the trust policies above, in account 126942145463.
- [x] A code owner of the bootstrap repo has approved.

**Implementation Note**: Phase 2 can be written in parallel, but Phase 3's CI cannot pass until this merges.

---

## Phase 2: One deployer

### Overview

OpenTofu owns the running image. `just deploy <env>` does everything a deploy needs, and is what CI runs in Phase 3.

### Changes Required:

#### 1. Image tag variable
**File**: `engineering/infrastructure/iac/components/app/opentofu/variables.tf`
**Changes**:

```hcl
variable "image_tag" {
  description = "The API image tag to run, in the repository repo_name names: the git commit SHA that built it"
  type        = string
  validation {
    condition     = can(regex("^[0-9a-f]{40}$", var.image_tag))
    error_message = "image_tag is the 40-character commit SHA the image was built from."
  }
}
```

**Files**: `engineering/infrastructure/iac/components/app/opentofu/ecs.tf`, `worker.tf`
**Changes**: the three `image` values become `"${var.repo_name}:${var.image_tag}"`. Remove `task_definition` from both services' `ignore_changes` (keep `desired_count` on the API service), and delete the comment that explained the CI handoff. Scheduler is unchanged: it runs the latest jobs revision, which the apply registers.

#### 2. Immutable ECR with a lifecycle policy
**File**: `engineering/infrastructure/iac/components/ecr/opentofu/ecr.tf`
**Changes**: a lifecycle policy per repository; expire untagged images after 7 days and keep the newest 30 tagged.

```hcl
resource "aws_ecr_lifecycle_policy" "repos" {
  for_each   = aws_ecr_repository.repos
  repository = each.value.name
  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Untagged layers from superseded builds"
        selection    = { tagStatus = "untagged", countType = "sinceImagePushed", countUnit = "days", countNumber = 7 }
        action       = { type = "expire" }
      },
      {
        rulePriority = 2
        description  = "Keep the newest 30 releases"
        selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 30 }
        action       = { type = "expire" }
      },
    ]
  })
}
```

**File**: `engineering/infrastructure/iac/environments/dev/us-east-1/ecr.tfvars`
**Changes**: `image_tag_mutability = "IMMUTABLE"`. Existing tags are unaffected; a push that reuses a tag is rejected, which `just deploy` checks for first.

#### 3. Jumpbox from the network state
**File**: `engineering/infrastructure/iac/components/app/opentofu/networking.tf`
**Changes**: delete the `aws_secretsmanager_secret_version.jumpbox` data source and the `jumpbox_sg_ids` local that reads it; replace with the network output, which is null or absent when the bootstrap repo creates no jumpbox.

```hcl
locals {
  # The bootstrap repo's network module exports the jumpbox's security group when
  # create_jumpbox is on; older states have no such output.
  jumpbox_sg_ids = compact([try(data.terraform_remote_state.network.outputs.jumpbox_security_group_id, null)])
}
```

**File**: `engineering/infrastructure/iac/components/app/opentofu/variables.tf`
**Changes**: remove `jumpbox_enabled`.

**File**: `engineering/infrastructure/iac/environments/dev/us-east-1/app.tfvars`
**Changes**: remove `jumpbox_enabled`. `image_tag` is never set here; CI and `just deploy` pass it.

**File**: `engineering/infrastructure/iac/README.md`
**Changes**: the variables table drops `jumpbox_enabled`, gains `image_tag` ("set by `just deploy`, never in tfvars"); "Adding an environment" drops the jumpbox entry and says the jumpbox is the bootstrap repo's `create_jumpbox`.

#### 4. Push recipe in the API
**File**: `engineering/api/justfile`
**Changes**: `build` targets `linux/amd64` (Fargate's default platform) and tags the full SHA; a `push` recipe logs in to ECR, skips when the tag already exists (immutable repository), and pushes.

```just
image_tag := `git rev-parse HEAD`

# Build the production image for Fargate (linux/amd64), tagged with the commit
build:
    docker build --platform linux/amd64 --target app \
        --tag {{ app_name }}:latest --tag {{ app_name }}:{{ image_tag }} .

# Push the built image to an ECR repository URL; a tag already there is left alone (tags are immutable)
push $repo: build
    aws ecr get-login-password | docker login --username AWS --password-stdin "${repo%%/*}"
    if aws ecr describe-images --repository-name "${repo##*/}" --image-ids imageTag={{ image_tag }} >/dev/null 2>&1; then \
        echo "{{ image_tag }} is already in $repo"; \
    else \
        docker tag {{ app_name }}:{{ image_tag }} "$repo:{{ image_tag }}" && docker push "$repo:{{ image_tag }}"; \
    fi
```

#### 5. `just deploy <env>`
**File**: `engineering/infrastructure/justfile`
**Changes**: `plan` and `apply` gain `*args` passed through to `tofu`, and the region becomes a justfile variable (`AWS_REGION`, default `us-east-1`) because a positional default before variadic arguments swallows the first extra argument; `validate` uses its own `TF_DATA_DIR` so it works after a `plan` on the same checkout; `deploy` chains the steps, reading everything it needs from component outputs rather than GitHub variables. `repo_name` stays a variable so the two components remain separately applicable; `deploy` passes it from the `ecr` output.

```just
# Deploy an environment: push the API image for this commit, apply ecr then app, publish the client
deploy env region="us-east-1":
    #!/usr/bin/env bash
    set -euo pipefail
    sha=$(git rev-parse HEAD)
    just apply ecr {{ env }} {{ region }} -auto-approve
    repo=$(cd {{ iac }}/components/ecr/opentofu && tofu output -json ecr_repositories | jq -r 'to_entries[0].value.repository_url')
    (cd {{ justfile_directory() }}/../api && just push "$repo")
    just apply app {{ env }} {{ region }} -auto-approve -var image_tag="$sha" -var repo_name="$repo"
    out() { (cd {{ iac }}/components/app/opentofu && tofu output -raw "$1"); }
    (cd {{ justfile_directory() }}/../client \
        && NEXT_PUBLIC_API_BASE_URL="" \
           NEXT_PUBLIC_COGNITO_REGION={{ region }} \
           NEXT_PUBLIC_COGNITO_USER_POOL_ID="$(out cognito_user_pool_id)" \
           NEXT_PUBLIC_COGNITO_CLIENT_ID="$(out cognito_client_id)" \
           pnpm install --frozen-lockfile && pnpm build)
    aws s3 sync {{ justfile_directory() }}/../client/out/ "s3://$(out client_assets_bucket)/" --delete
    aws cloudfront create-invalidation --distribution-id "$(out cloudfront_distribution_id)" --paths "/*" >/dev/null
```

`NEXT_PUBLIC_API_BASE_URL` is empty because CloudFront serves the API under the same host at `/api`; confirm against `engineering/client/.env.example` and the client's base-URL handling when implementing, and use `https://<dns_name>` if the client needs an absolute origin.

#### 6. Client build settings
**File**: `engineering/client/.env.example`
**Changes**: the comment on the Cognito settings names the outputs `just deploy` reads them from, replacing "take the pool and client IDs from Terraform outputs".

### Success Criteria:

#### Automated Verification:
- [x] `cd engineering/infrastructure && just check` passes.
- [x] `cd engineering/api && just lint` passes; the justfile change touches no Python, and the SCRUM-82 branch's test run covers the suite.
- [x] `git grep -n ':latest' engineering/infrastructure` returns nothing.
- [x] `tofu plan` with `-var image_tag=abc` fails on the validation message (scratch copy with a local backend, as in the SCRUM-82 plan).

#### Manual Verification:
- [x] With dev credentials: `just plan app dev -var image_tag=$(git rev-parse HEAD)` still reports 77 to add and 0 to change, and the plan's task definitions reference the SHA tag. Not applied.
- [x] `cd engineering/api && just build` produces a `linux/amd64` image (`docker image inspect pa-compact-api:latest --format '{{.Architecture}}'` prints `amd64`).

**Implementation Note**: pause here. Phase 3's first merge is the first deployment of dev; the user confirms before it is merged.

---

## Phase 3: CI plans, applies, and releases

### Overview

Plan on pull requests, deploy `dev` on merge, deploy `test` and `prod` from tags, all through GitHub Environments and the Phase 1 roles. The old deploy jobs go.

### Changes Required:

#### 1. GitHub Environments and variables (settings, done with `gh`)
- Environments `dev`, `test`, `prod`. `test` and `prod` have required reviewers (`mkalish`, `jalbinson`) and are restricted to tags; `dev` has no protection.
- `dev` Environment variables: `AWS_APPLY_ROLE_ARN` (from Phase 1's output), `AWS_REGION=us-east-1`.
- Repository variable `AWS_PLAN_ROLE_ARN`.
- The repository-level `ECS_*`, `ECR_REPOSITORY`, `CLIENT_S3_BUCKET`, `CLOUDFRONT_DISTRIBUTION_ID` variables and the old `AWS_ROLE_ARN` repository credential are removed in Phase 4, after the first deploy proves nothing reads them.

```bash
gh api -X PUT repos/focusconsulting/pa-compact-licensing-platform/environments/dev
gh api -X PUT repos/focusconsulting/pa-compact-licensing-platform/environments/prod \
  --input - <<'EOF'
{"reviewers":[{"type":"User","id":1225895},{"type":"User","id":1209453}],
 "deployment_branch_policy":{"protected_branches":false,"custom_branch_policies":true}}
EOF
gh api -X POST repos/focusconsulting/pa-compact-licensing-platform/environments/prod/deployment-branch-policies \
  -f name='v*' -f type=tag
# same for test, with pattern v*-rc*
gh variable set AWS_PLAN_ROLE_ARN --body arn:aws:iam::126942145463:role/PaCompactLicensingToolInfraPlan
gh variable set AWS_APPLY_ROLE_ARN --env dev --body arn:aws:iam::126942145463:role/PaCompactLicensingToolInfraApply
gh variable set AWS_REGION --env dev --body us-east-1
```

#### 2. Plan on pull requests
**File**: `.github/workflows/iac.yml`
**Changes**: a `plan` job after `check`, pull requests only, matrix over `ecr` and `app`, assuming the plan role. The plan output is posted as one comment per component, updated in place on later pushes, found by a marker line. A plan over GitHub's comment limit is truncated with a link to the job.

```yaml
  plan:
    if: github.event_name == 'pull_request'
    needs: check
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
      pull-requests: write
    strategy:
      matrix:
        component: [ecr, app]
    env:
      TF_IN_AUTOMATION: "true"
    steps:
      - uses: actions/checkout@v7
      # tool setup as in the check job
      - uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ vars.AWS_PLAN_ROLE_ARN }}
          aws-region: us-east-1
      - name: Plan
        working-directory: engineering/infrastructure
        run: |
          extra=""
          [ "${{ matrix.component }}" = app ] && extra="-var image_tag=${{ github.event.pull_request.head.sha }}"
          just plan ${{ matrix.component }} dev -no-color $extra 2>&1 | tee plan.txt
      - name: Comment
        env:
          GH_TOKEN: ${{ github.token }}
        run: scripts/comment-plan.sh ${{ github.event.pull_request.number }} ${{ matrix.component }} engineering/infrastructure/plan.txt
```

`scripts/comment-plan.sh` (repo root `scripts/`, new, about 25 lines): finds a comment on the PR whose body starts with `<!-- tofu-plan:<component> -->`, and creates or updates it with the plan in a collapsed `<details>` block headed by the plan's summary line.

#### 3. Deploy workflow
**File**: `.github/workflows/deploy.yml` (new)
**Changes**: one job, reusable and runnable by hand for `dev`. Decided 2026-10-28: no `push` to `main` trigger yet; dev deploys when someone runs the workflow, and deploy-on-merge is turned on later by adding the trigger. The Environment gates the role; `concurrency` serializes deploys per environment.

```yaml
name: Deploy

on:
  push:
    branches: [main]
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
  workflow_dispatch:
    inputs:
      environment:
        required: true
        type: choice
        options: [dev]

concurrency:
  group: deploy-${{ inputs.environment || 'dev' }}
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment || 'dev' }}
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v7
      # tool setup: uv, python, pnpm, node, just, opentofu, from .tool-versions and the client's packageManager
      - uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ vars.AWS_APPLY_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}
      - name: Deploy
        working-directory: engineering/infrastructure
        run: just deploy ${{ inputs.environment || 'dev' }}
```

A push to `main` deploys every merge, whether or not it touched the API or client: `just deploy` pushes nothing when the image exists, applies nothing when the plan is empty, and the client build and sync are a few minutes. That is simpler than path filters that miss a dependency, and it is what makes `dev` the live demo environment.

#### 4. Release workflow
**File**: `.github/workflows/release.yml` (new)
**Changes**: tags `v*` map to environments and call `deploy.yml`.

```yaml
name: Release

on:
  push:
    tags: ["v*"]

jobs:
  target:
    runs-on: ubuntu-latest
    outputs:
      environment: ${{ steps.map.outputs.environment }}
    steps:
      - id: map
        run: |
          case "${GITHUB_REF_NAME}" in
            v*-rc*) echo "environment=test" >> "$GITHUB_OUTPUT" ;;
            v*)     echo "environment=prod" >> "$GITHUB_OUTPUT" ;;
          esac
  deploy:
    needs: target
    uses: ./.github/workflows/deploy.yml
    with:
      environment: ${{ needs.target.outputs.environment }}
```

Until `test` and `prod` have environment files and Environment variables, the job stops at the Environment's required review and, if approved, at `just init` with the missing backend file. A tag is a deliberate act; that failure is visible and harmless.

#### 5. Remove the old deploy jobs
**Files**: `.github/workflows/api.yml`, `.github/workflows/client.yml`
**Changes**: delete the `changes` and `deploy` jobs and the `workflow_dispatch` trigger if nothing else uses it. The lint, test, and accessibility jobs are unchanged.

#### 6. Docs
**Files**: `engineering/infrastructure/iac/README.md`, `AGENTS.md`
**Changes**: a "Deploying" section: what a merge does, what a tag does, where to watch, how to deploy by hand; `just deploy <env>` in AGENTS.md's infrastructure list.

### Success Criteria:

#### Automated Verification:
- [x] On the PR: `check` passes and two plan comments appear, one per component (PR #140, first run: `ecr` 1 to add, 1 to change; `app` 77 to add); updating on a second push is checked on the next push.
- [x] `cd engineering/infrastructure && just check` passes; YAML parses; `pre-commit run --files` on changed Markdown passes.

#### Manual Verification:
- [ ] **The first merge to `main` deploys dev**: the `Deploy` run is green, `https://site.dev-pacompact.aws.focusconsulting.io/api/health/ready` returns ready, the sign-in page renders, and the Worker service has one running task. Watch the run; if it fails partway, the next run resumes from state.
- [ ] A second, empty merge applies nothing and pushes nothing.
- [ ] Pushing a tag `v0.0.1-rc1` on a throwaway commit stops at the `test` Environment's review; rejecting it ends the run. Delete the tag afterwards.

**Implementation Note**: the user confirms before the first merge.

---

## Phase 4: Protection, cleanup, and the runbook

### Overview

Lock `main`, remove what the old path used, and write the runbook the epic's acceptance criteria name.

### Changes Required:

#### 1. Branch protection (settings, done with `gh`)
Required checks are status-check names: `pre-commit`, `lint`, `test`, `smoke`, `Accessibility (pa11y-ci, WCAG 2 AA)`, `check`, `plan (ecr)`, `plan (app)`. `lint` and `test` are job names in both `api.yml` and `client.yml`; GitHub matches by name, so a PR that triggers only one workflow satisfies them with that workflow's jobs. Renaming them is a follow-up if that proves too loose. One approving review; dismiss stale reviews; no force pushes; admins included.

```bash
gh api -X PUT repos/focusconsulting/pa-compact-licensing-platform/branches/main/protection --input - <<'EOF'
{"required_status_checks":{"strict":true,"contexts":["pre-commit","lint","test","smoke","Accessibility (pa11y-ci, WCAG 2 AA)","check","plan (ecr)","plan (app)"]},
 "enforce_admins":true,
 "required_pull_request_reviews":{"required_approving_review_count":1,"dismiss_stale_reviews":true},
 "restrictions":null,"allow_force_pushes":false,"allow_deletions":false}
EOF
```

#### 2. Remove the old path's settings
`gh variable delete` for `ECS_CLUSTER`, `ECS_SERVICE`, `ECS_TASK_DEFINITION`, `ECS_CONTAINER_NAME`, `ECS_WORKER_TASK_DEFINITION`, `ECS_JOBS_TASK_DEFINITION`, `ECS_WORKER_SERVICE`, `ECR_REPOSITORY`, `CLIENT_S3_BUCKET`, `CLOUDFRONT_DISTRIBUTION_ID`; delete the repository's old `AWS_ROLE_ARN` credential. Delete `dev-jumpbox-sgid-tfvar` in Secrets Manager (nothing reads it after Phase 2). A follow-up ticket retires `PaCompactLicensingToolPipeline`.

#### 3. The runbook
**File**: `engineering/infrastructure/iac/README.md`
**Changes**: "Standing up an environment", from nothing to a deploy:
1. An AWS account from Focus's vending, with its bootstrap repo `focus-aws-infrastructure-<env>-pacompact` from the dev one: `create_dns_domain`, NAT, `create_jumpbox` as wanted; the NS delegation step from its README.
2. Pipeline roles in that repo's `account-access` for this repository's `<env>` Environment (Phase 1's file, with the environment name changed).
3. `<env>-slack-tfvar` in Secrets Manager; the Slack workspace authorized for AWS Chatbot in the account.
4. Environment files under `environments/<env>/<region>/` per the contract table; ECR first.
5. The GitHub Environment with its variables and, for `test` and `prod`, reviewers and the tag rule.
6. `just deploy <env>` from a laptop once, or a tag.
7. After: SES production access, and a request to tighten the bootstrap repo's developer policy.

**File**: `AGENTS.md`
**Changes**: the Git section's "`main` is protected" line becomes true; add that a merge deploys `dev`.

### Success Criteria:

#### Automated Verification:
- [ ] `gh api repos/.../branches/main/protection` shows the checks and review count above.
- [ ] `gh variable list` shows none of the removed names.
- [ ] `pre-commit run --files engineering/infrastructure/iac/README.md AGENTS.md` passes.

#### Manual Verification:
- [ ] A PR without an approving review cannot merge; one with a failing `plan (app)` cannot merge.
- [ ] A new engineer reads the runbook and lists, without asking, every step from account to first deploy (the SCRUM-69 acceptance criterion).

---

## Testing Strategy

### API Tests:
- None added; the API's code is unchanged.

### E2E Tests:
- None; no user flow changes. The existing e2e workflow stays a required check.

### Manual Testing Steps:
1. Phase 2: `just plan app dev` with an image tag, from a laptop: 77 to add, 0 to change.
2. Phase 3: first merge deploys dev; health, sign-in page, Worker task.
3. Phase 3: an empty merge is a no-op deploy; a `-rc` tag stops at review.
4. Phase 4: merge blocked without review; blocked on a failing plan.

## Security Impact Assessment

No PII flows change. What changes is who can change the infrastructure that holds it:

- **Before**: a role trusted by *any* ref of the repository could deploy ECS and S3; a developer's SSO policy is `*:*`.
- **After**: pull requests get a read-only role; Administrator is reachable only from the `dev` Environment on `main`, which needs a review and passing checks, and the plan the reviewer approved is in the PR. `prod` adds required reviewers on the Environment itself.
- **Risk**: the plan role can read every Secrets Manager value whose name ends in `-tfvar`; nothing else there. The plan comment on a public repository's PR shows resource names and configuration, never secret values; OpenTofu marks sensitive values in plans, and the SES SMTP credential and the database password are computed resources, not plan inputs. The implementation checks one real plan comment for leaked values before Phase 3 merges.
- **Risk**: a merge deploys immediately. Branch protection and the plan comment are the review; `dev` holds no real data.

## Dates and Deadlines

Not applicable.

## Migration Notes

Not applicable; no database migration. Deploy ordering is unchanged: the API task starts first and applies migrations before the Worker's new revision is scheduled, because ECS rolls the API service and the Worker service independently and the Worker tolerates the old schema for the seconds in between (SCRUM-80's design).

## Documentation Updates

- `engineering/infrastructure/iac/README.md`: deploying, the runbook, the variables table.
- `AGENTS.md`: `just deploy`, protected `main`, merges deploy dev.
- `engineering/api/justfile` and `engineering/infrastructure/justfile` recipe comments.
- `engineering/docs/architecture.md`: unchanged; no component changes.
- No dependency or license change.

## Performance Considerations

A deploy takes the image build (a few minutes), the apply (seconds when nothing changes, about 20 minutes the first time for Aurora and CloudFront), and the client build and sync. Serialized per environment by `concurrency`.

## References

- Jira: SCRUM-83, SCRUM-69
- Bootstrap repo: <https://github.com/focusconsulting/focus-aws-infrastructure-dev-pacompact>
- Previous plans: `engineering/thoughts/shared/plans/cross-cutting/2026-04-09-deploy-api-dev.md`, `2026-04-10-deploy-frontend-dev.md`; `engineering/thoughts/shared/plans/iac/2026-10-28-SCRUM-82-environment-contract-opentofu.md`
- GitHub OIDC subject claims: <https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect#example-subject-claims>
