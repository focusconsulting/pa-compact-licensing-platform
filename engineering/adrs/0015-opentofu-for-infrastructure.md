---
category: architecture
status: proposed
date: 2026-10-28
---

# ADR-0015: OpenTofu for Infrastructure

## Status

Proposed

## Date

2026-10-28

## Context

The infrastructure under `engineering/infrastructure/iac/` is HCL applied by hand with Terraform 1.14 ([README](../infrastructure/iac/README.md)). Epic 3 (SCRUM-69) builds the deploy pipeline on it: plans commented on pull requests, applies on merge, and tag-driven promotion (SCRUM-83). Whatever binary that pipeline runs is the one the team keeps, so the choice is made before the pipeline exists.

Terraform has been under HashiCorp's Business Source License since 1.6 (2023), and HashiCorp is now part of IBM. The license permits our use, but it is source-available rather than open source, its terms are the licensor's to change, and it is third-party material the Commission must consent to and will own the use of ([SOW §7.5](../../product/context/PA%20Compact%20Data%20System%20SOW%20-%20Focus%20Consulting.md#75-intellectual-property-and-open-source)). The Commission takes ownership of all infrastructure as code and the tooling to deploy it, and must be able to run it with any vendor after the engagement.

OpenTofu is the Linux Foundation's fork of Terraform 1.5, under the MPL-2.0. It runs the same HCL, reads Terraform 1.x state, and installs the same providers from its own registry. The module uses nothing Terraform-specific: an S3 backend with native locking, `terraform_remote_state`, and the `hashicorp/aws` and `hashicorp/random` providers, all of which OpenTofu supports.

## Decision

1. **OpenTofu runs the infrastructure.** The pinned version is in `.tool-versions` (constitution Principle XII); the module's `required_version` constrains OpenTofu, not Terraform.
2. **The provider lockfile is committed.** `.terraform.lock.hcl` leaves `.gitignore`, so every machine and CI install the same provider builds. Principle XV already lists it as a lockfile.
3. **`just` is the entry point**, as for the API and client: `engineering/infrastructure/justfile` holds `init`, `plan`, `apply`, `fmt`, `validate`, and `check`, each taking a component and an environment. `gen-tf-plan.py` is removed.
4. **Nothing else changes.** File names keep the `.tf` extension and the `terraform {}` block, which OpenTofu reads; the directory stays `components/<name>/terraform/`, so existing links and state keys hold.

## Pros and cons

### OpenTofu (chosen)

- Pro: open-source license with no restrictions for the Commission to consent to or inherit, and no licensor who can change the terms.
- Pro: the HCL, providers, and state carry over; the switch is a version pin, a constraint, and a lockfile.
- Pro: native S3 state locking (`use_lockfile`), which the backends already use.
- Con: a second community to track for provider and language changes. Mitigation: the lockfile pins providers, and `.tool-versions` pins the binary, so an upgrade is a reviewed change.
- Con: Terraform may not read state after OpenTofu writes it. Mitigation: nothing here runs Terraform again; a return would go through `tofu state pull` and a fresh `terraform init`.

### Stay on Terraform

- Pro: no change.
- Con: the pipeline, runbook, and every documented command are built on a binary under a license the Commission would have to accept and could later be asked to pay for.
- Con: the constraint `required_version = "1.14.9"` already pins a version only Terraform ships, so the pin would stay a Terraform one.

### Another tool (Pulumi, CDK for Terraform)

- Con: a rewrite of 1,700 lines of working HCL and a new language for the team and the Commission's successors to learn, against Principle I's spirit of a stack that one set of skills can read.

## Consequences

- `.tool-versions` gains `opentofu`; the root README's prerequisites and AGENTS.md's verification commands name `tofu` and the infrastructure `justfile`.
- The constitution's Technology Stack and Principle XV name OpenTofu where they named Terraform.
- The per-component `.terraform.lock.hcl` is committed and regenerated with `tofu providers lock` for the platforms the team and CI run on.
- A CI job runs `tofu fmt -check` and `tofu validate` on every pull request that touches the infrastructure; SCRUM-83 adds plan and apply to it.
- The first `tofu plan` against `dev` is the compatibility check: the state was last written by Terraform 1.14, and the expected result is no changes.

## Related

- Jira: SCRUM-175, under SCRUM-69
- Implementation plan: `engineering/thoughts/shared/plans/iac/2026-10-28-SCRUM-82-environment-contract-opentofu.md`
