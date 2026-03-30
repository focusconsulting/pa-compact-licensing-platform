import datetime
from unittest.mock import patch

import connexion
from freezegun import freeze_time


class TestHealth:
    @freeze_time("2024-07-26")
    def test_get_health_endpoint(self, test_client: connexion.FlaskApp) -> None:
        now = datetime.datetime.now(datetime.UTC)
        response = test_client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["statusCode"] == 200
        assert data["message"] == "Success"
        assert data["data"] == {
            "status": "up",
            "timestamp": now.isoformat(),
            "apiName": "api",
            "apiVersion": "v1",
        }

    @freeze_time("2024-07-26")
    def test_get_health_deep_endpoint(self, test_client: connexion.FlaskApp) -> None:
        now = datetime.datetime.now(datetime.UTC)
        response = test_client.get("/v1/health/deep")
        assert response.status_code == 200
        data = response.json()
        assert data["statusCode"] == 200
        assert data["data"] == {
            "status": "up",
            "timestamp": now.isoformat(),
            "apiName": "api",
            "apiVersion": "v1",
            "components": {"db": {"status": "up"}, "cache": {"status": "up"}},
        }

    @freeze_time("2024-07-26")
    def test_health_deep_db_down(self, test_client: connexion.FlaskApp) -> None:
        """When PostgreSQL is unreachable, returns 503 with db status down."""
        with patch("licensing_api.controllers.health.get_request_db_session") as mock_session:
            mock_session.return_value.execute.side_effect = Exception("connection refused")
            response = test_client.get("/v1/health/deep")
        assert response.status_code == 503
        data = response.json()
        assert data["data"]["status"] == "down"
        assert data["data"]["components"]["db"]["status"] == "down"
        assert data["data"]["components"]["cache"]["status"] == "up"

    @freeze_time("2024-07-26")
    def test_health_deep_redis_down(self, test_client: connexion.FlaskApp) -> None:
        """When Redis is unreachable, returns 503 with cache status down."""
        with patch("licensing_api.controllers.health.Cache") as mock_cache:
            mock_cache.get_cache.return_value.ping.side_effect = Exception("connection refused")
            response = test_client.get("/v1/health/deep")
        assert response.status_code == 503
        data = response.json()
        assert data["data"]["status"] == "down"
        assert data["data"]["components"]["db"]["status"] == "up"
        assert data["data"]["components"]["cache"]["status"] == "down"
