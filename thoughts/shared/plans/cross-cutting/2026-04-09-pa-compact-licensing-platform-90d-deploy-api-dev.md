# Deploy API to DEV — Implementation Plan

## Overview

Add a `deploy` job to `.github/workflows/api.yml` that builds the production Docker image, pushes it to ECR, and deploys to ECS Fargate on every merge to `main` that touches `api/**`. Deploy is gated on `lint` and `test` passing. No Dockerfile changes are needed — ECS natively injects Secrets Manager values as environment variables via the task definition.

## Related

- GitHub Issue: N/A
- Beads Task: pa-compact-licensing-platform-90d
- ADRs: ADR-0002 (`docs/architecture_decision_records/0002-db-config-decomposition.md`) — explains why no AWS SDK is needed in the container
- **Area**: cross-cutting

## Current State Analysis

- `.github/workflows/api.yml` has `lint` and `test` jobs triggered on push to `main` and PRs touching `api/**`. No deploy job exists.
- `api/Dockerfile` has three stages: `build`, `dev`, `app` (prod). The `app` stage runs gunicorn on port 8000 as non-root user 999.
- All AWS infrastructure (ECS cluster, Fargate service, task definition, ECR repo, RDS, ElastiCache, Secrets Manager) is already provisioned.
- The app reads 9 env vars at startup (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `REDIS_URL`, `API_PORT`, `LOG_LEVEL`, `ENVIRONMENT`). ECS injects them natively from Secrets Manager via the task definition `secrets` block — the container needs no AWS SDK.
- `defaults: run: working-directory: api` is set at the workflow level (`api.yml:10-12`). The deploy job must override this to `.` since docker build context and AWS CLI file outputs reference paths from the repo root.

## Desired End State

On every push to `main` that touches `api/**`:
1. `lint` and `test` jobs run (existing behaviour).
2. On success, `deploy` job:
   - Builds the `app` stage of `api/Dockerfile`.
   - Tags the image `YYYYMMDDHHmmss-<first 10 chars of SHA>` (e.g. `20260409143022-abc123def0`).
   - Pushes to ECR.
   - Registers a new ECS task definition revision with the updated image.
   - Updates the ECS service and waits for stabilisation.
3. PRs touching `api/**` run only `lint` and `test` — deploy never runs on PRs.

**Verification**: After a merge to `main`, the GitHub Actions run shows all three jobs green. The ECS service shows the new task definition revision, and `GET /health/ready` on the DEV endpoint returns `{"db": true, "cache": true}`.

## What We're NOT Doing

- Not creating any AWS infrastructure (already provisioned in a separate IaC branch).
- Not modifying the Dockerfile.
- Not adding staging/prod deployment stages.
- Not configuring ECR image lifecycle policies.
- Not setting up automatic rollback (ECS handles rollback via `wait-for-service-stability`).

## Implementation Approach

Append a `deploy` job to `.github/workflows/api.yml` using four official AWS GitHub Actions:

1. `aws-actions/configure-aws-credentials@v4` — OIDC auth (no long-lived keys).
2. `aws-actions/amazon-ecr-login@v2` — ECR registry login.
3. `aws-actions/amazon-ecs-render-task-definition@v1` — swap image URI in the downloaded task definition JSON.
4. `aws-actions/amazon-ecs-deploy-task-definition@v2` — register new revision and update the service.

---

## Phase 1: Add Deploy Job to api.yml

### Overview

Append the `deploy` job to `.github/workflows/api.yml`. The job overrides the workflow-level `working-directory` default to `.` (repo root) so that `docker build api/` and the task definition JSON file resolve correctly.

### Changes Required

#### 1. `.github/workflows/api.yml`

Append the following after the closing of the `test` job (after line 73):

```yaml
  deploy:
    name: Deploy to DEV
    runs-on: ubuntu-latest
    needs: [lint, test]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    defaults:
      run:
        working-directory: .

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ vars.AWS_REGION }}

      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image to ECR
        id: build-image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: ${{ vars.ECR_REPOSITORY }}
        run: |
          IMAGE_TAG=$(date +%Y%m%d%H%M%S)-${GITHUB_SHA::10}
          docker build --target app -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG api/
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Download task definition
        run: |
          aws ecs describe-task-definition \
            --task-definition ${{ vars.ECS_TASK_DEFINITION }} \
            --query taskDefinition \
            > task-definition.json

      - name: Render new task definition
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: task-definition.json
          container-name: ${{ vars.ECS_CONTAINER_NAME }}
          image: ${{ steps.build-image.outputs.image }}

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: ${{ vars.ECS_SERVICE }}
          cluster: ${{ vars.ECS_CLUSTER }}
          wait-for-service-stability: true
```

### GitHub Secrets and Variables to Configure

Set these in **GitHub → repository Settings → Secrets and variables → Actions** before the workflow runs.

| Type | Name | Example value | Notes |
|---|---|---|---|
| Secret | `AWS_ROLE_ARN` | `arn:aws:iam::123456789012:role/github-deploy-role` | IAM role with OIDC trust for this repo |
| Variable | `AWS_REGION` | `us-east-1` | AWS region where resources live |
| Variable | `ECR_REPOSITORY` | `pa-compact-api` | ECR repository name (not the full URI) |
| Variable | `ECS_TASK_DEFINITION` | `pa-compact-api` | Task definition family name |
| Variable | `ECS_CONTAINER_NAME` | `api` | Container name inside the task definition |
| Variable | `ECS_SERVICE` | `pa-compact-api` | ECS service name |
| Variable | `ECS_CLUSTER` | `pa-compact-dev` | ECS cluster name |

### Required IAM permissions for `AWS_ROLE_ARN`

```
ecr:GetAuthorizationToken
ecr:BatchCheckLayerAvailability
ecr:InitiateLayerUpload
ecr:UploadLayerPart
ecr:CompleteLayerUpload
ecr:PutImage
ecs:DescribeTaskDefinition
ecs:RegisterTaskDefinition
ecs:DescribeServices
ecs:UpdateService
iam:PassRole   # to pass the ECS task execution role
```

### Success Criteria

#### Automated Verification

- [ ] YAML is valid: `gh workflow view .github/workflows/api.yml`
- [ ] On a PR touching `api/**`: only `lint` and `test` jobs appear in Actions — no `deploy` job
- [ ] On merge to `main` touching `api/**`: all three jobs (`lint`, `test`, `deploy`) run and turn green
- [ ] ECR console shows a new image with tag matching `YYYYMMDDHHmmss-<sha10>` format
- [ ] ECS console shows a new task definition revision after the deploy completes

#### Manual Verification

- [ ] `GET /health/ready` on the DEV load balancer URL returns `{"db": true, "cache": true}`
- [ ] CloudWatch Logs for the new container show structured JSON log output

**Implementation Note**: After completing Phase 1 and automated verification passes, confirm manual testing before closing the beads task.

---

## Testing Strategy

### Manual Testing Steps

1. Create a trivial change in `api/` (e.g. bump a comment) and open a PR — confirm only `lint` and `test` appear, no `deploy`.
2. Merge the PR to `main` — watch the Actions run progress through `lint` → `test` → `deploy`.
3. Check ECR: new image present with expected tag format.
4. Check ECS service: running the new task definition revision, all tasks healthy.
5. Hit `GET /health/ready` on the DEV ALB URL — both `db` and `cache` must be `true`.
6. Check CloudWatch Logs for the new task — JSON log lines present.

## References

- Beads task: pa-compact-licensing-platform-90d
- ADR-0002: `docs/architecture_decision_records/0002-db-config-decomposition.md`
- Existing CI workflow: `.github/workflows/api.yml`
- AWS actions used:
  - `aws-actions/configure-aws-credentials`
  - `aws-actions/amazon-ecr-login`
  - `aws-actions/amazon-ecs-render-task-definition`
  - `aws-actions/amazon-ecs-deploy-task-definition`
