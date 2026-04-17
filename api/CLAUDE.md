# Project Instructions for AI Agents

This file provides instructions and context for AI coding agents working on this project.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:ca08a54f -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

## Session Completion

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd dolt push
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
<!-- END BEADS INTEGRATION -->


## Build & Test

```bash
just test
# for checking coverage
just test-coverage
```

## Architecture Overview

FastAPI application served by Uvicorn/Gunicorn, targeting Python 3.13.

**Request lifecycle:**
1. `CORSMiddleware` → `UnhandledExceptionMiddleware` → `RequestLoggingMiddleware` (registered outermost-first, executed innermost-first)
2. FastAPI exception handlers normalize `AppError`, `HTTPException`, and `RequestValidationError` into `{"code": "...", "details": [...]}` JSON responses
3. Secured routes inject `get_auth_claims` (validates a Cognito ID token via JWKS, returns `AuthClaims(sub: UUID, email: str)`)

**Layers (one file per resource):**
- `routes/` — HTTP handlers; own request/response Pydantic models for OpenAPI docs
- `repo/` — async DB query functions (SQLModel + asyncpg); accept plain values, return model instances
- `migrations.py` — programmatic yoyo migrations run at startup

**Backing services:**
- PostgreSQL — primary store; async via asyncpg/SQLModel
- Redis — available via `get_redis` dependency; currently used for health checks, intended for permission caching keyed on `AuthClaims.sub`
- AWS Cognito — identity provider; tokens validated with `python-jose` against the pool's JWKS endpoint

**Observability:** structured JSON logs (all app + Uvicorn output); OpenTelemetry traces exported via OTLP/gRPC.

## Conventions & Patterns

- All endpoints with response bodies must return pydantic models so they are
  clearly documented in OpenAPI.
- The annotations marking functions as endpoints must contain name and description
- When adding a dependency, list its documentation page in README.md, follow the
    pattern there.
- Flag places where people are querying for serial user.id by using
    AuthClaim.sub for the purpose of updating audit columns. Prefer sub-queries
    to avoid an extra roundtrip to the database.
