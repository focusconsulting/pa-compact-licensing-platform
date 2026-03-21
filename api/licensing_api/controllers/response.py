from typing import Any

from connexion import request  # type: ignore
from connexion.lifecycle import ConnexionRequest  # type: ignore
from flask_wtf import csrf  # type: ignore
from pydantic import ValidationError
from werkzeug.exceptions import (
    BadRequest,
    Conflict,
    Forbidden,
    HTTPException,
    NotFound,
    ServiceUnavailable,
    UnprocessableEntity,
)

from licensing_api.utils.api_exceptions import FieldValidationErrorDetail, RuleValidationErrorDetail
from licensing_api.utils.pydantic import PydanticBaseModel

ApiResponse = tuple[dict[str, Any] | None, int, dict[str, str] | None]


class PagingMetaData(PydanticBaseModel):
    page_offset: int
    page_size: int
    total_records: int
    total_pages: int
    order_by: str
    order_direction: str


class MetaData(PydanticBaseModel):
    resource: str
    method: str
    query: dict[str, str] | None = None
    paging: PagingMetaData | None = None


class Response(PydanticBaseModel):
    status_code: int
    message: str = ""
    meta: MetaData | None = None
    data: None | dict | list[dict] = None
    warnings: (
        list[FieldValidationErrorDetail] | list[RuleValidationErrorDetail] | list[str] | None
    ) = None
    errors: (
        list[FieldValidationErrorDetail] | list[RuleValidationErrorDetail] | list[str] | None
    ) = None

    def to_api_response(self, passed_request: ConnexionRequest | None = None) -> ApiResponse:
        # In some situations this is invoked before Connexion has setup the global request
        # For example, handling an error validating a request body against the open API spec
        request_to_use = passed_request if passed_request is not None else request
        scope = request_to_use.scope
        assert scope is not None, "Request scope must be available"
        if self.meta is None:
            self.meta = MetaData(method=scope["method"], resource=scope["path"])
        else:
            self.meta.method = scope["method"]
            self.meta.resource = scope["path"]
        response_headers = {
            "Content-Type": "application/json",
            "Access-Control-Expose-Headers": "X-CSRFToken",
        }
        # The request is no longer active in an error handler, and
        # flask_wtf requires an active requests, so check the status
        # code.  It doesn't make any sense to generate a CSRF token
        # for an error response anyway.
        if self.status_code == 200:
            response_headers["X-CSRFToken"] = csrf.generate_csrf()
        return (
            self.model_dump(exclude_none=True, by_alias=True),
            self.status_code,
            response_headers,
        )


def empty_api_response(status_code: int = 204) -> ApiResponse:
    return ({}, status_code, {})


def success_response(
    message: str,
    data: None | dict | list[dict] = None,
    warnings: list[FieldValidationErrorDetail] | None = None,
    status_code: int = 200,
    meta: MetaData | None = None,
) -> Response:
    return Response.model_construct(
        status_code=status_code, message=message, data=data, warnings=warnings, meta=meta
    )


def error_response(
    status_code: HTTPException
    | type[HTTPException]
    | type[BadRequest]
    | type[Conflict]
    | type[ServiceUnavailable]
    | type[NotFound]
    | type[Forbidden]
    | type[UnprocessableEntity],
    message: str,
    errors: list[FieldValidationErrorDetail] | list[RuleValidationErrorDetail] | list[str],
    data: None | dict | list[dict] = None,
    warnings: list[FieldValidationErrorDetail]
    | list[RuleValidationErrorDetail]
    | list[str]
    | None = None,
) -> Response:
    code = status_code.code if status_code.code is not None else 400

    return Response.model_construct(
        status_code=code, message=message, errors=errors, data=data, warnings=warnings
    )


def convert_validation_error_to_validation_error_detail(
    ex: ValidationError,
) -> list[FieldValidationErrorDetail]:
    details = []
    for error in ex.errors():
        type = error["type"]
        field = (
            error["ctx"]["field"]
            if "ctx" in error and "field" in error["ctx"]
            else ".".join(str(loc) for loc in error["loc"])
        )
        details.append(FieldValidationErrorDetail(type=type, field=field))
    return details


def strip_error_field(errors: list[FieldValidationErrorDetail]) -> list[FieldValidationErrorDetail]:
    """
    Strip the error field of any leading or trailing whitespace and single quotes.
    Example:
    Input: [{"type": "value_error", "field": "'transactionAmount'"}]
    Output: [{"type": "value_error", "field": "transactionAmount"}]
    """
    return [
        FieldValidationErrorDetail(type=error.type, field=error.field.strip().strip("'"))
        for error in errors
    ]
