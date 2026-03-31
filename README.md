# PA Compact Licensing Platform

## Repository Structure

```text
api/          Python API (Connexion/Flask, Python 3.13)
client/       Next.js frontend (React, TypeScript, USWDS)
iac/          Infrastructure as Code
```

## Prerequisites

- Python 3.13+
- Node.js 24+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [pnpm](https://pnpm.io/) 10+
- [just](https://github.com/casey/just) (task runner)
- Docker (for containerized linting and builds)

## Getting Started

### API

```bash
cd api
just install     # Install Python dependencies
just dev         # Run API with hot reload (localhost:8000)
```

### Client

```bash
cd client
pnpm install     # Install Node dependencies
pnpm dev         # Run dev server
```

## Development

### API Commands

```bash
just test              # Run tests
just test-coverage     # Run tests with coverage
just lint              # Run all linting (spectral + ruff + pyright)
just format            # Format code
just build             # Build production Docker image
```

### Client Commands

```bash
pnpm test              # Run tests (vitest)
pnpm lint              # Lint
pnpm storybook         # Run Storybook
pnpm build             # Production build
```
