import logging
import time

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class UnhandledExceptionMiddleware:
    """Catch any exception that escapes the inner app, log it, and return a 500.

    Sits inside ServerErrorMiddleware so the exception never propagates to uvicorn,
    which would log an unstructured 'Exception in ASGI application' trace.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        try:
            await self.app(scope, receive, send)
        except Exception:
            logger.exception('Unhandled exception', extra={'path': scope['path']})
            response = JSONResponse(status_code=500, content={'detail': 'Internal server error'})
            await response(scope, receive, send)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
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
                    'method': scope['method'],
                    'path': scope['path'],
                    'status': status_code,
                    'elapsed_ms': round((time.perf_counter() - start) * 1000),
                },
            )
