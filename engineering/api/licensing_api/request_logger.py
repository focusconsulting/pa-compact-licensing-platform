import logging
import re
import time
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from licensing_api.errors import ErrorCode, ErrorResponse

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = 'X-Request-ID'
# Limits an inbound ID to a short token, so a caller cannot write arbitrary text into the logs.
_VALID_REQUEST_ID = re.compile(r'[A-Za-z0-9._-]{1,128}')


class RequestIdMiddleware:
    """Give each request an ID: the caller's ``X-Request-ID`` if it is a short token, else a new one.

    The ID is in ``request.state.request_id``, on the response, and in the request log line (ADR-0009).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Store the request's ID in ``scope["state"]`` and add it to the response headers; non-HTTP scopes pass through."""
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        inbound = (
            dict(scope['headers']).get(REQUEST_ID_HEADER.lower().encode(), b'').decode('latin-1')
        )
        request_id = inbound if _VALID_REQUEST_ID.fullmatch(inbound) else uuid4().hex
        scope.setdefault('state', {})['request_id'] = request_id

        async def send_with_id(message: Message) -> None:
            if message['type'] == 'http.response.start':
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        await self.app(scope, receive, send_with_id)


class UnhandledExceptionMiddleware:
    """Catch any exception that escapes the inner app, log it, and return a 500.

    Sits inside ServerErrorMiddleware so the exception never propagates to uvicorn,
    which would log an unstructured 'Exception in ASGI application' trace.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Run the request, turning any exception that escapes into a logged 500 response."""
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        except Exception:
            logger.exception('Unhandled exception', extra={'path': scope['path']})
            body = ErrorResponse(code=ErrorCode.InternalError, details=['Internal server error'])
            response = JSONResponse(status_code=500, content=body.model_dump())
            await response(scope, receive, send)


class RequestLoggingMiddleware:
    """Log one structured line per HTTP request: request ID, method, path, status, and elapsed milliseconds."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Time the request and log it when it finishes, even if it raised; the status is 500 if no response started."""
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message['type'] == 'http.response.start':
                status_code = message['status']
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            logger.info(
                '',
                extra={
                    'request_id': scope.get('state', {}).get('request_id'),
                    'method': scope['method'],
                    'path': scope['path'],
                    'status': status_code,
                    'elapsed_ms': round((time.perf_counter() - start) * 1000),
                },
            )
