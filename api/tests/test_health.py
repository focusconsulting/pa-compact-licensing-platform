from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from licensing_api.__main__ import app
from licensing_api.routes.health_schemas import LiveResp, ReadyResp

client = TestClient(app)


def test_live_returns_200():
    response = client.get('/health/live')
    assert response.status_code == 200
    assert LiveResp.model_validate(response.json()) == LiveResp(status='ok')


def test_ready_all_healthy():
    response = client.get('/health/ready')
    assert response.status_code == 200
    assert ReadyResp.model_validate(response.json()) == ReadyResp(db=True, cache=True)


def test_ready_db_down():
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


def test_ready_cache_down():
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


def test_ready_all_down():
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
