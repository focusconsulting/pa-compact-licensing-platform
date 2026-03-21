from contextvars import ContextVar
from typing import Any

from sqlalchemy.orm import Session

from licensing_api.utils.logging import get_logger

logger = get_logger(__name__)

_request_session: ContextVar[Session | None] = ContextVar("request_session", default=None)


def get_request_db_session() -> Session | None:
    """Get the session for the current request context."""
    return _request_session.get()


class DbSessionMiddleware:
    def __init__(self, app: Any, db_session_factory: Any) -> None:
        self.app = app
        self.db_session_factory = db_session_factory

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        session: Session = self.db_session_factory()
        token = _request_session.set(session)
        try:
            await self.app(scope, receive, send)
            if session.is_active:
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            _request_session.reset(token)
