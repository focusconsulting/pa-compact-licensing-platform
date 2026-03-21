from collections.abc import Callable
from functools import wraps
from typing import Any

import requests
from pydantic import ValidationError
from werkzeug.exceptions import (
    BadRequest,
    Conflict,
    ExpectationFailed,
    Forbidden,
    HTTPException,
    InternalServerError,
    NotFound,
    ServiceUnavailable,
    TooManyRequests,
    Unauthorized,
)

from licensing_api.utils import logging
from licensing_api.utils.pydantic import PydanticBaseModel


class ProxyAuthenticationFailed(HTTPException):
    code = 407
    description = "Proxy Authentication Failed"


ApiErrorExceptions = (
    HTTPException
    | type[HTTPException]
    | type[Conflict]
    | type[ServiceUnavailable]
    | type[NotFound]
    | type[Forbidden]
    | type[InternalServerError]
    | type[BadRequest]
    | type[ExpectationFailed]
    | type[ProxyAuthenticationFailed]
    | type[Unauthorized]
    | type[ServiceUnavailable]
)

logger = logging.get_logger(__name__)


class ApiException(Exception):
    """
    Generic API exception that can be extended.  The error handler treats it as a server error
    """

    pass


class FieldValidationErrorDetail(PydanticBaseModel):
    type: str
    field: str
    extra: dict[str, Any] | None = None


class FieldValidationException(ApiException):
    """
    Exception that is generated when a request can be parsed, but one or more fields are invalid.  These invalid fields
    can be caught at the open API spec level or by pydantic when parsing the request body

    Examples of invalid:
    - field that is too long
    - missing required property
    """

    def __init__(self, errors: list[FieldValidationErrorDetail], *args: object) -> None:
        super().__init__(*args)
        self.errors = errors


class RuleValidationErrorDetail(PydanticBaseModel):
    rule: str


class RuleValidationException(ApiException):
    """
    Exception that should be raised when a business rule is violated.

    """

    def __init__(self, errors: list[RuleValidationErrorDetail], *args: object) -> None:
        super().__init__(*args)
        self.errors = errors


class ExternalApiErrorEncountered(ApiException):
    """
    Exception that can be raised if an error is encountered while invoking an API.  They are automatically caught
    by the api_exception_error_handler
    """

    status: ApiErrorExceptions
    api_name: str
    errors: list[str] | list[FieldValidationErrorDetail]

    def __init__(
        self,
        message: str,
        status: ApiErrorExceptions,
        api_name: str,
        errors: list[str] | list[FieldValidationErrorDetail] | None = None,
    ) -> None:
        if errors is None:
            errors = []
        super().__init__(message)
        self.status = status
        self.api_name = api_name
        self.errors = errors


def handle_external_api_error(api_name: str) -> Callable:
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args: Any, **kwargs: Any) -> Any:
            try:
                return f(*args, **kwargs)
            except ValidationError as ex:
                import licensing_api.controllers.response

                errors = licensing_api.controllers.response.convert_validation_error_to_validation_error_detail(
                    ex
                )
                logger.error(
                    "External API response did not match the expected shape",
                    extra={"errors": errors, "api_name": api_name},
                )
                raise ExternalApiErrorEncountered(
                    "response was invalid",
                    status=InternalServerError,
                    api_name=api_name,
                    errors=errors,
                )
            except RuleValidationException as ex:
                logger.info(
                    "External API contains business rule errors",
                    extra={"errors": ex},
                )
                raise ex
            except requests.HTTPError as ex:
                body = ex.request.json if isinstance(ex.request, requests.Request) else {}
                logger.error(
                    f"Failed to run {api_name}",
                    extra={"response": ex.response.text, "request": body},
                )
                match ex.response.status_code:
                    case 400:
                        raise ExternalApiErrorEncountered(
                            ex.response.text, status=BadRequest, api_name=api_name
                        )
                    case 401:
                        raise ExternalApiErrorEncountered(
                            ex.response.text, status=Unauthorized, api_name=api_name
                        )
                    case 403:
                        raise ExternalApiErrorEncountered(
                            ex.response.text, status=Forbidden, api_name=api_name
                        )
                    case 404:
                        raise ExternalApiErrorEncountered(
                            ex.response.text, status=NotFound, api_name=api_name
                        )
                    case 407:
                        raise ExternalApiErrorEncountered(
                            ex.response.text,
                            status=ProxyAuthenticationFailed,
                            api_name=api_name,
                        )
                    case 417:
                        raise ExternalApiErrorEncountered(
                            ex.response.text, status=ExpectationFailed, api_name=api_name
                        )
                    case 429:
                        raise ExternalApiErrorEncountered(
                            ex.response.text, status=TooManyRequests, api_name=api_name
                        )
                    case 500:
                        raise ExternalApiErrorEncountered(
                            ex.response.text, status=InternalServerError, api_name=api_name
                        )
                    case 503:
                        raise ExternalApiErrorEncountered(
                            ex.response.text, status=ServiceUnavailable, api_name=api_name
                        )
                    case _:
                        raise ExternalApiErrorEncountered(
                            ex.response.text, status=BadRequest, api_name=api_name
                        )
            except requests.ConnectionError:
                raise ExternalApiErrorEncountered(
                    "Unable to connect", status=NotFound, api_name=api_name
                )
            except Exception as ex:
                # 2024-12-03 During some smoke test prep we encountered SSLErrors in the mTLS handshake that were silently timed out
                logger.exception("Unexpected external API error", exc_info=ex)
                raise ExternalApiErrorEncountered(
                    "Unexpected external API error", status=InternalServerError, api_name=api_name
                )

        return decorated

    return decorator
