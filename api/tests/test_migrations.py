import pytest
from asgi_lifespan import LifespanManager
from sqlalchemy import text

from licensing_api.__main__ import app


@pytest.fixture
async def running_app():
    async with LifespanManager(app):
        yield app


async def test_test_table_row_one_has_epoch_added_at(
    running_app,
) -> None:
    async with running_app.state.session_factory() as session:
        result = await session.execute(text('SELECT added_at FROM test WHERE id = 1'))
        row = result.first()

    assert row is not None
    assert row[0].timestamp() == 0
