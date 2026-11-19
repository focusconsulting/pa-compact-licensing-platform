"""GET /api/admin/status: the system admin sees what the API task is running."""

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from licensing_api.__main__ import app
from licensing_api.dependencies import get_db_engine
from tests.factories import make_user

_URL = '/api/admin/status'
_MIGRATIONS = Path(__file__).parents[1] / 'db-migrations'


def _user(client, session, role: str, state_code: str | None = None) -> str:
    async def _make():
        user = await make_user(
            session, email=f'{uuid.uuid4().hex}@example.com', role=role, state_code=state_code
        )
        return user.email

    return client.portal.call(_make)


def test_a_system_admin_sees_the_version_uptime_and_database(client, auth_header, route_db_session):
    email = _user(client, route_db_session, 'admin')

    response = client.get(_URL, headers=auth_header(email))

    assert response.status_code == 200
    data = response.json()['data']
    assert (data['version'], data['environment']) == ('dev', 'LOCAL_DEV')
    assert data['uptime_seconds'] >= 0
    assert datetime.fromisoformat(data['started_at']).utcoffset() == timedelta(0)
    database = data['database']
    assert database['reachable'] is True
    assert database['latency_ms'] >= 0
    assert database['latest_migration'] == max(p.stem for p in _MIGRATIONS.glob('*.sql'))


@pytest.mark.parametrize(
    ('role', 'state_code'),
    [('compact_admin', None), ('state_admin', 'KS'), ('licensee', None)],
)
def test_only_a_system_admin_sees_the_status(
    client, auth_header, route_db_session, role, state_code
):
    email = _user(client, route_db_session, role, state_code)

    response = client.get(_URL, headers=auth_header(email))

    assert response.status_code == 403


def test_an_anonymous_caller_sees_nothing(client):
    assert client.get(_URL).status_code == 401


def _engine_that_cannot_connect() -> MagicMock:
    connection = MagicMock()
    connection.__aenter__ = AsyncMock(side_effect=OSError('connection refused'))
    connection.__aexit__ = AsyncMock(return_value=False)
    engine = MagicMock()
    engine.connect.return_value = connection
    return engine


@pytest.fixture
def database_down(client):
    app.dependency_overrides[get_db_engine] = _engine_that_cannot_connect
    yield
    del app.dependency_overrides[get_db_engine]


def test_an_unreachable_database_is_reported_not_raised(
    client, auth_header, route_db_session, database_down
):
    email = _user(client, route_db_session, 'admin')

    response = client.get(_URL, headers=auth_header(email))

    assert response.status_code == 200
    assert response.json()['data']['database'] == {
        'reachable': False,
        'latency_ms': None,
        'latest_migration': None,
    }
