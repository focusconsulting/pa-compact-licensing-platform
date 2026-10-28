# Environment Contract and OpenTofu Implementation Plan

## Overview

Two small tasks that the rest of epic 3 builds on, in one pull request: move the infrastructure code from Terraform to OpenTofu (SCRUM-175), and fix the contract for what differs between environments so `test` and `prod` can be added later by adding files, not code (SCRUM-82).

## Related

- **Spec**: epic 3 in [MVP epics and tickets](../../../../../product/backlog/mvp-jira-tickets.md) and F-09 in the [MVP ticket breakdown](../../../../../product/backlog/mvp-ticket-breakdown.md); card 3 in [Engineering tickets at a glance](../../../../../product/backlog/engineering-tickets-at-a-glance.md)
- **Flows**: none directly
- **Compact rules**: none. [SOW §2](../../../../../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md#2-scope-of-work) (United States hosting) and [SOW §7.5](../../../../../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md#75-intellectual-property-and-open-source) (third-party materials)
- **Decisions**: scoping decisions recorded on SCRUM-69 on 2026-10-28: only `dev` is built in this epic, reusing the existing state bucket; work branches from PR #136; OpenTofu replaces Terraform before the pipeline is built
- Jira: SCRUM-82, SCRUM-175 (both under SCRUM-69); SCRUM-175 blocks SCRUM-83 and SCRUM-84
- ADRs: [ADR-0015](../../../../adrs/0015-opentofu-for-infrastructure.md) (written with this plan)
- **Area**: iac, with one line in the API

## Constitution Check

- **I, Idiomatic Python and FastAPI**: the API change is one `Literal` value in `config.py`; no new dependency.
- **III, Test coverage**: the `Literal` change adds a settings test so the new value is exercised.
- **XI, Prose earns its keep**: the infrastructure README gains the contract table and the steps to add an environment, which the code cannot say; the obsolete manual-apply instructions go.
- **XII, A fresh clone runs from the README**: `opentofu` is pinned in `.tool-versions` and installed with asdf like the other tools; CI reads the same pin; the root README's prerequisites and AGENTS.md's verification commands are updated in the same PR; every documented command is run while reviewing.
- **XV, Pull requests stay reviewable**: hand-written changes are the justfile, the workflow, variable blocks, and one API line, well under 600 lines. Lockfiles and Markdown do not count.
- **Technology Stack**: names Terraform. ADR-0015 records the change, and this PR amends the stack section and Principle XV's lockfile line to say OpenTofu.

## Current State Analysis

- Two components, `app` and `ecr`, under `engineering/infrastructure/iac/components/<name>/terraform/`, with one environment under `environments/dev/us-east-1/` holding `<component>.backend.hcl` and `<component>.tfvars`.
- Both `main.tf` files pin `required_version = "1.14.9"`, a Terraform version. OpenTofu 1.11.6 refuses the module on `init` and `validate` with that constraint (verified 2026-10-28).
- `tofu fmt -check` fails on `app/terraform/cdn.tf`, `app/terraform/main.tf`, and `ecr/terraform/variables.tf`.
- `.gitignore` excludes `.terraform.lock.hcl`, so no provider lockfile is committed, although constitution Principle XV lists it as a lockfile.
- Both backends already use `use_lockfile = true`, which OpenTofu's S3 backend supports natively.
- `gen-tf-plan.py` (255 lines) discovers components and environments, runs `terraform init`, prompts for unset variables, and prints or runs `terraform plan`. The README's manual steps duplicate it.
- `app/terraform/variables.tf` declares the per-environment inputs. `tf_state_bucket` defaults to the dev bucket name; `environment_name`'s description says `dev | stage | prod` with no validation. `ecr/terraform/variables.tf` defaults `tf_state_bucket` and `aws_region` to dev values and declares `environment_name` without a type.
- `app/terraform/main.tf` reads VPC and subnet IDs from remote state at the hard-coded key `bootstrap/network/default/terraform.tfstate` in `var.tf_state_bucket`. Nothing in the repo creates that state; the README does not mention it.
- `app/terraform/ecs.tf` and the branch's `worker.tf` pass `ENVIRONMENT = upper(var.environment_name)` to the containers. `engineering/api/licensing_api/config.py:17` accepts `LOCAL_DEV`, `DEV`, `STAGING`, `PROD`, so a `test` environment's containers would fail settings validation at startup. `settings.environment` is read in `__main__.py:70` (OpenTelemetry resource attribute) and `migrations.py:15` (a log line) only.
- The branch `feature/SCRUM-80-terraform` (PR #136, draft) adds `worker.tf`, `scheduler.tf`, `ses.tf`, and `commission_ops_email`. This plan's branch was created from it, so the PR targets that branch until #136 merges, then `main`.
- `.claude/commands/implement_plan.md`, `validate_plan.md`, `describe_pr.md`, and `create_plan.md` give `terraform validate` and `terraform fmt -check` as the IaC verification commands; `.claude/settings.json` allows `Bash(terraform *)`.
- No AWS credentials are configured on the planning machine, so `tofu plan` against `dev` is a manual step for someone with access.

## Desired End State

- `cd engineering/infrastructure && just check` passes: `tofu fmt -check` and `tofu validate` on both components, with no AWS credentials.
- `just plan app dev` and `just plan ecr dev` run `tofu plan` against the dev backend and report no changes (the OpenTofu state-compatibility check from ADR-0015).
- No file under `engineering/infrastructure/`, the READMEs, AGENTS.md, the constitution, or `.claude/commands/` names the `terraform` binary.
- The infrastructure README documents every per-environment variable, its dev value, and what a new environment must provide outside the module.
- A GitHub Actions job runs `just check` on every pull request that touches `engineering/infrastructure/`.
- `Settings(environment="TEST")` validates.

### Key Discoveries:
- `engineering/infrastructure/iac/components/app/terraform/main.tf:27` and `ecr/terraform/main.tf:13`: the only two places that break OpenTofu.
- `engineering/infrastructure/iac/components/app/terraform/main.tf:49-56`: the remote-state read that makes a bootstrap step an undocumented prerequisite.
- `engineering/infrastructure/iac/components/app/terraform/variables.tf:1-5` and `ecr/terraform/variables.tf:1-9`: dev values baked in as defaults, which the contract removes.
- `engineering/api/justfile` and the root `justfile`: the recipe style to copy (a comment line above each recipe, parameters with defaults).
- `.github/workflows/lint.yml`: the smallest existing workflow, the model for `iac.yml`.

## What We're NOT Doing

- Creating `test` or `prod` environment files, backends, or GitHub Environments (SCRUM-83).
- Plan-on-PR, apply-on-merge, tag promotion, or `just deploy` (SCRUM-83).
- Checkov, or fixing anything Checkov will report (SCRUM-84).
- Checking the `bootstrap/network` state's Terraform into the repo. This plan documents it as a prerequisite; SCRUM-83's bootstrap runbook decides whether it moves into the repo.
- Removing `STAGING` from the API's accepted environment names (decided 2026-10-28: add `TEST`, keep `STAGING`).
- Renaming `components/<name>/terraform/` directories or `.tf` files.
- Changing any resource. Both components must plan with no changes against `dev` after this PR.

## Implementation Approach

Phase 1 makes the module run under OpenTofu and gives it a `just` entry point and a CI check, changing no resources. Phase 2 tightens the variable contract, documents it, and widens the API's environment literal. Each phase is one commit; together they are one pull request against `feature/SCRUM-80-terraform`, retargeted to `main` once PR #136 merges.

The OpenTofu version is 1.11.6, the release installed on the team's machines on 2026-10-28; the module constrains `~> 1.11` so patch upgrades need only a `.tool-versions` change.

---

## Phase 1: Run the module with OpenTofu

### Overview

Pin OpenTofu, fix the version constraint, commit the provider lockfile, replace the plan script with a justfile, add a CI check, and update every document that names Terraform.

### Changes Required:

#### 1. Tool pin
**File**: `.tool-versions`
**Changes**: add `opentofu 1.11.6`.

#### 2. Version constraints and formatting
**Files**: `engineering/infrastructure/iac/components/app/terraform/main.tf`, `engineering/infrastructure/iac/components/ecr/terraform/main.tf`
**Changes**: replace the pin with a constraint OpenTofu satisfies, then run `tofu fmt -recursive` from `engineering/infrastructure/iac` (reformats `app/terraform/cdn.tf`, `app/terraform/main.tf`, `ecr/terraform/variables.tf`).

```hcl
terraform {
  required_version = "~> 1.11"
```

#### 3. Provider lockfiles
**Files**: `.gitignore`, `engineering/infrastructure/iac/components/app/terraform/.terraform.lock.hcl`, `engineering/infrastructure/iac/components/ecr/terraform/.terraform.lock.hcl`
**Changes**: remove `.terraform.lock.hcl` from `.gitignore`. In each component directory run `tofu init -backend=false` then `tofu providers lock -platform=linux_amd64 -platform=darwin_arm64 -platform=darwin_amd64`, and commit both lockfiles. Linux is for CI; the two Darwin platforms cover the team's machines.

#### 4. Justfile replaces the plan script
**File**: `engineering/infrastructure/justfile` (new); delete `engineering/infrastructure/gen-tf-plan.py`
**Changes**: recipes take a component and an environment; the region defaults to `us-east-1` because every environment is US-only (SOW §2) and `dev` is there. `init` runs with `-reconfigure` so switching environments on one checkout works.

```just
# Infrastructure under iac/, applied with OpenTofu. See iac/README.md.

iac := justfile_directory() / "iac"

# Show available commands
default:
    @just --list

# Initialise a component against an environment's backend (safe to rerun; switches environments)
init component env region="us-east-1":
    cd {{ iac }}/components/{{ component }}/terraform && tofu init -input=false -reconfigure \
        -backend-config={{ iac }}/environments/{{ env }}/{{ region }}/{{ component }}.backend.hcl

# Plan a component against an environment
plan component env region="us-east-1": (init component env region)
    cd {{ iac }}/components/{{ component }}/terraform && tofu plan -input=false \
        -var-file={{ iac }}/environments/{{ env }}/{{ region }}/{{ component }}.tfvars

# Apply a component to an environment (prompts for confirmation)
apply component env region="us-east-1": (init component env region)
    cd {{ iac }}/components/{{ component }}/terraform && tofu apply -input=false \
        -var-file={{ iac }}/environments/{{ env }}/{{ region }}/{{ component }}.tfvars

# Format every .tf file
fmt:
    tofu fmt -recursive {{ iac }}

# Validate every component with no backend or credentials
validate:
    for c in {{ iac }}/components/*/terraform; do \
        (cd "$c" && tofu init -backend=false -input=false >/dev/null && tofu validate) || exit 1; \
    done

# Everything CI checks: formatting and validation
check: validate
    tofu fmt -check -recursive {{ iac }}
```

#### 5. CI check
**File**: `.github/workflows/iac.yml` (new)
**Changes**: on pull requests that touch `engineering/infrastructure/**` or the workflow, and on push to `main`, install `just` and OpenTofu at the versions in `.tool-versions`, then run `just check` from `engineering/infrastructure`. No AWS credentials. Use `opentofu/setup-opentofu` with `tofu_version` read from `.tool-versions` and `extractions/setup-just`; confirm each action's current major version when implementing and pin it.

```yaml
name: IaC CI

on:
  push:
    branches: [main]
  pull_request:
    paths: [engineering/infrastructure/**, .github/workflows/iac.yml, .tool-versions]
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Read tool versions
        id: versions
        run: |
          echo "tofu=$(awk '$1 == "opentofu" {print $2}' .tool-versions)" >> "$GITHUB_OUTPUT"
          echo "just=$(awk '$1 == "just" {print $2}' .tool-versions)" >> "$GITHUB_OUTPUT"
      - uses: opentofu/setup-opentofu@v1
        with:
          tofu_version: ${{ steps.versions.outputs.tofu }}
          tofu_wrapper: false
      - uses: extractions/setup-just@v3
        with:
          just-version: ${{ steps.versions.outputs.just }}
      - name: Format and validate
        working-directory: engineering/infrastructure
        run: just check
```

#### 6. Documents that name Terraform
**Files**: `engineering/infrastructure/iac/README.md`, `README.md`, `AGENTS.md`, `engineering/engineering-constitution.md`, `.claude/commands/create_plan.md`, `.claude/commands/implement_plan.md`, `.claude/commands/validate_plan.md`, `.claude/commands/describe_pr.md`, `.claude/settings.json`
**Changes**:
- Infrastructure README: replace the manual steps with the `just` recipes and the prerequisites (asdf, AWS credentials for the target account). The contract table is added in Phase 2.
- Root README: `opentofu` in the asdf block and the prerequisites list; the repository-structure line says OpenTofu.
- AGENTS.md: a "When iterating on the infrastructure" list with `just check`, `just plan <component> <env>`, and `just apply <component> <env>` from `engineering/infrastructure/`.
- Constitution: Technology Stack "Infrastructure" entry and the "All infrastructure changes go through Terraform" bullet say OpenTofu; Principle XV's "Terraform" in the hand-written list says "infrastructure code"; bump the version and "Last amended" date.
- `.claude/commands/*`: the IaC verification lines become `cd engineering/infrastructure && just check`.
- `.claude/settings.json`: `Bash(tofu *)` beside, or instead of, `Bash(terraform *)`.

### Success Criteria:

#### Automated Verification:
- [ ] `cd engineering/infrastructure && just check` passes.
- [ ] `git grep -n -i terraform -- engineering/infrastructure README.md AGENTS.md engineering/engineering-constitution.md .claude/commands` shows only the `terraform {}` block, directory names, `.terraform.lock.hcl`, and the `terraform_remote_state` data source.
- [ ] Both lockfiles are tracked: `git ls-files '**/.terraform.lock.hcl'` lists two files.
- [ ] `pre-commit run --files <changed Markdown and YAML>` passes.
- [ ] The `IaC CI` workflow is green on the pull request.

#### Manual Verification:
- [ ] With credentials for the dev account, `just plan app dev` and `just plan ecr dev` report no changes. If OpenTofu refuses the state because Terraform 1.14 wrote it, stop and record the error on SCRUM-175 before trying anything that writes state.
- [ ] `asdf install` on a fresh clone installs OpenTofu 1.11.6 and `tofu version` matches.

**Implementation Note**: pause after the dev plans for confirmation before Phase 2.

---

## Phase 2: The per-environment contract

### Overview

Make the module refuse an unknown environment, remove dev values from defaults, let a new environment point at its own bootstrap state, document the contract, and let the API accept `TEST`.

### Changes Required:

#### 1. App variables
**File**: `engineering/infrastructure/iac/components/app/terraform/variables.tf`
**Changes**: validate `environment_name`; drop the dev default from `tf_state_bucket`; add `network_state_key`.

```hcl
variable "environment_name" {
  description = "The environment: dev, test, or prod. Names resources, secrets, and the ENVIRONMENT the containers run with."
  type        = string
  validation {
    condition     = contains(["dev", "test", "prod"], var.environment_name)
    error_message = "environment_name must be dev, test, or prod."
  }
}

variable "tf_state_bucket" {
  description = "The state bucket this environment's components and its network bootstrap state live in"
  type        = string
}

variable "network_state_key" {
  description = "Key in tf_state_bucket of the bootstrap state that exports vpc_id and private_subnet_ids"
  type        = string
  default     = "bootstrap/network/default/terraform.tfstate"
}
```

**File**: `engineering/infrastructure/iac/components/app/terraform/main.tf`
**Changes**: `data "terraform_remote_state" "network"` reads `key = var.network_state_key`.

#### 2. ECR variables
**File**: `engineering/infrastructure/iac/components/ecr/terraform/variables.tf`
**Changes**: `type = string` on every variable; remove the defaults from `tf_state_bucket` and `aws_region`; the same `environment_name` validation as the app component. `environments/dev/us-east-1/ecr.tfvars` already sets all three.

#### 3. Dev tfvars
**File**: `engineering/infrastructure/iac/environments/dev/us-east-1/app.tfvars`
**Changes**: none to values. Group the file by the table's sections and remove the stale `acm_certificate_arn` comment (the variable is declared but unused; SCRUM-84 wires or removes it).

#### 4. The contract, documented
**File**: `engineering/infrastructure/iac/README.md`
**Changes**: a table of every variable in both components: name, what it controls, the dev value, and whether a new environment must set it. Then "Adding an environment": the files to create under `environments/<env>/<region>/`, and what must exist outside the module before `just plan app <env>` succeeds:
- the state bucket, versioned, and the network bootstrap state at `network_state_key` exporting `vpc_id` and `private_subnet_ids`;
- a Route 53 public hosted zone for the parent of `dns_name` and an issued wildcard ACM certificate for it in `us-east-1`;
- Secrets Manager secrets `<env>-slack-tfvar` (keys `slack_team_id`, `slack_channel_id`) and, if `jumpbox_enabled`, `<env>-jumpbox-sgid-tfvar` (key `jumpbox_sg_id`);
- the ECR component applied first, since `repo_name` is its output;
- SES production access requested for the account (sandbox otherwise).
SCRUM-83's bootstrap runbook grows from this section.

#### 5. API accepts TEST
**File**: `engineering/api/licensing_api/config.py`
**Changes**: `environment: Literal['LOCAL_DEV', 'DEV', 'TEST', 'STAGING', 'PROD'] = 'LOCAL_DEV'`.

**File**: `engineering/api/.env.example`
**Changes**: the comment lists `TEST`.

**File**: `engineering/api/tests/test_config.py` (new, or the existing settings test if one exists)
**Changes**: `Settings(environment='TEST').environment == 'TEST'`, and an unknown name raises `ValidationError`.

### Success Criteria:

#### Automated Verification:
- [ ] `cd engineering/infrastructure && just check` passes.
- [ ] `cd engineering/api && just lint` and `just test-coverage` pass at 100%.
- [ ] `tofu plan` with `environment_name = "stage"` fails on the validation message (run with `-backend=false` is not possible for plan; use `tofu validate` plus `tofu console` or a throwaway tfvars with `just plan app dev` to confirm the message once).
- [ ] `pre-commit run --files engineering/infrastructure/iac/README.md` passes.

#### Manual Verification:
- [ ] `just plan app dev` and `just plan ecr dev` still report no changes.
- [ ] A reader can list, from the README alone, everything a `test` environment needs before its first plan.

---

## Testing Strategy

### API Tests:
- Settings accept `TEST` and reject an unknown environment name.

### E2E Tests:
- None; no user flow changes.

### Manual Testing Steps:
1. `asdf install` from the repo root; `tofu version` prints 1.11.6.
2. `cd engineering/infrastructure && just check`.
3. With dev credentials: `just plan app dev` and `just plan ecr dev`; both say no changes.
4. Edit a `.tf` file's spacing; `just check` fails; `just fmt` fixes it.

## Security Impact Assessment

Not applicable. No data flow, permission, or network rule changes; both components plan with no changes. The tool switch affects who reads and writes the state file, which holds the generated database master password; the backend, bucket, and credentials are unchanged.

## Dates and Deadlines

Not applicable.

## Migration Notes

Not applicable; no database migration.

## Documentation Updates

- ADR-0015 (written).
- `engineering/infrastructure/iac/README.md`: rewritten around the justfile and the contract table.
- Root `README.md`, `AGENTS.md`, `engineering/engineering-constitution.md`, `.claude/commands/*.md`: as listed in Phase 1.
- `engineering/docs/architecture.md`: no diagram change; the containers are the same.
- No new dependency for the license inventory. OpenTofu is a build tool, not a shipped component; ADR-0015 records its license (MPL-2.0) for the Commission's third-party materials register.

## Performance Considerations

None.

## References

- Jira: SCRUM-82, SCRUM-175, SCRUM-69
- ADR-0015: `engineering/adrs/0015-opentofu-for-infrastructure.md`
- Earlier infrastructure plans: `engineering/thoughts/shared/plans/cross-cutting/2026-04-09-deploy-api-dev.md`, `2026-04-10-deploy-frontend-dev.md`, `2026-04-13-metrics-and-alerting.md`
- OpenTofu S3 backend and migration guide: <https://opentofu.org/docs/language/settings/backends/s3>, <https://opentofu.org/docs/intro/migration/migration-guide>
