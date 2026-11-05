from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from licensing_api.storage import Storage


def get_db_engine(request: Request) -> AsyncEngine:
    """
    Dependency that provides the database engine from the app state.
    """
    return request.app.state.db_engine


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession]:
    """
    Dependency that provides a database session from the app state.
    """
    async with request.app.state.session_factory() as session:
        yield session


def get_storage(request: Request) -> Storage:
    """The documents bucket the app built at start-up."""
    return request.app.state.storage
