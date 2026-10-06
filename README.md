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
- Docker, running (local Postgres and Redis for the API, and image builds)
- [pre-commit](https://pre-commit.com/) (`pipx install pre-commit` or `brew install pre-commit`)

## Pre-commit hooks

Install once after cloning:

```bash
pre-commit install           # sets up the git hook
pre-commit install-hooks     # pre-fetch hook environments
```

Hooks run automatically on `git commit`. To run them on demand:

```bash
pre-commit run --all-files   # lint the whole repo
pre-commit run               # lint staged files only
```

Hooks include: ruff (Python lint + format), gitleaks (secret detection),
markdownlint, and generic file checks (trailing whitespace, EOF, merge
conflicts, large files, YAML/JSON validity). The same hooks run in CI via
`.github/workflows/lint.yml`.

## Getting Started

### API

```bash
cd engineering/api
export UV_PYTHON=$(asdf which python) # use the python from asdf
cp .env.example .env   # local settings; works as-is with `just infra`
just install           # Install Python dependencies
just infra             # Start Postgres and Redis (resets their data)
just dev               # Run API with hot reload (localhost:8000/docs)
```

`just test` also needs `just infra` running.

### Client

```bash
cd engineering/client
cp .env.example .env.local   # public settings only, no secrets
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
just infra             # Start Postgres and Redis
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
pnpm test              # Run tests (vitest)
pnpm lint              # Lint
pnpm storybook         # Run Storybook
pnpm build             # Production build
```
