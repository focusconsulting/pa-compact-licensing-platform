from unittest.mock import AsyncMock, MagicMock

import pytest

from licensing_api.__main__ import app
from licensing_api.dependencies import get_db_engine, get_redis
from licensing_api.routes.health_schemas import LiveResp, ReadyResp


def test_live_returns_200(client):
    response = client.get('/api/health/live')
    assert response.status_code == 200
    assert LiveResp.model_validate(response.json()) == LiveResp(status='ok')


def test_ready_all_healthy(client):
    response = client.get('/api/health/ready')
    assert response.status_code == 200
    assert ReadyResp.model_validate(response.json()) == ReadyResp(db=True, cache=True)


def _mock_engine_raising(exc: Exception) -> MagicMock:
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(side_effect=exc)
    cm.__aexit__ = AsyncMock(return_value=False)
    engine = MagicMock()
    engine.connect.return_value = cm
    return engine


def _mock_redis_raising(exc: Exception) -> AsyncMock:
    redis = AsyncMock()
    redis.ping.side_effect = exc
    return redis


@pytest.fixture()
def db_raises(client):
    app.dependency_overrides[get_db_engine] = lambda: _mock_engine_raising(Exception('DB error'))
    yield
    del app.dependency_overrides[get_db_engine]


@pytest.fixture()
def cache_raises(client):
    app.dependency_overrides[get_redis] = lambda: _mock_redis_raising(Exception('Redis error'))
    yield
    del app.dependency_overrides[get_redis]


def test_ready_db_down(client, db_raises):
    response = client.get('/api/health/ready')
    assert response.status_code == 200
    assert ReadyResp.model_validate(response.json()) == ReadyResp(db=False, cache=True)


def test_ready_cache_down(client, cache_raises):
    response = client.get('/api/health/ready')
    assert response.status_code == 200
    assert ReadyResp.model_validate(response.json()) == ReadyResp(db=True, cache=False)


def test_ready_all_down(client, db_raises, cache_raises):
    response = client.get('/api/health/ready')
    assert response.status_code == 200
    assert ReadyResp.model_validate(response.json()) == ReadyResp(db=False, cache=False)
