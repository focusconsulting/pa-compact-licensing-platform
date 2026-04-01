# PA Compact Licensing API

## Getting started

See the prerequisites in [root README](../README.md)

Set your local environment variables:

```shell
cp ./.env.example ./env
```

### 1. Install dependencies

```bash
just install
```

### 2. Start local infrastructure (Postgres + Redis)

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
| [asyncpg](https://magicstack.github.io/asyncpg/)                                  | Async PostgreSQL client         | https://magicstack.github.io/asyncpg/                        |
| [redis-py](https://redis-py.readthedocs.io/)                                      | Redis client (async)            | https://redis-py.readthedocs.io/                             |
| [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | Environment-based configuration | https://docs.pydantic.dev/latest/concepts/pydantic_settings/ |
| [uv](https://docs.astral.sh/uv/)                                                  | Dependency management           | https://docs.astral.sh/uv/                                   |
| [pytest](https://docs.pytest.org/)                                                | Test framework                  | https://docs.pytest.org/                                     |
| [ruff](https://docs.astral.sh/ruff/)                                              | Linter and formatter            | https://docs.astral.sh/ruff/                                 |
| [pyright](https://microsoft.github.io/pyright/)                                   | Static type checker             | https://microsoft.github.io/pyright/                         |
