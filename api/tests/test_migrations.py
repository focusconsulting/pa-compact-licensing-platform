from sqlalchemy import text

from licensing_api.__main__ import app


def test_test_table_row_one_has_epoch_added_at(client) -> None:
    async def _query():
        async with app.state.session_factory() as session:
            result = await session.execute(text('SELECT added_at FROM test WHERE id = 1'))
            return result.first()

    row = client.portal.call(_query)
    assert row is not None
    assert row[0].timestamp() == 0
