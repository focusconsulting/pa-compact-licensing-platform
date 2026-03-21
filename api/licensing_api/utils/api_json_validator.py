from typing import Any

from connexion.validators.json import JSONRequestBodyValidator  # type: ignore

from licensing_api.utils.api_exceptions import (
    ApiException,
    FieldValidationErrorDetail,
    FieldValidationException,
)


class ApiJSONRequestBodyValidator(JSONRequestBodyValidator):
    """
    This extends the JSONRequestBodyValidator in the connexion library.  It changes the functionality
    so that all of the validation errors are surfaced (rather than just the first) and raises an FieldValidationException
    rather than BadRequestProblem
    """

    def _validate(self, body: Any) -> dict | None:
        if not self._nullable and body is None:
            raise ApiException("Request body must not be empty")

        errors = self._validator.iter_errors(body)

        validation_errors = []
        for error in errors:
            # https://github.com/python-jsonschema/jsonschema/issues/119
            if len(error.path) > 0:
                field = error.path[0]
            else:
                field = error.message.split(" ")[0]

            validation_errors.append(FieldValidationErrorDetail(type=error.validator, field=field))

        if len(validation_errors) > 0:
            raise FieldValidationException(validation_errors)

        return None
