from unittest.mock import AsyncMock, MagicMock

import pytest

from licensing_api.__main__ import app
from licensing_api.dependencies import get_db_engine
from licensing_api.routes.health import LiveResp, ReadyResp


def test_live_returns_200(client):
    response = client.get('/api/health/live')
    assert response.status_code == 200
    assert LiveResp.model_validate(response.json()) == LiveResp(status='ok')


def test_ready_db_healthy(client):
    response = client.get('/api/health/ready')
    assert response.status_code == 200
    assert ReadyResp.model_validate(response.json()) == ReadyResp(db=True)


def _mock_engine_raising(exc: Exception) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=exc)
    cm.__aexit__ = AsyncMock(return_value=False)
    engine = MagicMock()
    engine.connect.return_value = cm
    return engine


@pytest.fixture()
def db_raises(client):
    app.dependency_overrides[get_db_engine] = lambda: _mock_engine_raising(Exception('DB error'))
    yield
    del app.dependency_overrides[get_db_engine]


def test_ready_db_down(client, db_raises):
    response = client.get('/api/health/ready')
    assert response.status_code == 200
    assert ReadyResp.model_validate(response.json()) == ReadyResp(db=False)
