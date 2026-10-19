import logging

import httpx

from licensing_api.request_logger import UnhandledExceptionMiddleware


async def _failing_app(scope, receive, send):
    raise RuntimeError('boom')


async def test_unhandled_exception_is_logged_and_becomes_a_500(caplog):
    transport = httpx.ASGITransport(app=UnhandledExceptionMiddleware(_failing_app))

    with caplog.at_level(logging.ERROR, logger='licensing_api.request_logger'):
        async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
            response = await client.get('/anything')

    assert response.status_code == 500
    assert response.json() == {'detail': 'Internal server error'}
    assert any(r.message == 'Unhandled exception' and r.exc_info for r in caplog.records)


async def test_non_http_scopes_pass_through():
    seen = []

    async def _inner(scope, receive, send):
        seen.append(scope['type'])

    await UnhandledExceptionMiddleware(_inner)({'type': 'lifespan'}, None, None)

    assert seen == ['lifespan']
