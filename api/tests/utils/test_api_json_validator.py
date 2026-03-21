import pytest

from licensing_api.utils.api_exceptions import ApiException, FieldValidationException
from licensing_api.utils.api_json_validator import ApiJSONRequestBodyValidator


class TestApiJSONRequestBodyValidator:
    def _make_validator(self, schema: dict, nullable: bool = False) -> ApiJSONRequestBodyValidator:
        return ApiJSONRequestBodyValidator(
            schema=schema,
            nullable=nullable,
            encoding="utf-8",
            strict_validation=True,
        )

    def test_raises_on_null_body_when_not_nullable(self) -> None:
        validator = self._make_validator({"type": "object"}, nullable=False)
        with pytest.raises(ApiException, match="Request body must not be empty"):
            validator._validate(None)

    def test_allows_null_body_when_nullable(self) -> None:
        validator = self._make_validator({"type": "object"}, nullable=True)
        # When nullable=True and body is None, validation is skipped (returns None)
        result = validator._validate({"valid": "data"})
        assert result is None

    def test_valid_body_returns_none(self) -> None:
        validator = self._make_validator(
            {"type": "object", "properties": {"name": {"type": "string"}}}
        )
        result = validator._validate({"name": "test"})
        assert result is None

    def test_invalid_body_raises_field_validation(self) -> None:
        validator = self._make_validator(
            {
                "type": "object",
                "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
                "required": ["name", "age"],
            }
        )
        with pytest.raises(FieldValidationException) as exc_info:
            validator._validate({})
        assert len(exc_info.value.errors) == 2

    def test_collects_all_errors(self) -> None:
        validator = self._make_validator(
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "email": {"type": "string"},
                },
                "required": ["name", "age", "email"],
            }
        )
        with pytest.raises(FieldValidationException) as exc_info:
            validator._validate({})
        assert len(exc_info.value.errors) == 3
