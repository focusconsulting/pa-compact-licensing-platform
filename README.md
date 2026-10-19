# PA Compact Licensing Platform

**API Coverage**: [![API Coverage](https://codecov.io/gh/focusconsulting/pa-compact-licensing-platform/branch/main/graph/badge.svg?flag=api)](https://codecov.io/gh/focusconsulting/pa-compact-licensing-platform)

**Client Coverage**: [![Client Coverage](https://codecov.io/gh/focusconsulting/pa-compact-licensing-platform/branch/main/graph/badge.svg?flag=client)](https://codecov.io/gh/focusconsulting/pa-compact-licensing-platform)

## Repository Structure

```text
engineering/api/                  Python API (FastAPI, Python 3.13)
engineering/client/               Next.js frontend (React, TypeScript, USWDS)
engineering/infrastructure/iac/   Infrastructure as Code (Terraform)
product/                          Product context: flows, evidence, research corpus
```

## Prerequisites

- Install the following using [asdf](https://asdf-vm.com/guide/getting-started.html):

   ```bash
     asdf plugin add python
     asdf install python 3.13.12
     asdf set python 3.13.12

     asdf plugin add nodejs
     asdf install nodejs 25.8.2
     asdf set nodejs 25.8.2

     asdf plugin add uv
     asdf install uv 0.11.2
     asdf set uv 0.11.2

     asdf plugin add just
     asdf install just 1.48.1
     asdf set just 1.48.1

     asdf reshim
     npm install -g pnpm@latest-10
   ```

  - Python 3.13+
  - Node.js 24+
  - [uv](https://docs.astral.sh/uv/) (Python package manager)
  - [pnpm](https://pnpm.io/) 10+
  - [just](https://github.com/casey/just) (task runner)
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
local services, applies migrations, loads the local users, and runs the API
and client. Ctrl-C stops the API and client; `just down` stops the services.
No AWS account or credentials are needed.

| What | Where |
|---|---|
| The app | <http://localhost:3000> |
| API docs | <http://localhost:8000/docs> |
| Email (maildev) | <http://localhost:1080> |
| File storage console (RustFS, `rustfsadmin` / `rustfsadmin`) | <http://localhost:9301> |

Sign in as any user in
[`engineering/mocks/cognito/db/local_licensing.json`](engineering/mocks/cognito/db/local_licensing.json)
with `Local-Passw0rd!`, for example `gustavo.torrico@focusconsulting.io`.
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
from the examples.

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
just dev               # Run API with hot reload (localhost:8000/docs)
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

- **`Input should be 'LOCAL_DEV', 'DEV', 'STAGING' or 'PROD'`** when
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
[`.eslintrc.cjs`](engineering/client/.eslintrc.cjs).
