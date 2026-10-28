# PA Compact infrastructure

The AWS infrastructure, as OpenTofu code ([ADR-0015](../../adrs/0015-opentofu-for-infrastructure.md)).
What it builds is drawn in [`engineering/docs/architecture.md`](../../docs/architecture.md).

## Layout

```text
components/<component>/terraform/   The code: app (everything the system runs on) and ecr (the image repositories)
environments/<env>/<region>/        One backend and one tfvars file per component, per environment
```

Each environment is an `<env>/<region>` directory holding
`<component>.backend.hcl` (where its state lives) and `<component>.tfvars`
(its values). The code is the same for every environment; only those files
differ.

## Prerequisites

- OpenTofu and `just`, at the versions in the root [`.tool-versions`](../../../.tool-versions)
  (`asdf install` from the repository root).
- AWS credentials for the environment's account in your shell, with access
  to its state bucket. `just check` needs none.

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
[`.github/workflows/iac.yml`](../../../.github/workflows/iac.yml). Plans and
applies from CI are SCRUM-83's.
