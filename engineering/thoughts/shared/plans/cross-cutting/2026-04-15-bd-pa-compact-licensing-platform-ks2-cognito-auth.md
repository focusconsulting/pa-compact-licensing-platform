# Cognito Authentication Implementation Plan

## Overview

Add AWS Cognito-based authentication across the full stack: Terraform provisions the User Pool,
FastAPI validates JWTs on every request, and Next.js handles the login flow. Admin users are
pre-seeded via SQL and linked to Cognito by email. The DB schema accommodates state-scoped
permissions, but enforcement is deferred to a later phase.

## Related

- GitHub Issue: N/A
- Beads Task: pa-compact-licensing-platform-ks2
- ADRs: [ADR-0003](../../../docs/architecture_decision_records/0003-users-table-schema-and-auth-design.md)
- **Area**: cross-cutting

## Current State Analysis

- **No auth exists**: no middleware, no user model, no JWT validation anywhere
- **FastAPI** (`api/licensing_api/`): only health routes, two dependencies (DB pool, Redis)
- **Config** (`api/licensing_api/config.py`): DB/Redis/OTEL settings only — no Cognito fields
- **DB schema** (`api/db-migrations/20250402_000000_initial_tables.sql`): empty placeholder
- **Terraform** (`infrastructure/iac/components/app/terraform/`): no Cognito resources; secrets.tf manages DB credentials via Secrets Manager
- **Next.js** (`client/`): static SPA export, USWDS components, no auth library installed

### Key Discoveries:
- `api/licensing_api/dependencies.py` uses typed FastAPI dependencies — auth will slot in cleanly here
- Terraform uses per-env `var.*` pattern; Cognito vars follow the same convention
- `next.config.js` uses `output: "export"` — no server-side API routes; tokens must live client-side
- Secrets Manager already in use for DB creds; Cognito IDs can follow the same pattern

## Desired End State

A request to any protected API endpoint without a valid Cognito token returns 401. A request
with a valid token returns the response with the user's identity available in the handler.
The Next.js app redirects unauthenticated users to `/login`, completes the Cognito PKCE flow,
stores tokens, and attaches the Bearer token to all API calls.

### Key Discoveries:
- Admin users exist in both Cognito (created via admin CLI/console) and the `users` DB table (seeded via SQL), linked by email
- State-scoped permissions need a `state_code` column from day one even if not enforced yet

## What We're NOT Doing

- Self-registration / sign-up flows
- MFA enforcement (Cognito supports it but we won't require it yet)
- Non-admin user types (licensees, state staff, compact admins) — schema ready, not seeded
- State-scoped permission enforcement (schema in place, authz logic deferred)
- Cognito Lambda triggers
- ALB-level auth offload

---

## Phase 1: Terraform — Cognito User Pool

### Overview
Provision the Cognito User Pool and App Client via Terraform so Cognito exists before
the API or frontend can reference it.

### Changes Required:

#### 1. New file: `infrastructure/iac/components/app/terraform/cognito.tf`

```hcl
resource "aws_cognito_user_pool" "main" {
  name = "${var.environment_name}-licensing"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length                   = 12
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  tags = var.tags
}

resource "aws_cognito_user_pool_client" "web" {
  name         = "${var.environment_name}-licensing-web"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret                      = false
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]

  callback_urls = [var.cognito_callback_url]
  logout_urls   = [var.cognito_logout_url]

  supported_identity_providers = ["COGNITO"]

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",   # enables AWS CLI token fetch for local testing
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]
}
```

#### 2. Update `infrastructure/iac/components/app/terraform/variables.tf`

Add:

```hcl
variable "cognito_callback_url" {
  description = "Cognito OAuth callback URL (frontend login redirect)"
  type        = string
}

variable "cognito_logout_url" {
  description = "Cognito logout redirect URL"
  type        = string
}
```

#### 3. Update `infrastructure/iac/components/app/terraform/secrets.tf`

Add a secret to expose Cognito IDs to the API at runtime:

```hcl
resource "aws_secretsmanager_secret" "cognito" {
  name = "${var.environment_name}-cognito-config"
}

resource "aws_secretsmanager_secret_version" "cognito" {
  secret_id = aws_secretsmanager_secret.cognito.id
  secret_string = jsonencode({
    user_pool_id = aws_cognito_user_pool.main.id
    client_id    = aws_cognito_user_pool_client.web.id
    region       = var.aws_region
  })
}
```

#### 4. Update `infrastructure/iac/components/app/terraform/ecs.tf`

Two changes are required so the ECS task can actually read the Cognito secret at startup:

**a) Extend the IAM policy** — `ecs_secrets_policy` originally granted
`secretsmanager:GetSecretValue` only for the DB credentials secret. Add `cognito_config` to the
`Resource` array:

```hcl
{
  Effect = "Allow"
  Action = "secretsmanager:GetSecretValue"
  Resource = [
    aws_secretsmanager_secret.db_credentials.arn,
    aws_secretsmanager_secret.cognito_config.arn,
  ]
},
```

Without this, ECS fails to start the container with an access-denied error when fetching the
Cognito secret.

**b) Wire secrets into the task definition** — add three entries to the `secrets` block of the
API container, using ECS's `ARN:key::` JSON-key extraction syntax:

```hcl
{
  name      = "COGNITO_USER_POOL_ID"
  valueFrom = "${aws_secretsmanager_secret.cognito_config.arn}:user_pool_id::"
},
{
  name      = "COGNITO_CLIENT_ID"
  valueFrom = "${aws_secretsmanager_secret.cognito_config.arn}:client_id::"
},
{
  name      = "COGNITO_REGION"
  valueFrom = "${aws_secretsmanager_secret.cognito_config.arn}:region::"
},
```

These map to the `cognito_user_pool_id`, `cognito_client_id`, and `cognito_region` fields in
`config.py` (pydantic-settings upcases field names to env var names).

> **Re-deployment note**: `terraform apply` creates a new task definition *revision* but the
> ECS service has `ignore_changes = [task_definition]`, so it will not automatically pick up the
> new revision. After apply, force a new deployment:
>
> ```bash
> aws ecs update-service \
>   --cluster <env>-pacompact-app-ecs-cluster \
>   --service <env>-pacompact-app-api-service \
>   --force-new-deployment \
>   --region us-east-1
> ```

#### 6. Add IAM role for Cognito user import to `infrastructure/iac/components/app/terraform/cognito.tf`

```hcl
resource "aws_iam_role" "cognito_user_import" {
  name = "${var.environment_name}-cognito-user-import"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{ Effect = "Allow", Principal = { Service = "cognito-idp.amazonaws.com" }, Action = "sts:AssumeRole" }]
  })
}

resource "aws_iam_role_policy" "cognito_user_import_logs" {
  name = "cloudwatch-logs"
  role = aws_iam_role.cognito_user_import.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:DescribeLogGroups",
                  "logs:DescribeLogStreams", "logs:PutLogEvents", "logs:GetLogEvents", "logs:FilterLogEvents"]
      Resource = "arn:aws:logs:${data.aws_region.current.name}:*:log-group:/aws/cognito/*"
    }]
  })
}
```

#### 7. Add outputs to `infrastructure/iac/components/app/terraform/outputs.tf`

```hcl
output "cognito_user_pool_id"         { value = aws_cognito_user_pool.main.id }
output "cognito_client_id"            { value = aws_cognito_user_pool_client.web.id }
output "cognito_user_import_role_arn" { value = aws_iam_role.cognito_user_import.arn }
```

### Success Criteria:

#### Automated Verification:
- [x] `cd infrastructure/iac/components/app/terraform && terraform validate`
- [x] `terraform fmt -check`
- [x] `terraform plan` shows Cognito resources without errors (in DEV)

#### Manual Verification:
- [x] After `terraform apply`, User Pool visible in AWS Console → Cognito → User Pools
- [x] App Client has no secret, code flow enabled, callback URLs correct
- [x] In AWS Console → Secrets Manager, secret `<env>-cognito-config` exists and its value
  contains the correct `user_pool_id`, `client_id`, and `region`

---

## Phase 2: DB Schema — Users Table

### Overview
Create the `users` table that maps email → role/state, and document the seed SQL for admins.

### Design Decisions

See [ADR-0003](../../../docs/architecture_decision_records/0003-users-table-schema-and-auth-design.md)
for the rationale behind: `BIGSERIAL` vs UUID primary keys, the `created_by` audit trail
pattern, the `public_id UUID` Cognito identity column, and the decision not to cache auth
lookups in Redis.

> **Assumption**: `compact_admin` is also allowed `NULL state_code`. If only `admin` should
> allow `NULL`, change the constraint to `CHECK (state_code IS NOT NULL OR role = 'admin')`.

### Changes Required:

#### 1. New file: `api/db-migrations/20260415_091700_user_table.sql`

```sql
-- Migration: user role tables
-- Created: 2026-04-15

CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    public_id     UUID UNIQUE,              -- Cognito 'sub' claim (always UUID v4); NULL until first login
    given_name    TEXT,                     -- Cognito 'given_name' standard attribute
    family_name   TEXT,                     -- Cognito 'family_name' standard attribute
    role          TEXT NOT NULL,
    state_code    CHAR(2),
    is_active     BOOLEAN NOT NULL DEFAULT TRUE,
    created_by    BIGINT NOT NULL REFERENCES users(id) DEFERRABLE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_users_role
        CHECK (role IN ('admin', 'state_staff', 'compact_admin', 'licensee')),
    CONSTRAINT chk_users_state_code
        CHECK (state_code IS NOT NULL OR role IN ('admin', 'compact_admin'))
);

CREATE INDEX idx_users_email     ON users(email);
CREATE INDEX idx_users_public_id ON users(public_id);
```

#### 2. Seed Cognito users via CSV import

Cognito supports bulk user creation via a CSV import job. This creates the Cognito accounts
that correspond to the rows inserted in Step 3. The emails must match exactly.

**Do not create the CSV file in the repository** — it contains real admin email addresses.
Prepare it locally and discard after the import completes.

**CSV structure:**

```
given_name,family_name,email,cognito:username,email_verified,cognito:mfa_enabled,profile,address,birthdate,gender,preferred_username,updated_at,website,picture,phone_number,phone_number_verified,zoneinfo,locale,middle_name,name,nickname
Jane,Doe,admin1@example.com,admin1@example.com,TRUE,FALSE,,,,,,,,,,,,,,,
John,Smith,admin2@example.com,admin2@example.com,TRUE,FALSE,,,,,,,,,,,,,,,
Alice,Jones,admin3@example.com,admin3@example.com,TRUE,FALSE,,,,,,,,,,,,,,,
```

**Column notes:**
- `given_name` / `family_name` — set at import time; backfilled into the DB `users` row on first login via `COALESCE` in `get_current_user`. Not guaranteed present from all future IdPs — see ADR-0003
- `email` — must match the email in the DB `users` seed exactly
- `cognito:username` — must match `email`; the User Pool uses email as the username attribute
- `email_verified` — `TRUE`; prevents Cognito from sending verification emails to imported users
- `cognito:mfa_enabled` — `FALSE`; MFA is not enforced at this stage
- All remaining columns — leave empty (nullable); Cognito accepts the column headers but does not require values
- No password column — Cognito sends each user a temporary password by email; they must change it on first login (`NEW_PASSWORD_REQUIRED` challenge)
- The AWS import will fail if the number of columns does not match, ensure you have the same number of columns by counting commas: `awk '{ print gsub(/,/, "") }' admins.csv`

**Import steps** (AWS Console):

1. Navigate to **AWS Console → Cognito → User Pools → `<env>-licensing` → Users tab**
2. Click **Import users**
3. Under **CloudWatch logging**, select the existing IAM role
   **`<env>-cognito-user-import`** (created by Terraform in Phase 1).
4. Under **Upload CSV**, click **Choose file** and select your locally prepared CSV.
5. Click **Create import job** — the job is created but not yet running.
6. On the import job detail page, click **Start** to begin the import.
7. Refresh the page until the status shows **Succeeded**. If it shows **Failed**, open the
   linked CloudWatch log group to see which rows were rejected and why.
8. Confirm the users exist: go back to **Users tab** and verify each admin email appears
   with status **FORCE_CHANGE_PASSWORD** (expected — they will change it on first login).

#### 3. Admin seed SQL (documented — do not create a file; apply manually)

The implementer should run this SQL directly against the target database.
Cognito accounts must be created separately with matching emails before or after seeding —
order doesn't matter since the link is by email at login time.

Replace the placeholder emails with real admin emails before running.

```sql
-- Seed initial admin users.
-- The created_by FK is DEFERRABLE (INITIALLY IMMEDIATE). Since it's declared
-- inline (no named constraint), we defer ALL deferrable constraints for this
-- transaction only. The constraint is checked at COMMIT, by which point id=1 exists.
BEGIN;

SET CONSTRAINTS users_created_by_fkey DEFERRED;

INSERT INTO users (email, role, state_code, is_active, created_by)
VALUES
    ('admin1@example.com', 'admin', NULL, TRUE, 1),
    ('admin2@example.com', 'admin', NULL, TRUE, 1),
    ('admin3@example.com', 'admin', NULL, TRUE, 1);

SET CONSTRAINTS users_created_by_fkey IMMEDIATE;

COMMIT;
```

> **Note on id=1**: With `BIGSERIAL`, the first row inserted into a fresh `users` table gets
> `id = 1`. The seed assumes a pristine database. If other rows were inserted earlier (e.g.,
> in a previous failed migration), use `SELECT currval('users_id_seq')` after the first INSERT
> to get the actual ID before committing, or restructure with a CTE.

### Success Criteria:

#### Manual Verification:
- [x] Cognito import job status is `Succeeded`; each admin email visible in User Pool via AWS Console → Cognito → User Pools → Users
- [x] Launch api locally using `just dev` and ensure migrations run
- [x] Seed SQL runs inside a transaction without error on a fresh DB
- [x] Attempt to insert a `state_staff` row with `state_code = NULL` → constraint violation
- [x] Attempt to insert an `admin` row with `state_code = NULL` → succeeds

---

## Phase 3: FastAPI — JWT Validation & Auth Dependencies

### Overview
Add Cognito JWT verification, a standardised error response shape, and a `get_current_user`
dependency that routes can use.

### Changes Required:

#### 1. Update `api/pyproject.toml` and `api/README.md`

Move `httpx` from dev to production dependencies and add `python-jose[cryptography]`:

```toml
# api/pyproject.toml — production dependencies
"python-jose[cryptography]>=3.5.0",
"httpx>=0.28.1",
```

Add both to the key dependencies table in `api/README.md`:
- `python-jose[cryptography]` — JWT validation (Cognito ID tokens)
- `httpx` — HTTP client (JWKS fetching)

#### 2. Update `api/licensing_api/config.py`

Add Cognito settings, a `cors_origins` list, a derived `cognito_jwks_url` property, and a
`get_settings()` accessor (needed so FastAPI `Depends()` can use it as a proper dependency
rather than reading the module-level singleton directly):

```python
cognito_user_pool_id: str = 'invalid'
cognito_region: str = 'us-east-1'
cognito_client_id: str = 'invalid'

cors_origins: list[str] = ['http://localhost:3000']

@property
def cognito_jwks_url(self) -> str:
    return (
        f'https://cognito-idp.{self.cognito_region}.amazonaws.com'
        f'/{self.cognito_user_pool_id}/.well-known/jwks.json'
    )


settings = Settings()


def get_settings() -> Settings:
    return settings
```

#### 3. New file: `api/licensing_api/errors.py`

Standardised error contract used by all endpoints. All application errors raise `AppError`;
FastAPI's own exceptions and validation errors are caught and reformatted by the handlers
registered in `__main__.py`.

```python
from enum import StrEnum

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ErrorCode(StrEnum):
    InvalidToken    = 'INVALID_TOKEN'
    UserNotFound    = 'USER_NOT_FOUND'
    UserInactive    = 'USER_INACTIVE'
    ValidationError = 'VALIDATION_ERROR'
    HttpError       = 'HTTP_ERROR'


class ErrorResponse(BaseModel):
    code: ErrorCode
    details: list[str]


class AppError(HTTPException):
    def __init__(self, status_code: int, code: ErrorCode, details: list[str]) -> None:
        super().__init__(status_code=status_code)
        self.code = code
        self.details = details


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(code=exc.code, details=exc.details).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(code=ErrorCode.HttpError, details=[detail]).model_dump(),
        headers=getattr(exc, 'headers', None),
    )


async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(code=ErrorCode.ValidationError, details=details).model_dump(),
    )
```

#### 4. New file: `api/licensing_api/auth.py`

**JWKS caching**: `_get_jwks` takes the JWKS URL as an argument so `lru_cache` keys on it.
Each Gunicorn/uvicorn worker fetches the keys once on first use. Cognito keys rarely rotate
so this is safe. Does not import from `dependencies.py` — defines its own `_get_db_pool`
inline to avoid a circular import (`dependencies.py` previously had aliases that imported
from `auth.py`; those aliases were removed, so no circular dependency exists today).

**User lookup**: Plain `SELECT` — no Redis caching, no UPDATE backfill. The indexed lookup
is negligible at this scale, and immediate deactivation (no stale cache) matters more.

**`CurrentUser`**: Pydantic `BaseModel` (not a dataclass) so FastAPI serialises it directly
from route return annotations and documents it in OpenAPI.

```python
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import asyncpg
import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from licensing_api.config import Settings, get_settings
from licensing_api.errors import AppError, ErrorCode

_bearer = HTTPBearer()


class CurrentUser(BaseModel):
    id: int
    email: str
    public_id: UUID | None
    given_name: str | None
    family_name: str | None
    role: str
    state_code: str | None
    is_active: bool


def _get_db_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.db_pool


@lru_cache
def _get_jwks(jwks_url: str) -> dict:
    """Fetch and cache Cognito JWKS. Cached per worker process."""
    with httpx.Client(timeout=10) as client:
        response = client.get(jwks_url)
        response.raise_for_status()
    return response.json()


def _verify_token(token: str, settings: Settings) -> dict:
    """Validate a Cognito ID token and return its claims."""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise AppError(401, ErrorCode.InvalidToken, ['Invalid token format']) from e

    jwks = _get_jwks(settings.cognito_jwks_url)
    kid = unverified_header.get('kid')
    key = next((k for k in jwks['keys'] if k['kid'] == kid), None)
    if key is None:
        raise AppError(401, ErrorCode.InvalidToken, ['Unknown signing key'])

    try:
        claims = jwt.decode(token, key, algorithms=['RS256'], audience=settings.cognito_client_id)
    except JWTError as e:
        raise AppError(401, ErrorCode.InvalidToken, ['Token validation failed']) from e

    if claims.get('token_use') != 'id':
        raise AppError(401, ErrorCode.InvalidToken, ['Expected Cognito ID token'])

    return claims


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[asyncpg.Pool, Depends(_get_db_pool)],
) -> CurrentUser:
    claims = _verify_token(credentials.credentials, settings)
    row = await db.fetchrow(
        'SELECT id, email, public_id, given_name, family_name, role, state_code, is_active '
        'FROM users WHERE email = $1',
        claims['email'],
    )
    if row is None:
        raise AppError(403, ErrorCode.UserNotFound, ['User not found'])
    if not row['is_active']:
        raise AppError(403, ErrorCode.UserInactive, ['User is inactive'])
    return CurrentUser(**dict(row))
```

#### 5. Update `api/licensing_api/dependencies.py`

Remove all type aliases (`DbPool`, `RedisCli` and any auth aliases). Keep only the two raw
getter functions — routes use `Annotated[T, Depends(getter)]` inline. This avoids the
circular import that aliases created when `auth.py` needed to import from `dependencies.py`:

```python
import asyncpg
import redis.asyncio as aioredis
from fastapi import Request


def get_db_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.db_pool


def get_redis(request: Request) -> aioredis.Redis:
    return request.app.state.redis
```

Update `api/licensing_api/routes/health.py` to use inline `Annotated[..., Depends(...)]`
now that the aliases are gone.

#### 6. New file: `api/licensing_api/routes/user.py`

No route prefix — mounts at `/api/me` via the top-level `api_router`. Returns `CurrentUser`
directly so FastAPI documents the response schema in OpenAPI:

```python
from typing import Annotated
from fastapi import APIRouter, Depends
from licensing_api.auth import CurrentUser, get_current_user

router = APIRouter()

@router.get('/me', name='Get current user')
async def get_me(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    return user
```

#### 7. Update `api/licensing_api/__main__.py`

Add CORS middleware, register exception handlers, and wire the user router:

```python
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from licensing_api.errors import AppError, app_error_handler, http_exception_handler, validation_error_handler
from licensing_api.routes import health, user

# after app creation:
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

api_router.include_router(health.router)
api_router.include_router(user.router)
```

#### 8. Update `api/.env.example`

```
COGNITO_USER_POOL_ID='us-east-1_xxxxxxxxx'
COGNITO_REGION='us-east-1'
COGNITO_CLIENT_ID='xxxxxxxxxxxxxxxxxxxxxxxxxx'

# JSON list of allowed CORS origins
# TODO will need to populate this in terraform after PR 26
CORS_ORIGINS='["http://localhost:3000"]'
```

#### 9. New file: `api/tests/test_user.py`

Tests use a real RSA key pair generated in a module-scoped fixture to mint signed JWTs.
`_get_jwks` is patched to return the matching public key (avoids HTTP to Cognito).
`get_settings` is overridden via `app.dependency_overrides` — necessary because
`Depends(get_settings)` stores the function object at import time, so `unittest.mock.patch`
on the module name cannot intercept it.

Four cases: happy path, unknown email (403 `USER_NOT_FOUND`), inactive user
(403 `USER_INACTIVE`), malformed JWT (401 `INVALID_TOKEN`).

### Success Criteria:

#### Automated Verification:
- [x] `cd api && uv run pyright licensing_api`
- [x] `cd api && uv run ruff check licensing_api tests`
- [x] `cd api && uv run pytest`

#### Manual Verification:
- [x] `curl -X GET http://localhost:8000/api/me` → 401 with `{"code":"INVALID_TOKEN",...}`
- [ ] Obtain a Cognito ID token via the AWS CLI:

  CSV-imported users land in `RESET_REQUIRED` status — no password was ever set, so
  `initiate-auth` throws `PasswordResetRequiredException` rather than returning a challenge.
  The simplest fix is to set a permanent password directly as an admin, which bypasses the
  reset requirement:

  ```bash
  aws cognito-idp admin-set-user-password \
    --user-pool-id <user_pool_id> \
    --username <admin-email> \
    --password <new-password> \
    --permanent \
    --region us-east-1
  ```

  Then `initiate-auth` works normally:

  ```bash
  aws cognito-idp initiate-auth \
    --auth-flow USER_PASSWORD_AUTH \
    --client-id <cognito_client_id> \
    --auth-parameters USERNAME=<admin-email>,PASSWORD=<new-password> \
    --region us-east-1 \
    --query 'AuthenticationResult.IdToken' \
    --output text
  ```

  > **Note**: `RESET_REQUIRED` is specific to CSV-imported users (no password was ever set).
  > Users created via `admin-create-user` get a temporary password and land in
  > `FORCE_CHANGE_PASSWORD` status instead, which returns a `NEW_PASSWORD_REQUIRED` challenge
  > on `initiate-auth` — a different flow requiring `respond-to-auth-challenge`.
- [x] With the token:

  ```bash
  curl -H "Authorization: Bearer <id_token>" http://localhost:8000/api/me
  ```

  → 200 with `CurrentUser` JSON (`email`, `role`, `given_name`, `family_name`, etc.)

---

## Phase 4: Next.js — Auth Flow

### Overview
Add Cognito SRP login flow to the SPA: login page, auth context, protected route wrapper,
API fetch wrapper, dev proxy, and USWDS asset handling.

### Changes Required:

#### 1. Add dependency

```bash
cd client && pnpm add amazon-cognito-identity-js
```

#### 2. Replace `client/.env.development` with `client/.env.example`

`.env.development` was removed from the repo and replaced with `.env.example` (committed)
so that real environment values are never tracked in git. Each developer copies `.env.example`
to `.env.development` locally and fills in their values.

```
NEXT_PUBLIC_BASE_PATH=

NEXT_PUBLIC_COGNITO_USER_POOL_ID=
NEXT_PUBLIC_COGNITO_CLIENT_ID=
NEXT_PUBLIC_COGNITO_REGION=us-east-1
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

#### 3. New file: `client/src/lib/auth.ts`

Cognito pool + `signIn()`, `completeNewPassword()`, `signOut()`, `getCurrentSession()`.

`CognitoUserPool` is **lazily initialised** (not module-level). Next.js pre-renders all pages
— including `'use client'` pages — in Node.js during `next build`. A module-level
`new CognitoUserPool(...)` runs at that point with undefined env vars and throws
`Both UserPoolId and ClientId are required`. Lazy init defers construction until the first
browser call.

```typescript
let _userPool: CognitoUserPool | null = null;

function getUserPool(): CognitoUserPool {
  if (!_userPool) {
    _userPool = new CognitoUserPool({
      UserPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID!,
      ClientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID!,
    });
  }
  return _userPool;
}
```

`signIn` returns a discriminated union:
```typescript
export type SignInResult =
  | { type: "success"; session: CognitoUserSession }
  | { type: "newPasswordRequired"; user: CognitoUser; userAttributes: Record<string, string> };
```

#### 4. New file: `client/src/contexts/AuthContext.tsx`

React context exposing `{ isLoading, idToken, email, signIn, completeNewPassword, signOut }`.

On mount, calls `getCurrentSession()` to restore the session from tokens the Cognito SDK
persists in `localStorage`. The ID token and email live in React state (cleared on tab close);
the refresh token lives in `localStorage` (allows session restoration across page reloads).

#### 5. New file: `client/src/lib/api.ts`

Calls `getCurrentSession()` directly (not via context) to get the current ID token, then
attaches it as a `Bearer` header. `NEXT_PUBLIC_API_BASE_URL` is prepended to the path; in
production this is the API's public URL. In development the dev proxy (see below) intercepts
`/api/*` before it reaches the network, so the base URL value doesn't matter for local work.

```typescript
export async function authFetch(path: string, options?: RequestInit): Promise<Response> {
  const session = await getCurrentSession();
  if (!session) throw new Error("Not authenticated");
  const token = session.getIdToken().getJwtToken();
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  return fetch(`${baseUrl}${path}`, {
    ...options,
    headers: { ...options?.headers, Authorization: `Bearer ${token}` },
  });
}
```

#### 6. New file: `client/src/app/login/page.tsx`

Email + password form using `@trussworks/react-uswds` (Form, Label, TextInput, Button, Alert).
After a successful `signIn` that returns `newPasswordRequired`, switches to a set-new-password
form. Uses `completeNewPassword` to complete the challenge, then redirects to `/`.

#### 7. New file: `client/src/components/ProtectedRoute.tsx`

`useEffect` redirects to `/login` when `!isLoading && !idToken`. Returns `null` while loading
or unauthenticated to avoid a flash of protected content.

#### 8. Update `client/src/app/layout.tsx`

Wrap `{children}` in `<AuthProvider>`.

#### 9. Update `client/src/app/page.tsx`

After sign-in, the dashboard calls `authFetch('/api/me')` and displays the `CurrentUser`
record (name, email, role, state, active status) in a USWDS borderless table.

#### 10. Update `client/next.config.js` — dev proxy + conditional static export

`output: "export"` prevents rewrites from being defined (Next.js throws at build time).
Apply `output` only in production; in development omit it and add a rewrite that proxies
`/api/*` to the FastAPI backend:

```js
const isDev = process.env.NODE_ENV !== "production";

const nextConfig = {
  ...(isDev ? {} : { output: "export" }),
  async rewrites() {
    if (!isDev) return [];
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${apiBase}/api/:path*` }];
  },
  // ...
};
```

#### 11. Update `client/package.json` — USWDS asset copy

USWDS fonts and images must be served at `/uswds/fonts/` and `/uswds/img/` (paths baked into
the compiled CSS via `$theme-font-path`). Copy them from `node_modules` on install rather than
tracking them in git:

```json
"copy-uswds-assets": "cp -r node_modules/@uswds/uswds/dist/fonts public/uswds/fonts && cp -r node_modules/@uswds/uswds/dist/img public/uswds/img",
"postinstall": "mkdir -p public/uswds && pnpm run copy-uswds-assets",
```

Add `/public/uswds/` to `client/.gitignore`.

#### 12. Update `infrastructure/iac/components/app/terraform/cognito.tf`

Add `ALLOW_USER_SRP_AUTH` to the App Client's `explicit_auth_flows`.
`amazon-cognito-identity-js` uses SRP auth by default; without this the browser gets
`USER_SRP_AUTH is not enabled for the client`:

```hcl
explicit_auth_flows = [
  "ALLOW_USER_SRP_AUTH",      # used by amazon-cognito-identity-js in the browser
  "ALLOW_USER_PASSWORD_AUTH", # enables AWS CLI token fetch for local testing
  "ALLOW_REFRESH_TOKEN_AUTH",
]
```

**Token storage:**
- ID token + access token: React state (memory only, cleared on tab close)
- Refresh token: `localStorage` via the Cognito SDK (allows session restoration across reloads)

### Success Criteria:

#### Automated Verification:
- [x] `cd client && pnpm tsc --noEmit`
- [x] `cd client && pnpm lint`
- [x] `cd client && pnpm build`
- [x] `terraform apply` shows in-place update to Cognito App Client only

#### Manual Verification:
- [x] Navigate to a protected page → redirect to `/login`
- [x] Log in with a seeded admin account → redirect to dashboard, user details from `/api/me` displayed
- [x] Refresh the page → session restored from refresh token, no re-login required
- [x] Sign out → token cleared, protected page redirects to `/login`

---

## Testing Strategy

### API Tests (`api/tests/test_user.py`):
- Malformed JWT → 401 `INVALID_TOKEN` (fails at header parse, before JWKS is consulted)
- Valid token, email not in DB → 403 `USER_NOT_FOUND`
- Valid token, user `is_active = FALSE` → 403 `USER_INACTIVE`
- Valid token, active user → 200 with `CurrentUser` shape

Tests sign real JWTs with a generated RSA key pair. `_get_jwks` is patched to return the
matching public JWKS. `get_settings` is overridden via `app.dependency_overrides` (not
`patch`) because `Depends()` captures the function object at import time.

### Integration Tests:
- Full login → token → `/api/me` using a real Cognito pool in a staging environment

### Manual Testing Steps:
1. Seed admin users in Cognito via CSV import (Phase 2) and in the DB via seed SQL
2. Obtain an ID token via `aws cognito-idp initiate-auth` (handle `NEW_PASSWORD_REQUIRED` on first login)
3. `curl -H "Authorization: Bearer <token>" http://localhost:8000/api/me` → 200
4. Log in from the Next.js frontend (Phase 4), confirm redirect and token storage
5. Log out, confirm token cleared, protected page redirects to `/login`

## Migration Notes

- Cognito users must be created with matching emails before or after seeding — the link is resolved at login time
- First-login requires a password change — the login page must handle the `NEW_PASSWORD_REQUIRED` challenge
- `_get_jwks()` is cached with `lru_cache` per worker process; a rolling restart clears it if Cognito ever rotates keys (rare)

## References

- Beads task: pa-compact-licensing-platform-ks2
- FastAPI dependencies pattern: `api/licensing_api/dependencies.py`
- Terraform secrets pattern: `infrastructure/iac/components/app/terraform/secrets.tf`
- Next.js app entry: `client/src/app/layout.tsx`
