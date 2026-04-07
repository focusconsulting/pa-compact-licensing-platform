from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from licensing_api.__main__ import app
from licensing_api.routes.health_schemas import LiveResp, ReadyResp


@pytest.fixture(scope='module')
def client():
    with TestClient(app) as c:
        yield c


def test_live_returns_200(client):
    response = client.get('/health/live')
    assert response.status_code == 200
    assert LiveResp.model_validate(response.json()) == LiveResp(status='ok')


def test_ready_all_healthy(client):
    response = client.get('/health/ready')
    assert response.status_code == 200
    assert ReadyResp.model_validate(response.json()) == ReadyResp(db=True, cache=True)


def test_ready_db_down(client):
    with (
        patch(
            'licensing_api.routes.health.check_postgres',
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            'licensing_api.routes.health.check_redis',
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        response = client.get('/health/ready')
        assert response.status_code == 200
        assert ReadyResp.model_validate(response.json()) == ReadyResp(db=False, cache=True)


def test_ready_cache_down(client):
    with (
        patch(
            'licensing_api.routes.health.check_postgres',
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            'licensing_api.routes.health.check_redis',
            new_callable=AsyncMock,
            return_value=False,
        ),
    ):
        response = client.get('/health/ready')
        assert response.status_code == 200
        assert ReadyResp.model_validate(response.json()) == ReadyResp(db=True, cache=False)


def test_ready_all_down(client):
    with (
        patch(
            'licensing_api.routes.health.check_postgres',
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            'licensing_api.routes.health.check_redis',
            new_callable=AsyncMock,
            return_value=False,
        ),
    ):
        response = client.get('/health/ready')
        assert response.status_code == 200
        assert ReadyResp.model_validate(response.json()) == ReadyResp(db=False, cache=False)
