# API

## Table of contents

-   [Developer Setup](./README.md#developer-setup)
-   [Key Tooling](./README.md#key-tooling)

## Developer Setup

Please make sure that you have completed all the steps in the [root setup](../README.md#developer-setup)
1. Run `just` to see the available commands

## Key Tooling

The API uses these main libraries:
- Connexion: REST API framework using Flask, handles OpenAPI/Swagger specs, mocking, validation
- Flask: Web application framework (via Connexion)
- Gunicorn: WSGI HTTP server for production deployment

Database Layer:
- SQLAlchemy: ORM for database operations
- psycopgbinary: PostgreSQL database driver (binary wheels included)
- Alembic: Database migrations

Data Validation:
- Pydantic: Data validation using Python type hints
- Pydantic-settings: Settings management with Pydantic

Caching & Storage:
- Redis: Caching and session storage
- Flask-session: Server-side session management with Redis backend
- Cachetools: In-memory cache implementations (LRU, TTL)

HTTP Client:
- Requests: HTTP requests library
- Botocore: AWS SDK client (used with botocore)
Security:
- Flask-WTF: CSRF protection and form handling

Performance/Monitoring:
- Locust: Load testing framework
- Uvicorn: ASGI server (optional in Connexion)

Development Tools:
- Pytest: Testing framework
- Pyright: Static type checker
- Coverage: Code coverage
- Testcontainers: Docker-based test isolation
- Freezegun: Time mocking for tests

