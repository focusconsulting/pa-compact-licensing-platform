import json
from unittest.mock import MagicMock

from fastapi import HTTPException

from licensing_api.errors import ErrorCode, http_exception_handler, validation_error_handler


def test_unknown_route_returns_404(client):
    response = client.get('/api/nonexistent')
    assert response.status_code == 404


def test_missing_auth_header_goes_through_http_exception_handler(client):
    # HTTPBearer raises HTTPException(401) when no Authorization header is present.
    # This goes through http_exception_handler, which returns our ErrorResponse format.
    response = client.get('/api/me')
    assert response.status_code == 401
    body = response.json()
    assert body['code'] == ErrorCode.HttpError
    assert len(body['details']) > 0


async def test_http_exception_handler_string_detail():
    exc = HTTPException(status_code=404, detail='Not Found')
    response = await http_exception_handler(MagicMock(), exc)
    body = json.loads(response.body)
    assert response.status_code == 404
    assert body['code'] == ErrorCode.HttpError
    assert 'Not Found' in body['details']


async def test_http_exception_handler_non_string_detail():
    exc = HTTPException(status_code=400, detail={'field': 'error'})
    response = await http_exception_handler(MagicMock(), exc)
    body = json.loads(response.body)
    assert response.status_code == 400
    assert body['code'] == ErrorCode.HttpError
    assert len(body['details']) > 0


async def test_http_exception_handler_with_headers():
    exc = HTTPException(
        status_code=401, detail='Unauthorized', headers={'WWW-Authenticate': 'Bearer'}
    )
    response = await http_exception_handler(MagicMock(), exc)
    assert response.status_code == 401
    assert response.headers.get('www-authenticate') == 'Bearer'


async def test_validation_error_handler_formats_details():
    exc = MagicMock()
    exc.errors.return_value = [{'loc': ('body', 'name'), 'msg': 'field required'}]
    response = await validation_error_handler(MagicMock(), exc)
    body = json.loads(response.body)
    assert response.status_code == 422
    assert body['code'] == ErrorCode.ValidationError
    assert body['details'] == ['body.name: field required']


async def test_validation_error_handler_multiple_errors():
    exc = MagicMock()
    exc.errors.return_value = [
        {'loc': ('body', 'email'), 'msg': 'invalid email'},
        {'loc': ('body', 'age'), 'msg': 'must be positive'},
    ]
    response = await validation_error_handler(MagicMock(), exc)
    body = json.loads(response.body)
    assert response.status_code == 422
    assert len(body['details']) == 2
