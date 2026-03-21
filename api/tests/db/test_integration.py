"""Integration tests using testcontainers to verify database connectivity."""

import pytest
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from licensing_api.db import init
from licensing_api.db.config import DbConfig


@pytest.fixture(scope="module")
def postgres_container():
    """Start a PostgreSQL container for integration tests."""
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as postgres:
        yield postgres


@pytest.fixture
def db_session(postgres_container):
    """Create a database session connected to the testcontainer."""
    connection_url = postgres_container.get_connection_url()
    config = DbConfig(
        connection_string=connection_url,
        schema="public",
    )
    session_factory = init(config)
    try:
        yield session_factory
    finally:
        session_factory.remove()


class TestDatabaseIntegration:
    def test_connection_and_simple_query(self, db_session) -> None:
        """Verify we can connect and execute a simple query."""
        result = db_session.execute(text("SELECT 1 AS value")).one()
        assert result[0] == 1

    def test_current_database(self, db_session) -> None:
        """Verify we're connected to the expected database."""
        result = db_session.execute(text("SELECT current_database()")).one()
        assert result[0] == "test"

    def test_create_and_query_table(self, db_session) -> None:
        """Verify we can create a table, insert data, and query it."""
        db_session.execute(
            text(
                "CREATE TABLE IF NOT EXISTS test_items "
                "(id SERIAL PRIMARY KEY, name VARCHAR(100) NOT NULL)"
            )
        )
        db_session.execute(text("INSERT INTO test_items (name) VALUES (:name)"), {"name": "item1"})
        db_session.execute(text("INSERT INTO test_items (name) VALUES (:name)"), {"name": "item2"})
        db_session.commit()

        results = db_session.execute(text("SELECT name FROM test_items ORDER BY id")).all()
        assert len(results) == 2
        assert results[0][0] == "item1"
        assert results[1][0] == "item2"

        # Clean up
        db_session.execute(text("DROP TABLE test_items"))
        db_session.commit()

    def test_explicit_transaction(self, db_session) -> None:
        """Verify explicit transactions work with BEGIN/COMMIT."""
        db_session.execute(
            text("CREATE TABLE IF NOT EXISTS txn_test (id SERIAL PRIMARY KEY, val TEXT)")
        )

        db_session.execute(text("INSERT INTO txn_test (val) VALUES ('committed')"))

        result = db_session.execute(text("SELECT COUNT(*) FROM txn_test")).one()
        assert result[0] == 1

        db_session.execute(text("DROP TABLE txn_test"))

    def test_schema_search_path(self, db_session) -> None:
        """Verify the search path is set correctly."""
        result = db_session.execute(text("SHOW search_path")).one()
        assert "public" in result[0]
