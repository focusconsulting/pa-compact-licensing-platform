from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


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


def get_redis(request: Request) -> aioredis.Redis:
    """
    Dependency that provides the Redis connection from the app state.
    """
    return request.app.state.redis
