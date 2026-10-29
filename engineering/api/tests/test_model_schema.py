"""Every table model matches its table, every table has a model, and every status enum matches its CHECK (ADR-0005)."""

import re
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Column, text
from sqlmodel import AutoString, SQLModel

import licensing_api.repo  # noqa: F401 -- registers every table model on SQLModel.metadata
from licensing_api.repo.participation_application import ApplicationStatus
from licensing_api.repo.privilege import AdministratorStatus, DeactivationReason
from licensing_api.repo.privilege_request import PrivilegeRequestStatus
from licensing_api.repo.qualifying_license import LicenseStatus
from licensing_api.repo.status import LicenseComputedStatus

_POSTGRES_TYPES_BY_PYTHON_TYPE = {
    int: {'smallint', 'integer', 'bigint'},
    str: {'text', 'character', 'character varying'},
    bool: {'boolean'},
    # Instants are always timestamptz (Principle XIII).
    datetime: {'timestamp with time zone'},
    date: {'date'},
    UUID: {'uuid'},
    dict: {'jsonb'},
    bytes: {'bytea'},
}

# Tables owned by yoyo, and the local-only seed table awaiting removal from migrations.
_TABLES_WITHOUT_MODELS = {'_yoyo_log', '_yoyo_migration', '_yoyo_version', 'yoyo_lock', 'test'}


def _python_type(column: Column) -> type:
    # SQLModel's AutoString does not implement python_type.
    if isinstance(column.type, AutoString):
        return str
    return column.type.python_type


async def _database_columns(db_session) -> dict[str, dict[str, tuple[str, bool | None]]]:
    """Columns of every table and view. A view's nullability is None: Postgres reports every view column as nullable."""
    result = await db_session.execute(
        text(
            "SELECT c.table_name, c.column_name, c.data_type, c.is_nullable = 'YES', "
            "t.table_type = 'VIEW' "
            'FROM information_schema.columns c JOIN information_schema.tables t '
            'USING (table_schema, table_name) '
            "WHERE c.table_schema = 'public'"
        )
    )
    tables: dict[str, dict[str, tuple[str, bool | None]]] = {}
    for table_name, column_name, data_type, nullable, is_view in result:
        tables.setdefault(table_name, {})[column_name] = (data_type, None if is_view else nullable)
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
            if db_nullable is not None and column.nullable != db_nullable:
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


_STATUS_CHECKS = {
    'chk_participation_applications_status': ApplicationStatus,
    'chk_privilege_requests_status': PrivilegeRequestStatus,
    'chk_privileges_administrator_status': AdministratorStatus,
    'chk_privileges_deactivation_reason': DeactivationReason,
    'chk_qualifying_licenses_state_reported_status': LicenseStatus,
}


async def test_every_status_enum_matches_its_check(db_session):
    result = await db_session.execute(
        text(
            'SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = ANY(:names)'
        ),
        {'names': list(_STATUS_CHECKS)},
    )
    # Postgres renders IN (...) as = ANY (ARRAY['draft'::text, ...]).
    allowed = {
        name: set(re.findall(r"'([a-z_]+)'::text", definition)) for name, definition in result
    }

    assert allowed == {
        name: {member.value for member in enum} for name, enum in _STATUS_CHECKS.items()
    }


def test_computed_license_statuses_include_every_reported_status():
    # The license status query passes a non-active reported status through (repo/status.py).
    assert set(LicenseStatus) <= set(LicenseComputedStatus)
