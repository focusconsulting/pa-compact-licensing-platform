import os
from collections.abc import Generator

import connexion
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from licensing_api.cache import Cache


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer]:
    """Start a PostgreSQL container for the test session."""
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer]:
    """Start a Redis container for the test session."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


@pytest.fixture(autouse=True)
def set_db_env(postgres_container: PostgresContainer, redis_container: RedisContainer) -> None:
    """Configure environment to point at testcontainers."""
    os.environ["POSTGRES_CONNECTION_STRING"] = postgres_container.get_connection_url()

    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    # Cache.get_cache() constructs the URL as f"{redis_url}:{redis_port}"
    # so set redis_url without port and redis_port separately
    os.environ["SESSION_CONFIG__REDIS_URL"] = f"redis://{host}"
    os.environ["SESSION_CONFIG__REDIS_PORT"] = str(port)

    # Reset the Cache singleton so it reconnects to the new container
    Cache._client = None


@pytest.fixture
def test_client() -> connexion.FlaskApp:
    from licensing_api.app import create_app

    return create_app().test_client()
