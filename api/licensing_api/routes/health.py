import asyncio
import logging
from collections.abc import Awaitable
from typing import Annotated, cast

import asyncpg
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends

from licensing_api.dependencies import get_db_pool, get_redis
from licensing_api.routes.health_schemas import LiveResp, ReadyResp

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/health', tags=['health'])


async def check_postgres(pool: asyncpg.Pool) -> bool:
    try:
        async with pool.acquire() as conn:
            await conn.execute('SELECT 1')
        return True
    except Exception:
        logger.error('Postgres health check failed', exc_info=True)
        return False


async def check_redis(redis: aioredis.Redis) -> bool:
    try:
        await cast(Awaitable[bool], redis.ping())
        return True
    except Exception:
        logger.error('Redis health check failed', exc_info=True)
        return False


@router.get(
    path='/live',
    name='Liveness check',
    description='Check whether the application is ready to receive requests',
)
async def live() -> LiveResp:
    return LiveResp(status='ok')


@router.get(
    path='/ready',
    name='Ready check',
    description='Check the database and cache are ready to accept requests',
)
async def ready(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> ReadyResp:
    db_ok, cache_ok = await asyncio.gather(
        check_postgres(pool),
        check_redis(redis),
    )
    return ReadyResp(db=db_ok, cache=cache_ok)
