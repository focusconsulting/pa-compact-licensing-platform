from unittest.mock import MagicMock

import pytest
import requests
from werkzeug.exceptions import BadRequest, InternalServerError, NotFound

from licensing_api.utils.api_exceptions import (
    ApiException,
    ExternalApiErrorEncountered,
    FieldValidationErrorDetail,
    FieldValidationException,
    RuleValidationErrorDetail,
    RuleValidationException,
    handle_external_api_error,
)


class TestApiException:
    def test_is_exception(self) -> None:
        ex = ApiException("test error")
        assert isinstance(ex, Exception)
        assert str(ex) == "test error"


class TestFieldValidationException:
    def test_stores_errors(self) -> None:
        errors = [
            FieldValidationErrorDetail(type="required", field="name"),
            FieldValidationErrorDetail(type="too_long", field="email"),
        ]
        ex = FieldValidationException(errors)
        assert len(ex.errors) == 2
        assert ex.errors[0].field == "name"
        assert ex.errors[1].type == "too_long"

    def test_inherits_api_exception(self) -> None:
        ex = FieldValidationException([])
        assert isinstance(ex, ApiException)


class TestRuleValidationException:
    def test_stores_errors(self) -> None:
        errors = [RuleValidationErrorDetail(rule="must_be_eligible")]
        ex = RuleValidationException(errors)
        assert len(ex.errors) == 1
        assert ex.errors[0].rule == "must_be_eligible"

    def test_inherits_api_exception(self) -> None:
        ex = RuleValidationException([])
        assert isinstance(ex, ApiException)


class TestExternalApiErrorEncountered:
    def test_stores_fields(self) -> None:
        ex = ExternalApiErrorEncountered(
            message="failed",
            status=BadRequest,
            api_name="test_api",
            errors=["something went wrong"],
        )
        assert str(ex) == "failed"
        assert ex.status == BadRequest
        assert ex.api_name == "test_api"
        assert ex.errors == ["something went wrong"]


class TestHandleExternalApiError:
    def test_passes_through_on_success(self) -> None:
        @handle_external_api_error("test_api")
        def my_func() -> str:
            return "ok"

        assert my_func() == "ok"

    def test_catches_http_error_400(self) -> None:
        @handle_external_api_error("test_api")
        def my_func() -> None:
            response = MagicMock()
            response.status_code = 400
            response.text = "bad request"
            request = MagicMock(spec=requests.Request)
            request.json = {}
            raise requests.HTTPError(response=response, request=request)

        with pytest.raises(ExternalApiErrorEncountered) as exc_info:
            my_func()
        assert exc_info.value.status == BadRequest

    def test_catches_http_error_500(self) -> None:
        @handle_external_api_error("test_api")
        def my_func() -> None:
            response = MagicMock()
            response.status_code = 500
            response.text = "internal error"
            request = MagicMock(spec=requests.Request)
            request.json = {}
            raise requests.HTTPError(response=response, request=request)

        with pytest.raises(ExternalApiErrorEncountered) as exc_info:
            my_func()
        assert exc_info.value.status == InternalServerError

    def test_catches_connection_error(self) -> None:
        @handle_external_api_error("test_api")
        def my_func() -> None:
            raise requests.ConnectionError("refused")

        with pytest.raises(ExternalApiErrorEncountered) as exc_info:
            my_func()
        assert exc_info.value.status == NotFound

    def test_catches_generic_exception(self) -> None:
        @handle_external_api_error("test_api")
        def my_func() -> None:
            raise RuntimeError("unexpected")

        with pytest.raises(ExternalApiErrorEncountered) as exc_info:
            my_func()
        assert exc_info.value.status == InternalServerError

    def test_re_raises_rule_validation(self) -> None:
        @handle_external_api_error("test_api")
        def my_func() -> None:
            raise RuleValidationException([RuleValidationErrorDetail(rule="test")])

        with pytest.raises(RuleValidationException):
            my_func()
