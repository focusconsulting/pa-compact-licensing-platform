import json

from connexion.lifecycle import (
    ConnexionRequest,  # type: ignore
    ConnexionResponse,
)
from werkzeug.exceptions import NotFound, ServiceUnavailable, UnprocessableEntity

import licensing_api.controllers.response
import licensing_api.utils.api_exceptions


def not_found_handler(request: ConnexionRequest, ex: Exception) -> ConnexionResponse:
    (resp, status_code, headers) = licensing_api.controllers.response.error_response(
        NotFound, message="requested url was not found", errors=[]
    ).to_api_response(request)

    return ConnexionResponse(
        status_code,
        None,
        "application/json",
        body=json.dumps(resp),
        headers=headers,
    )


def api_exception_error_handler(
    request: ConnexionRequest, ex: licensing_api.utils.api_exceptions.ApiException
) -> ConnexionResponse:
    """
    Error handler for when an ApiException is raised

    FieldValidationException and RuleValidationException generate a 422 status and the generic ApiException
    generates a 503
    """

    match ex:
        case licensing_api.utils.api_exceptions.ExternalApiErrorEncountered():
            (resp, status_code, headers) = licensing_api.controllers.response.error_response(
                ex.status,
                message=f"Error invoking {ex.api_name}: {ex}",
                errors=ex.errors,
            ).to_api_response()

            return ConnexionResponse(
                status_code,
                None,
                "application/json",
                body=json.dumps(resp),
                headers=headers,
            )
        case licensing_api.utils.api_exceptions.FieldValidationException():
            errors = licensing_api.controllers.response.strip_error_field(ex.errors)
            (resp, status_code, headers) = licensing_api.controllers.response.error_response(
                UnprocessableEntity,
                message="Request body was not valid",
                errors=errors,
            ).to_api_response(request)
            return ConnexionResponse(
                status_code,
                None,
                "application/json",
                body=json.dumps(resp),
                headers=headers,
            )
        case licensing_api.utils.api_exceptions.RuleValidationException():
            (resp, status_code, headers) = licensing_api.controllers.response.error_response(
                UnprocessableEntity,
                message="Business rule was violated",
                errors=ex.errors,
            ).to_api_response(request)
            return ConnexionResponse(
                status_code,
                None,
                "application/json",
                body=json.dumps(resp),
                headers=headers,
            )
        case licensing_api.utils.api_exceptions.ApiException():
            (resp, status_code, headers) = licensing_api.controllers.response.error_response(
                ServiceUnavailable,
                message="Unexpected error",
                errors=[],
            ).to_api_response(request)
            return ConnexionResponse(
                status_code,
                None,
                "application/json",
                body=json.dumps(resp),
                headers=headers,
            )
