import asyncpg
import redis.asyncio as aioredis
from fastapi import Request


def get_db_pool(request: Request) -> asyncpg.Pool:
    """
    Dependency that provides the database connection pool from the app state.
    """
    return request.app.state.db_pool


def get_redis(request: Request) -> aioredis.Redis:
    """
    Dependency that provides the Redis connection from the app state.
    """
    return request.app.state.redis
