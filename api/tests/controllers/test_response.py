from pydantic import ValidationError
from werkzeug.exceptions import BadRequest, NotFound, UnprocessableEntity

from licensing_api.controllers.response import (
    convert_validation_error_to_validation_error_detail,
    empty_api_response,
    error_response,
    strip_error_field,
    success_response,
)
from licensing_api.utils.api_exceptions import FieldValidationErrorDetail


class TestSuccessResponse:
    def test_creates_200_response(self) -> None:
        resp = success_response("OK", {"key": "value"})
        assert resp.status_code == 200
        assert resp.message == "OK"
        assert resp.data == {"key": "value"}

    def test_custom_status_code(self) -> None:
        resp = success_response("Created", status_code=201)
        assert resp.status_code == 201

    def test_with_warnings(self) -> None:
        warnings = [FieldValidationErrorDetail(type="warn", field="name")]
        resp = success_response("OK", warnings=warnings)
        assert resp.warnings is not None
        assert len(resp.warnings) == 1


class TestErrorResponse:
    def test_creates_error_with_status(self) -> None:
        resp = error_response(BadRequest, "Bad request", ["invalid input"])
        assert resp.status_code == 400
        assert resp.message == "Bad request"
        assert resp.errors == ["invalid input"]

    def test_not_found_response(self) -> None:
        resp = error_response(NotFound, "Not found", [])
        assert resp.status_code == 404

    def test_unprocessable_entity(self) -> None:
        errors = [FieldValidationErrorDetail(type="required", field="name")]
        resp = error_response(UnprocessableEntity, "Validation failed", errors)
        assert resp.status_code == 422


class TestEmptyApiResponse:
    def test_default_204(self) -> None:
        body, status, headers = empty_api_response()
        assert status == 204
        assert body == {}

    def test_custom_status(self) -> None:
        _, status, _ = empty_api_response(status_code=200)
        assert status == 200


class TestStripErrorField:
    def test_strips_quotes_and_whitespace(self) -> None:
        errors = [
            FieldValidationErrorDetail(type="value_error", field="'transactionAmount'"),
            FieldValidationErrorDetail(type="required", field="  name  "),
        ]
        stripped = strip_error_field(errors)
        assert stripped[0].field == "transactionAmount"
        assert stripped[1].field == "name"


class TestConvertValidationError:
    def test_converts_pydantic_errors(self) -> None:
        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str
            age: int

        try:
            TestModel(name=123, age="not_int")  # type: ignore
        except ValidationError as ex:
            details = convert_validation_error_to_validation_error_detail(ex)
            assert len(details) == 2
            fields = {d.field for d in details}
            assert "name" in fields
            assert "age" in fields
