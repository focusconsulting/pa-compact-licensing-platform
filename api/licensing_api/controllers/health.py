import datetime
import logging

from sqlalchemy import text

from licensing_api.cache import Cache
from licensing_api.controllers.response import ApiResponse, success_response
from licensing_api.middleware import get_request_db_session

logger = logging.getLogger(__name__)


def health_deep() -> ApiResponse:
    components: dict[str, dict[str, str]] = {}

    # Check PostgreSQL
    try:
        session = get_request_db_session()
        if session is None:
            raise RuntimeError("No database session available")
        session.execute(text("SELECT 1;")).one()
        components["db"] = {"status": "up"}
    except Exception:
        logger.exception("PostgreSQL health check failed")
        components["db"] = {"status": "down"}

    # Check Redis
    try:
        Cache.get_cache().ping()
        components["cache"] = {"status": "up"}
    except Exception:
        logger.exception("Redis health check failed")
        components["cache"] = {"status": "down"}

    all_up = all(c["status"] == "up" for c in components.values())
    overall_status = "up" if all_up else "down"

    payload = {
        "status": overall_status,
        "timestamp": datetime.datetime.now(datetime.UTC),
        "apiName": "api",
        "apiVersion": "v1",
        "components": components,
    }

    status_code = 200 if all_up else 503
    return success_response("Response", payload, status_code=status_code).to_api_response()


def health() -> ApiResponse:
    return success_response(
        "Success",
        {
            "status": "up",
            "timestamp": datetime.datetime.now(datetime.UTC),
            "apiName": "api",
            "apiVersion": "v1",
        },
    ).to_api_response()
