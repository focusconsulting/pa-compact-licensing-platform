import datetime

from sqlalchemy import text

from licensing_api.controllers.response import ApiResponse, success_response
from licensing_api.middleware import get_request_db_session


def health_deep() -> ApiResponse:
    session = get_request_db_session()
    if session is None:
        raise RuntimeError("No database session available")

    session.execute(text("SELECT 1;")).one()
    return success_response(
        "Response",
        {
            "status": "up",
            "timestamp": datetime.datetime.now(datetime.UTC),
            "apiName": "api",
            "apiVersion": "v1",
            "components": {"db": {"status": "up"}},
        },
    ).to_api_response()


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
