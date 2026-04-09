# PA Compact Licensing API

## Getting started

See the prerequisites in [root README](../README.md)

Set your local environment variables:

```shell
cp ./.env.example ./env
```

### 1. Install dependencies

This step should be run once.

```bash
just install
```

### 2. Start local infrastructure (Postgres + Redis)

This should be run before launching the service. Everytime it is invoked, the data in services is reset.

You might need to reset the data for testing if a test doesn't clean up properly after itself. However, tests should be written such that the clean up after themselves.

Test data can be defined [ahead of time](./db-migrations/30000101_000000_test_data.sql).

```bash
just infra
```

### 3. Run the API with hot reload

```bash
just dev
```

Visit http://localhost:8000/docs to see the endpoints exposed.

### 4. Stop infrastructure

```bash
just infra-down
```

## Running tests

```bash
# Run all tests
just test

# Run a specific test by name
just test -k test_live_returns_200

# Run with coverage report printed to terminal
just test-coverage

# Open HTML coverage report in browser
just test-coverage-report
```

## Linting and formatting

```bash
# Run all linting (ruff + pyright)
just lint

# Auto-fix and format code
just format

# Type check only
just typecheck
```

## Building the Docker image

```bash
just build
```

This builds the production (`app`) stage and tags the image as `pa-compact-health-api:latest` and
`pa-compact-health-api:<git-sha>`.

## All available tasks

```
just --list
```

## Key frameworks and dependencies

| Package                                                                           | Purpose                         | Docs                                                         |
|-----------------------------------------------------------------------------------|---------------------------------|--------------------------------------------------------------|
| [FastAPI](https://fastapi.tiangolo.com/)                                          | Web framework                   | https://fastapi.tiangolo.com/                                |
| [Uvicorn](https://www.uvicorn.org/)                                               | ASGI server (development)       | https://www.uvicorn.org/                                     |
| [Gunicorn](https://gunicorn.org/)                                                 | WSGI/ASGI server (production)   | https://docs.gunicorn.org/                                   |
| [asyncpg](https://magicstack.github.io/asyncpg/current/)                          | Async PostgreSQL client         | https://magicstack.github.io/asyncpg/current/                |
| [redis-py](https://redis.readthedocs.io/en/stable/)                               | Redis client (async)            | https://redis.readthedocs.io/en/stable/                      |
| [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | Environment-based configuration | https://docs.pydantic.dev/latest/concepts/pydantic_settings/ |
| [yoyo-migrations](https://ollycope.com/software/yoyo/)                            | Database migrations             | https://ollycope.com/software/yoyo/                          |
| [psycopg2](https://www.psycopg.org/docs/)                                         | Sync PostgreSQL driver (yoyo)   | https://www.psycopg.org/docs/                                |
| [uv](https://docs.astral.sh/uv/)                                                  | Dependency management           | https://docs.astral.sh/uv/                                   |
| [pytest](https://docs.pytest.org/en/9.0.x/)                                       | Test framework                  | https://docs.pytest.org/en/9.0.x/                            |
| [pytest-asyncio](https://pytest-asyncio.readthedocs.io/en/stable/)                | Async test support              | https://pytest-asyncio.readthedocs.io/en/stable/             |
| [asgi-lifespan](https://github.com/florimondmanca/asgi-lifespan)                  | ASGI lifespan for tests         | https://github.com/florimondmanca/asgi-lifespan               |
| [ruff](https://docs.astral.sh/ruff/)                                              | Linter and formatter            | https://docs.astral.sh/ruff/                                 |
| [pyright](https://microsoft.github.io/pyright/)                                   | Static type checker             | https://microsoft.github.io/pyright/                         |

<!--
Thu Apr  9 12:39:41 EDT 2026
-->
