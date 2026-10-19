"""The computed-status functions in the database are the queries in licensing_api/repo/status.py (ADR-0005)."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from licensing_api.migrations import run_migrations
from licensing_api.repo.status import STATUS_FUNCTIONS, function_body, status_ddl
from tests.conftest import TEST_SETTINGS

_BODY = text('SELECT prosrc FROM pg_proc WHERE proname = :name')


async def test_the_database_holds_the_queries_in_code(db_session):
    for function in STATUS_FUNCTIONS:
        assert await db_session.scalar(_BODY, {'name': function.name}) == function_body(function)


async def test_a_startup_with_nothing_to_migrate_still_replaces_the_functions(client):
    stale = status_ddl()[0].replace('$body$\n', '$body$\n-- an older definition\n', 1)
    engine = create_async_engine(TEST_SETTINGS.db_url, poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.execute(text(stale))
    try:
        run_migrations()

        async with engine.connect() as connection:
            body = await connection.scalar(_BODY, {'name': STATUS_FUNCTIONS[0].name})
        assert body == function_body(STATUS_FUNCTIONS[0])
    finally:
        await engine.dispose()


def test_views_are_created_after_the_functions_they_read():
    statements = status_ddl()

    assert [s.startswith('CREATE OR REPLACE FUNCTION') for s in statements] == [True] * len(
        STATUS_FUNCTIONS
    ) + [False] * len(STATUS_FUNCTIONS)
