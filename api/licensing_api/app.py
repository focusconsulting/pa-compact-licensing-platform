import os
import time
from datetime import timedelta

import connexion  # type: ignore
import connexion.mock  # type: ignore
import flask
from connexion.middleware import MiddlewarePosition  # type: ignore
from connexion.validators import (  # type: ignore
    VALIDATOR_MAP,
    FormDataValidator,
    MediaTypeDict,
    MultiPartFormDataValidator,
)
from flask import g
from flask_session import Session as FSession  # type: ignore
from flask_wtf.csrf import CSRFProtect  # type: ignore
from starlette.middleware.cors import CORSMiddleware

from licensing_api.cache import Cache
from licensing_api.db import init
from licensing_api.middleware import DbSessionMiddleware
from licensing_api.utils.api_exceptions import ApiException
from licensing_api.utils.api_json_validator import ApiJSONRequestBodyValidator
from licensing_api.utils.config import get_app_config
from licensing_api.utils.logging import get_logger

sess = FSession()
csrf = CSRFProtect()

logger = get_logger(__name__)


def openapi_filenames() -> list[str]:
    return ["../openapi.yaml"]


def get_project_root_dir() -> str:
    return os.path.join(
        os.path.dirname(__file__),
        "../",
    )


def create_app() -> connexion.FlaskApp:  # type: ignore[type-arg]
    logger.info("Starting API")

    db_session_factory = init()

    # Enable mock responses for unimplemented paths.
    resolver = connexion.mock.MockResolver(mock_all=False)

    app = connexion.FlaskApp(
        __name__,
        strict_validation=True,
        validate_responses=True,
    )

    # DB session middleware — manages per-request SQLAlchemy sessions via ContextVar
    app.add_middleware(
        DbSessionMiddleware,  # type: ignore[arg-type]  # ASGI middleware doesn't match connexion's signature
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        db_session_factory=db_session_factory,
    )

    # These settings should get adjusted based on how the API and consumers are deployed
    app.add_middleware(
        CORSMiddleware,  # type: ignore[arg-type]  # starlette CORSMiddleware doesn't match connexion's ASGI signature
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_api(
        openapi_filenames()[0],
        resolver=resolver,
        strict_validation=True,
        validate_responses=True,
        validator_map={
            **VALIDATOR_MAP,
            **{
                "body": MediaTypeDict(
                    {
                        # Override the default JSONRequestBodyValidator
                        "*/*json": ApiJSONRequestBodyValidator,
                        "application/x-www-form-urlencoded": FormDataValidator,
                        "multipart/form-data": MultiPartFormDataValidator,
                    }
                )
            },
        },
    )

    # Global handler that captures field validation errors, business rule violations and errors invoking
    # an external API
    import licensing_api.utils.api_exceptions_error_handler

    app.add_error_handler(
        ApiException,
        licensing_api.utils.api_exceptions_error_handler.api_exception_error_handler,  # type: ignore[arg-type]  # connexion error handler signature mismatch
    )

    flask_app = app.app

    # Configure persistent session
    flask_app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(
        minutes=get_app_config().session_timeout_in_minutes
    )
    flask_app.config["SESSION_TYPE"] = "redis"
    flask_app.config["SESSION_COOKIE_SAMESITE"] = "lax"
    flask_app.config["SESSION_ID_LENGTH"] = 40
    flask_app.config["SESSION_COOKIE_NAME"] = "ses"
    flask_app.config["SESSION_REDIS"] = Cache.get_cache()
    flask_app.config["SESSION_REFRESH_EACH_REQUEST"] = False
    flask_app.config["SESSION_COOKIE_SECURE"] = True
    sess.init_app(flask_app)

    # Configure CSRF protection
    flask_app.config["SECRET_KEY"] = get_app_config().app_secret_key
    csrf.init_app(flask_app)
    flask_app.config["WTF_CSRF_CHECK_DEFAULT"] = True

    @flask_app.before_request
    def set_request_context() -> None:
        g.start_time = time.monotonic()
        g.connexion_flask_app = app

    @flask_app.after_request
    def access_log_end(
        response: flask.Response,
    ) -> flask.Response:
        response_time_ms = 1000 * (time.monotonic() - g.get("start_time"))
        logger.info(
            "%s %s %s",
            response.status_code,
            flask.request.method,
            flask.request.full_path,
            extra={
                "remote_addr": flask.request.remote_addr,
                "response_length": response.content_length,
                "response_type": response.content_type,
                "status_code": response.status_code,
                "response_time_ms": response_time_ms,
            },
        )
        return response

    return app
