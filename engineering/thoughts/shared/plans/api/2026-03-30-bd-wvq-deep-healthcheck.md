# Deep Healthcheck: PostgreSQL + Redis Implementation Plan

## Overview

Update the `GET /v1/health/deep` endpoint to probe both PostgreSQL and Redis independently, reporting per-component `"up"/"down"` status and an overall status that reflects the worst case. If any component is down, the endpoint returns HTTP 503 with `status: "down"`.

## Related

- Beads Task: pa-compact-licensing-platform-wvq
- **Area**: api

## Current State Analysis

- `health_deep()` (`api/licensing_api/controllers/health.py:9-24`) only checks PostgreSQL via `session.execute(text("SELECT 1;"))` — if it fails, the function raises and Connexion returns a generic 500.
- Redis is available as a singleton at `Cache._client` (`api/licensing_api/cache/__init__.py:61`) and already has `.ping()` used at startup (line 96), but the deep health endpoint doesn't check it.
- The OpenAPI `HealthResponseDeep` schema (`api/openapi.yaml:75-118`) only defines a `db` component under `components`.
- The test (`api/tests/controllers/test_health.py:23-36`) asserts `components: {"db": {"status": "up"}}` only.

### Key Discoveries:
- `Cache.get_cache()` returns the Redis singleton and calls `.ping()` on first init — we can reuse it for the health probe.
- The per-request DB session is injected via `DbSessionMiddleware` and retrieved via `get_request_db_session()` (`api/licensing_api/middleware.py:13`).
- Test fixtures in `api/tests/conftest.py` spin up real PostgreSQL and Redis containers via testcontainers.

## Desired End State

- `GET /v1/health/deep` returns `{"status": "up", ..., "components": {"db": {"status": "up"}, "cache": {"status": "up"}}}` with HTTP 200 when both are healthy.
- When either component is down, the endpoint returns HTTP 503 with the overall `status: "down"` and individual component statuses reflecting which are up/down.
- The OpenAPI spec documents both the 200 and 503 responses with the `cache` component.
- Tests cover: all-healthy, DB-down, Redis-down.

## What We're NOT Doing

- Adding retry logic or circuit breakers to the health probes
- Changing the shallow `GET /v1/health` endpoint
- Adding latency/timing information to component statuses
- Adding health checks for other services beyond PostgreSQL and Redis

## Implementation Approach

Wrap each dependency probe in a try/except within `health_deep()`. Compute overall status from individual results. Use `success_response` for 200 and `error_response` for 503. Import `Cache` to access the Redis client.

## Phase 1: Update OpenAPI Spec

### Overview
Add the `cache` component to the deep health response schema and add a 503 response.

### Changes Required:

#### 1. `api/openapi.yaml` — HealthResponseDeep response
**Changes**: Add `cache` object alongside `db` in the `components` property. Add a `"503"` response referencing the same schema.

```yaml
                      components:
                        type: object
                        properties:
                          db:
                            type: object
                            properties:
                              status:
                                type: string
                                example: up
                          cache:
                            type: object
                            properties:
                              status:
                                type: string
                                example: up
```

Add under the `/health/deep` path responses:
```yaml
        "503":
          $ref: "#/components/responses/HealthResponseDeep"
```

### Success Criteria:

#### Automated Verification:
- [x] Spectral lint passes: `cd api && docker run --rm --cap-drop=ALL --network=none --read-only --volume=$(pwd):/tmp:ro stoplight/spectral:6 lint /tmp/openapi.yaml --ruleset /tmp/.spectral.yaml`

---

## Phase 2: Update Controller

### Overview
Modify `health_deep()` to probe both PostgreSQL and Redis, catch failures per-component, and return appropriate HTTP status.

### Changes Required:

#### 1. `api/licensing_api/controllers/health.py`
**Changes**: Import `Cache` and logging. Wrap DB and Redis probes in try/except. Compute overall status. Return 503 when any component is down.

```python
import datetime
import logging

from sqlalchemy import text

from licensing_api.cache import Cache
from licensing_api.controllers.response import ApiResponse, success_response
from licensing_api.middleware import get_request_db_session

logger = logging.getLogger(__name__)


def health_deep() -> ApiResponse:
    components: dict[str, dict[str, str]] = {}

    # Check PostgreSQL
    try:
        session = get_request_db_session()
        if session is None:
            raise RuntimeError("No database session available")
        session.execute(text("SELECT 1;")).one()
        components["db"] = {"status": "up"}
    except Exception:
        logger.exception("PostgreSQL health check failed")
        components["db"] = {"status": "down"}

    # Check Redis
    try:
        Cache.get_cache().ping()
        components["cache"] = {"status": "up"}
    except Exception:
        logger.exception("Redis health check failed")
        components["cache"] = {"status": "down"}

    all_up = all(c["status"] == "up" for c in components.values())
    overall_status = "up" if all_up else "down"

    payload = {
        "status": overall_status,
        "timestamp": datetime.datetime.now(datetime.UTC),
        "apiName": "api",
        "apiVersion": "v1",
        "components": components,
    }

    status_code = 200 if all_up else 503
    return success_response("Response", payload, status_code=status_code).to_api_response()
```

Note: `error_response` in `response.py` expects an `HTTPException` type and an `errors` list — it's designed for validation errors, not health degradation. Instead, use `success_response` with `status_code=503` since the payload structure is identical and it keeps the response format consistent.

### Success Criteria:

#### Automated Verification:
- [x] Type checking passes: `cd api && uv run pyright licensing_api`
- [x] Linting passes: `cd api && uv run ruff check licensing_api`
- [x] Formatting correct: `cd api && uv run ruff format --check licensing_api`

#### Manual Verification:
- [ ] `curl localhost:8000/v1/health/deep` returns 200 with both `db` and `cache` components `"up"` when services are running
- [ ] Stopping Redis container and hitting the endpoint returns 503 with `cache: {status: "down"}` and `db: {status: "up"}`
- [ ] Stopping PostgreSQL container returns 503 with `db: {status: "down"}`

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 3: Update Tests

### Overview
Update existing test and add tests for degraded scenarios.

### Changes Required:

#### 1. `api/tests/controllers/test_health.py`
**Changes**: Update `test_get_health_deep_endpoint` to expect `cache` component. Add tests for DB-down and Redis-down scenarios using mocking.

```python
@freeze_time("2024-07-26")
def test_get_health_deep_endpoint(self, test_client: connexion.FlaskApp) -> None:
    now = datetime.datetime.now(datetime.UTC)
    response = test_client.get("/v1/health/deep")
    assert response.status_code == 200
    data = response.json()
    assert data["statusCode"] == 200
    assert data["data"] == {
        "status": "up",
        "timestamp": now.isoformat(),
        "apiName": "api",
        "apiVersion": "v1",
        "components": {"db": {"status": "up"}, "cache": {"status": "up"}},
    }

@freeze_time("2024-07-26")
def test_health_deep_db_down(self, test_client: connexion.FlaskApp) -> None:
    """When PostgreSQL is unreachable, returns 503 with db status down."""
    with patch("licensing_api.controllers.health.get_request_db_session") as mock_session:
        mock_session.return_value.execute.side_effect = Exception("connection refused")
        response = test_client.get("/v1/health/deep")
    assert response.status_code == 503
    data = response.json()
    assert data["data"]["status"] == "down"
    assert data["data"]["components"]["db"]["status"] == "down"
    assert data["data"]["components"]["cache"]["status"] == "up"

@freeze_time("2024-07-26")
def test_health_deep_redis_down(self, test_client: connexion.FlaskApp) -> None:
    """When Redis is unreachable, returns 503 with cache status down."""
    with patch("licensing_api.controllers.health.Cache") as mock_cache:
        mock_cache.get_cache.return_value.ping.side_effect = Exception("connection refused")
        response = test_client.get("/v1/health/deep")
    assert response.status_code == 503
    data = response.json()
    assert data["data"]["status"] == "down"
    assert data["data"]["components"]["db"]["status"] == "up"
    assert data["data"]["components"]["cache"]["status"] == "down"
```

### Success Criteria:

#### Automated Verification:
- [x] Tests pass: `cd api && uv run pytest`
- [x] Type checking passes: `cd api && uv run pyright licensing_api tests`
- [x] Linting passes: `cd api && uv run ruff check licensing_api tests`
- [x] Formatting correct: `cd api && uv run ruff format --check licensing_api tests`

---

## Testing Strategy

### Unit Tests:
- All-healthy: both components return `"up"`, HTTP 200
- DB-down: mock `get_request_db_session` to raise, expect 503 with `db: down`, `cache: up`
- Redis-down: mock `Cache.get_cache().ping()` to raise, expect 503 with `db: up`, `cache: down`

### Integration Tests:
- The existing testcontainer fixtures (`conftest.py`) spin up real PostgreSQL and Redis — the happy-path test exercises real connections

### Manual Testing Steps:
1. Start dev servers (`just dev`)
2. `curl localhost:8000/v1/health/deep` — expect 200 with both up
3. `docker stop api-redis-1` then curl — expect 503 with cache down
4. `docker start api-redis-1 && docker stop api-postgres-1` then curl — expect 503 with db down

## References

- Beads task: pa-compact-licensing-platform-wvq
- Health controller: `api/licensing_api/controllers/health.py`
- Cache singleton: `api/licensing_api/cache/__init__.py:60-98`
- OpenAPI spec: `api/openapi.yaml:75-118`
- Existing tests: `api/tests/controllers/test_health.py`
- Response helpers: `api/licensing_api/controllers/response.py`
