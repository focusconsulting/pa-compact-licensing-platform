import pytest
from asgi_lifespan import LifespanManager

from licensing_api.__main__ import app


@pytest.fixture
async def running_app():
    async with LifespanManager(app):
        yield app


async def test_test_table_row_one_has_epoch_added_at(running_app):
    async with running_app.state.db_pool.acquire() as conn:
        row = await conn.fetchrow('SELECT added_at FROM test WHERE id = 1')

    assert row is not None
    assert row['added_at'].timestamp() == 0
