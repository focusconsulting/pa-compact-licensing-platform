# PA Compact infrastructure

The AWS infrastructure, as OpenTofu code ([ADR-0015](../../adrs/0015-opentofu-for-infrastructure.md)).
What it builds is drawn in [`engineering/docs/architecture.md`](../../docs/architecture.md).

## Layout

```text
components/<component>/opentofu/   The code: app (everything the system runs on) and ecr (the image repositories)
environments/<env>/<region>/        One backend and one tfvars file per component, per environment
```

Each environment is an `<env>/<region>` directory holding
`<component>.backend.hcl` (where its state lives) and `<component>.tfvars`
(its values). The code is the same for every environment; only those files
differ, and the module refuses an `environment_name` other than `dev`,
`staging`, or `prod`.

## Prerequisites

- OpenTofu and `just`, at the versions in the root [`.tool-versions`](../../../.tool-versions)
  (`asdf install` from the repository root).
- The AWS CLI (`asdf plugin add awscli`), signed in to the environment's
  account as below. `just check` needs no credentials.

### Getting access

Each environment is its own AWS account, reached through Focus's IAM
Identity Center with the `AccountDeveloperAccess` role. The Identity Center
start URL is not in this public repository; ask the team for it. Then add
to `~/.aws/config`:

```ini
[sso-session focus]
sso_start_url = <the start URL>
sso_region = us-east-1

[profile dev-pacompact]
sso_session = focus
sso_account_id = 126942145463
sso_role_name = AccountDeveloperAccess
region = us-east-1
```

Sign in once a day and point the commands at the profile:

```bash
aws sso login --profile dev-pacompact
aws sts get-caller-identity --profile dev-pacompact   # Account must be 126942145463
export AWS_PROFILE=dev-pacompact
just plan app dev
```

A new environment gets its own `[profile <env>-pacompact]` block with its
account ID, and the same role.

## Commands

From `engineering/infrastructure/`:

```bash
just check             # tofu fmt -check and tofu validate on every component; what CI runs
just fmt               # format every .tf file
just plan app dev      # plan a component against an environment
just apply app dev     # apply it (asks for confirmation)
```

`plan` and `apply` initialise the component against the environment's backend
first, so switching environments on one checkout needs nothing else. Apply
`ecr` before `app` in a new environment: `app` needs the repository `ecr`
creates.

Every pull request that touches this directory runs `just check` in
[`.github/workflows/iac.yml`](../../../.github/workflows/iac.yml), then plans
each component against `dev` and posts the plan as a comment on the pull
request. The `app` plan runs the image the pull request's commit would
build, so it always shows the task definitions changing.

## Deploying

A deploy is `just deploy <env>`: apply `ecr`, build and push the API image
tagged with the commit, apply `app` with that tag, build the client from the
app outputs, sync it to S3, and invalidate CloudFront. Nothing else deploys
anything, and nothing deploys on its own: dev is deployed when someone runs
the `Deploy` workflow, until the team turns on deploy-on-merge.

| Trigger | Environment | Gate |
|---|---|---|
| Running the `Deploy` workflow by hand (Actions, Run workflow) | `dev` | Whoever can run workflows; a merge to `main` does not deploy yet |
| Tag `v*-rc*` | `test` | The `test` GitHub Environment's required reviewers |
| Tag `v*` (no `-rc`) | `prod` | The `prod` GitHub Environment's required reviewers |

[`deploy.yml`](../../../.github/workflows/deploy.yml) runs it from the
environment's GitHub Environment, whose variables name the role to assume
(`AWS_APPLY_ROLE_ARN`) and the region. Deploys to one environment run one at
a time. From a laptop, with the environment's credentials, `just deploy dev`
does the same thing. Until `test` and `prod` have environment files, a tag
stops at the Environment's review and, if approved, fails at `just init`.

## What differs between environments

Everything an environment chooses is a variable set in its tfvars files;
the module has no environment-specific defaults. A variable with a default
may be left out of the tfvars file when the default is right.

### `ecr`

| Variable | What it sets | `dev` |
|---|---|---|
| `environment_name` | The environment's name, in every resource name | `dev` |
| `aws_region` | Where the repositories live | `us-east-1` |
| `tf_state_bucket` | The state bucket | `focus-dev-pacompact-terraform-state` |
| `repositories` | The repositories to create: name, tag mutability, scan on push | `pacompact-app-dev`, immutable, scanned |

### `app`

| Variable | What it sets | `dev` | Default |
|---|---|---|---|
| `environment_name` | The environment's name: resource and secret names, and the containers' `ENVIRONMENT` (upper-cased) | `dev` | required |
| `aws_region` | Where everything but the CloudFront certificate lives | `us-east-1` | required |
| `tf_state_bucket` | The state bucket, which also holds the network bootstrap state | `focus-dev-pacompact-terraform-state` | required |
| `network_state_key` | Key of the bootstrap state that exports `vpc_id` and `private_subnet_ids` | default | `bootstrap/network/default/terraform.tfstate` |
| `dns_name` | The site's host name; its parent is the Route 53 zone, the certificate, and the email domain | `site.dev-pacompact.aws.focusconsulting.io` | required |
| `db_username` | The application's database user | `licensing` | required |
| `db_instance_class` | Aurora instance class | `db.t4g.medium` | `db.t4g.medium` |
| `instance_count` | Aurora instances | default | `1` |
| `backup_retention_period` | Days of automated database backups | `1` | `30` |
| `repo_name` | The `ecr` component's `repository_url` for the API image | the dev repository | required |
| `image_tag` | The commit SHA whose image runs; `just deploy` passes it, tfvars never set it | per deploy | required |
| `ecs_max_capacity` | Most API tasks the autoscaler may run | default | `2` |
| `commission_ops_email` | The Commission's operational mailbox; empty sends nothing | default | empty |
| `cognito_callback_url`, `cognito_logout_url` | Cognito redirect URLs | default | `https://<dns_name>` |
| `acm_certificate_arn` | Declared for an HTTPS listener on the load balancer; not yet used (SCRUM-84) | default | none |

## Adding an environment

1. Create `environments/<env>/<region>/` with `ecr.backend.hcl`,
   `ecr.tfvars`, `app.backend.hcl`, and `app.tfvars`, copying `dev`'s and
   changing the values in the tables above. Each backend's `key` carries the
   environment name.
2. Make what the module looks up, which it does not create:
   - The state bucket, with versioning, and the network bootstrap state at
     `network_state_key` exporting `vpc_id` and `private_subnet_ids`.
   - A public Route 53 hosted zone for the parent of `dns_name`, and an issued
     wildcard ACM certificate for it in `us-east-1`.
   - The Secrets Manager secret `<env>-slack-tfvar` (keys `slack_team_id`,
     `slack_channel_id`). A jumpbox, if wanted, is the bootstrap repo's
     `create_jumpbox`; the module reads its security group from the network
     state.
   - SES production access for the account; a new account's SES sends only to
     verified addresses.
3. `just apply ecr <env>`, put its `repository_url` in `app.tfvars` as
   `repo_name`, then `just apply app <env>`.
