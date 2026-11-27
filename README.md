# PA Compact Licensing Platform

**API Coverage**: [![API Coverage](https://codecov.io/gh/focusconsulting/pa-compact-licensing-platform/branch/main/graph/badge.svg?flag=api)](https://codecov.io/gh/focusconsulting/pa-compact-licensing-platform)

**Client Coverage**: [![Client Coverage](https://codecov.io/gh/focusconsulting/pa-compact-licensing-platform/branch/main/graph/badge.svg?flag=client)](https://codecov.io/gh/focusconsulting/pa-compact-licensing-platform)

## Repository Structure

```text
engineering/api/                  Python API (FastAPI, Python 3.13)
engineering/client/               Next.js frontend (React, TypeScript, USWDS)
engineering/infrastructure/iac/   Infrastructure as Code (OpenTofu)
product/context/flows/            The flows the system implements
```

## Prerequisites

Install these at the versions in [`.tool-versions`](.tool-versions):

| Tool | Version | Install |
|---|---|---|
| Python | 3.13.12 | <https://www.python.org/downloads/> |
| Node.js | 25.8.2 | <https://nodejs.org/en/download> |
| [uv](https://docs.astral.sh/uv/) (Python package manager) | 0.11.2 | <https://docs.astral.sh/uv/getting-started/installation/> |
| [just](https://github.com/casey/just) (task runner) | 1.48.1 | <https://github.com/casey/just#installation> |
| [OpenTofu](https://opentofu.org/) (only to plan or apply the infrastructure, see [`engineering/infrastructure/iac/README.md`](engineering/infrastructure/iac/README.md)) | 1.11.6 | <https://opentofu.org/docs/intro/install/> |

Or, our preference, install them with [asdf](https://asdf-vm.com/guide/getting-started.html),
which reads the versions from `.tool-versions`:

```bash
for tool in python nodejs uv just opentofu; do asdf plugin add "$tool"; done
asdf install
```

Then, however you installed them:

- [pnpm](https://pnpm.io/installation) 10: `npm install -g pnpm@latest-10`
- Docker, running (local Postgres for the API, and image builds)
- [pre-commit](https://pre-commit.com/) (`pipx install pre-commit` or `brew install pre-commit`)

## Pre-commit hooks

Install once after cloning:

```bash
pre-commit install           # sets up the git hook
pre-commit install-hooks     # pre-fetch hook environments
```

If `pre-commit install` refuses because `core.hooksPath` is set (left
over from an older tool), run `git config --unset core.hooksPath` first.

Hooks run automatically on `git commit`. To run them on demand:

```bash
pre-commit run --all-files   # lint the whole repo
pre-commit run               # lint staged files only
```

Hooks include: ruff (Python lint + format), gitleaks (secret detection),
markdownlint, and generic file checks (trailing whitespace, EOF, merge
conflicts, large files, YAML/JSON validity). The same hooks run in CI via
`.github/workflows/lint.yml`.

## Run the whole system locally

From a fresh clone, with the prerequisites above and Docker running:

```bash
just up
```

That installs dependencies, creates `engineering/api/.env` and
`engineering/client/.env` from their examples if missing, starts the
local services, applies migrations, loads the local users, and runs the API,
the Worker, and the client. Ctrl-C stops them; `just down` stops the services.
With the system running, `just e2e` builds the client and runs the Playwright
tests against it ([`engineering/e2e/`](engineering/e2e/README.md)).
No AWS account or credentials are needed.

| What | Where |
|---|---|
| The app | <http://localhost:3000> |
| API docs | <http://localhost:8000/docs> |
| Email (maildev) | <http://localhost:1080> |
| File storage console (RustFS, `rustfsadmin` / `rustfsadmin`) | <http://localhost:9301> |
| Malware scanner (tags uploads as GuardDuty would) | `docker compose -p pa-compact logs malware-scanner` |

Sign in as any user in
[`engineering/mocks/cognito/db/local_licensing.json`](engineering/mocks/cognito/db/local_licensing.json)
with `Local-Passw0rd!`.
`backfill@example.com` (`Temp-Passw0rd!`) is asked to choose a new password
on first sign-in.

Each AWS service is replaced by a local one that the app reaches through
its production client; only URLs differ (constitution Principle IV), except
that sign-in uses password auth instead of SRP
([ADR-0010](engineering/adrs/0010-local-sign-in-uses-password-auth.md)). The
names, ports, and settings are in
[`engineering/api/.env.example`](engineering/api/.env.example) and
[`engineering/client/.env.example`](engineering/client/.env.example). If your
`.env` files predate the local stack, copy the Cognito, SMTP, and S3 settings
from the examples; the RustFS keys are now the standard `AWS_*` variables
([ADR-0017](engineering/adrs/0017-s3-client.md)).

## Getting Started

### API

```bash
cd engineering/api
export UV_PYTHON=$(asdf which python) # use the python from asdf
cp .env.example .env   # local settings; works as-is with `just infra`
just install           # Install Python dependencies
just infra             # Start the local services (resets their data)
just migrate           # Apply migrations
just seed              # Load the local users
just seed demo         # Add demo practitioners in every status (engineering/docs/demo.md)
just dev               # Run API with hot reload (localhost:8000/docs)
just worker            # Run the Worker, which sends email and runs event handlers
just job heartbeat     # Run one scheduled job once
```

`just test` also needs `just infra` running.

### Client

```bash
cd engineering/client
cp .env.example .env         # public settings only, no secrets
pnpm install                 # Install Node dependencies
pnpm dev                     # Run dev server (localhost:3000)
```

### Troubleshooting

- **`Input should be 'LOCAL_DEV', 'STAGING' or 'PROD'`** when
  running the API or its tests: a variable exported in your shell is
  overriding `.env`, because `uv run --env-file` does not replace
  variables that are already set. Check with `env | grep -i environment`
  and unset it (for example `unset ENVIRONMENT`), or remove it from your
  shell profile.

## Development

### API Commands

From `engineering/api/`:

```bash
just infra             # Start the local services
just infra-down        # Stop them and delete their data
just test              # Run tests
just test-coverage     # Run tests with coverage
just lint              # Run all linting (ruff + pyright)
just format            # Format code
just build             # Build production Docker image
```

### Client Commands

From `engineering/client/`:

```bash
pnpm check             # Everything CI checks: lint, typecheck, tests at 100% coverage
pnpm test              # Run tests (vitest)
pnpm lint              # ESLint (Airbnb), Stylelint, Prettier; zero warnings
pnpm format            # Fix formatting and auto-fixable lint
pnpm a11y              # Build, serve, and scan pages with pa11y-ci (axe, WCAG 2 AA, includes contrast)
pnpm storybook         # Run Storybook
pnpm build             # Production build
```

Code style follows the GSA 18F front-end guide (SOW §5.2): ESLint with the
Airbnb style guide, Stylelint's standard SCSS rules with BEM class names, and
Prettier. The deliberate deviations are explained in
[`eslint.config.mjs`](engineering/client/eslint.config.mjs).
