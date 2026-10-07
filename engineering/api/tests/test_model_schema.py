"""Every table model matches its table, and every table has a model (ADR-0005)."""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Column, text
from sqlmodel import AutoString, SQLModel

import licensing_api.repo  # noqa: F401 -- registers every table model on SQLModel.metadata

_POSTGRES_TYPES_BY_PYTHON_TYPE = {
    int: {'smallint', 'integer', 'bigint'},
    str: {'text', 'character', 'character varying'},
    bool: {'boolean'},
    # Instants are always timestamptz (Principle XIII).
    datetime: {'timestamp with time zone'},
    date: {'date'},
    UUID: {'uuid'},
    dict: {'jsonb'},
}

# Tables owned by yoyo, and the local-only seed table awaiting removal from migrations.
_TABLES_WITHOUT_MODELS = {'_yoyo_log', '_yoyo_migration', '_yoyo_version', 'yoyo_lock', 'test'}


def _python_type(column: Column) -> type:
    # SQLModel's AutoString does not implement python_type.
    if isinstance(column.type, AutoString):
        return str
    return column.type.python_type


async def _database_columns(db_session) -> dict[str, dict[str, tuple[str, bool]]]:
    result = await db_session.execute(
        text(
            "SELECT table_name, column_name, data_type, is_nullable = 'YES' "
            "FROM information_schema.columns WHERE table_schema = 'public'"
        )
    )
    tables: dict[str, dict[str, tuple[str, bool]]] = {}
    for table_name, column_name, data_type, nullable in result:
        tables.setdefault(table_name, {})[column_name] = (data_type, nullable)
    return tables


async def test_every_model_matches_its_table(db_session):
    database = await _database_columns(db_session)
    mismatches = []
    for table in SQLModel.metadata.sorted_tables:
        db_columns = database.get(table.name)
        if db_columns is None:
            mismatches.append(f'{table.name}: no such table')
            continue
        model_names = {column.name for column in table.columns}
        if model_names != set(db_columns):
            mismatches.append(
                f'{table.name}: only in model {sorted(model_names - set(db_columns))}, '
                f'only in table {sorted(set(db_columns) - model_names)}'
            )
            continue
        for column in table.columns:
            data_type, db_nullable = db_columns[column.name]
            if column.nullable != db_nullable:
                mismatches.append(
                    f'{table.name}.{column.name}: model nullable={column.nullable}, table nullable={db_nullable}'
                )
            # The ORM must also send instants as timestamptz, or asyncpg rejects aware datetimes.
            if _python_type(column) is datetime and not getattr(column.type, 'timezone', False):
                mismatches.append(
                    f'{table.name}.{column.name}: model datetime is not timezone-aware'
                )
            if data_type not in _POSTGRES_TYPES_BY_PYTHON_TYPE[_python_type(column)]:
                mismatches.append(
                    f'{table.name}.{column.name}: model {_python_type(column).__name__}, table {data_type}'
                )
    assert mismatches == []


async def test_every_table_has_a_model(db_session):
    database = await _database_columns(db_session)
    modelled = {table.name for table in SQLModel.metadata.sorted_tables}
    assert set(database) - modelled - _TABLES_WITHOUT_MODELS == set()
