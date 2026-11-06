# The whole system, run locally with no AWS account. See "Run the whole system
# locally" in README.md. Per-app commands live in engineering/api/justfile and
# engineering/client/package.json.

compose := "docker compose -p pa-compact -f engineering/api/docker-compose.yaml"

# Show available commands
default:
    @just --list

# Start everything: local services, migrations, seed data, then the API, Worker, and client (Ctrl-C stops them)
up: install services
    cd engineering/api && just migrate && just seed
    trap 'kill 0' EXIT; (cd engineering/api && just dev) & (cd engineering/api && just worker) & (cd engineering/client && pnpm dev) & wait

# Install API and client dependencies, and create local settings files from the examples if missing
install:
    test -f engineering/api/.env || cp engineering/api/.env.example engineering/api/.env
    test -f engineering/client/.env || cp engineering/client/.env.example engineering/client/.env
    cd engineering/api && uv sync
    cd engineering/client && pnpm install

# Start the local services in the background (Postgres, maildev, RustFS, Cognito mock) and wait until ready
services:
    {{ compose }} up -d --wait --build
    {{ compose }} run --rm rustfs-init >/dev/null

# Stop the local services
down:
    {{ compose }} down

# Load local seed data from engineering/api/seed/: `users` (safe to rerun), or `demo` (docs/demo.md)
seed name="users":
    cd engineering/api && just seed {{ name }}

# Regenerate the API document, then the client's types from it
generate:
    cd engineering/api && just openapi
    cd engineering/client && pnpm generate

# Answer the API's routes with the examples in openapi.json on port 4010 (ADR-0013); any bearer token passes.
# Point the client at it with NEXT_PUBLIC_API_BASE_URL=http://localhost:4010. The image is amd64-only, and
# `-m false` avoids Prism 5.15's multi-process start, which fails on its bundled Node.
mock-api:
    docker run --rm --init --platform linux/amd64 -p 4010:4010 \
        -v "$PWD/engineering/api/openapi.json:/openapi.json:ro" \
        stoplight/prism:5.15.10 mock -m false -h 0.0.0.0 /openapi.json

# Run the end-to-end tests against the running system (start it with `just up` first)
e2e:
    cd engineering/e2e && pnpm install && pnpm exec playwright install chromium && pnpm test

# Everything CI checks, for the API, client, and e2e specs (the API's tests need `just services`)
check:
    cd engineering/api && just check
    cd engineering/client && pnpm check
    cd engineering/e2e && pnpm typecheck

# Scanner versions. CI's security workflow runs these recipes, so a local run checks what a pull request will.
trivy := "docker run --rm -v trivy-cache:/root/.cache -v /var/run/docker.sock:/var/run/docker.sock -v " + justfile_directory() + ":/repo -w /repo aquasec/trivy:0.76.1"
gitleaks := "docker run --rm -v " + justfile_directory() + ":/repo ghcr.io/gitleaks/gitleaks:v8.30.1"
pip_audit := "uvx pip-audit==2.10.1"
checkov := "uvx checkov==3.3.30"
reports := "security-reports"

# Every scan that fails a pull request on a medium, high, or critical finding (CodeQL runs only in CI)
security: audit-api audit-client scan-image scan-secrets

# Known vulnerabilities in the API's locked dependencies, dev tools included
audit-api:
    cd engineering/api && uv export --frozen --all-groups --no-hashes --no-emit-project --quiet \
        | {{ pip_audit }} --requirement /dev/stdin --disable-pip --no-deps --progress-spinner off

# Known vulnerabilities in the client's and the end-to-end specs' locked dependencies, dev tools included
audit-client:
    cd engineering/client && pnpm audit --audit-level moderate
    cd engineering/e2e && pnpm audit --audit-level moderate

# Build the API's production image and scan its OS and Python packages
scan-image:
    docker build --quiet --target app -t licensing-api:security engineering/api
    {{ trivy }} image --quiet --severity MEDIUM,HIGH,CRITICAL --exit-code 1 licensing-api:security

# Secrets anywhere in the git history
scan-secrets:
    {{ gitleaks }} git /repo --redact --no-banner

# Checkov over the OpenTofu, workflows, and Dockerfiles: reported, never failing, until SCRUM-84 hardens the infrastructure
scan-iac:
    {{ checkov }} --directory . --framework terraform github_actions dockerfile \
        --skip-path node_modules --skip-path .terraform --soft-fail --compact --quiet --output github_failed_only

# CycloneDX SBOMs of the API image and the client's shipped dependencies, and the third-party register from them (needs `scan-image` and the client's node_modules)
sbom:
    mkdir -p {{ reports }}
    {{ trivy }} image --quiet --format cyclonedx --output {{ reports }}/api.cdx.json licensing-api:security
    {{ trivy }} fs --quiet --format cyclonedx --output {{ reports }}/client.cdx.json engineering/client
    python3 scripts/security/third-party-register.py {{ reports }}/third-party-register.md \
        "API image={{ reports }}/api.cdx.json" "Client={{ reports }}/client.cdx.json"
