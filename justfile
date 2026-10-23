# The whole system, run locally with no AWS account. See "Run the whole system
# locally" in README.md. Per-app commands live in engineering/api/justfile and
# engineering/client/package.json.

compose := "docker compose -p pa-compact -f engineering/api/docker-compose.yaml"

# Show available commands
default:
    @just --list

# Start everything: local services, migrations, seed data, then the API and client (Ctrl-C stops both)
up: install services
    cd engineering/api && just migrate && just seed
    trap 'kill 0' EXIT; (cd engineering/api && just dev) & (cd engineering/client && pnpm dev) & wait

# Install API and client dependencies, and create local settings files from the examples if missing
install:
    test -f engineering/api/.env || cp engineering/api/.env.example engineering/api/.env
    test -f engineering/client/.env || cp engineering/client/.env.example engineering/client/.env
    cd engineering/api && uv sync
    cd engineering/client && pnpm install

# Start the local services in the background (Postgres, maildev, RustFS, Cognito mock) and wait until ready
services:
    {{ compose }} up -d --wait --build
    {{ compose }} wait rustfs-init >/dev/null

# Stop the local services
down:
    {{ compose }} down

# Load local seed data from engineering/api/seed/: `users` (safe to rerun), or `demo` (docs/demo.md)
seed name="users":
    cd engineering/api && just seed {{ name }}

# Regenerate the API document, then the client's types and mocks from it
generate:
    cd engineering/api && just openapi
    cd engineering/client && pnpm generate

# Run the end-to-end tests against the running system (start it with `just up` first)
e2e:
    cd engineering/e2e && pnpm install && pnpm exec playwright install chromium && pnpm test

# Everything CI checks, for the API, client, and e2e specs (the API's tests need `just services`)
check:
    cd engineering/api && just check
    cd engineering/client && pnpm check
    cd engineering/e2e && pnpm typecheck
