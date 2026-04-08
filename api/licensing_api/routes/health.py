import asyncio
from collections.abc import Awaitable
from typing import cast

import asyncpg
import redis.asyncio as aioredis
from fastapi import APIRouter

from licensing_api.dependencies import DbPool, RedisCli
from licensing_api.routes.health_schemas import LiveResp, ReadyResp

router = APIRouter(prefix='/health', tags=['health'])


async def check_postgres(pool: asyncpg.Pool) -> bool:
    try:
        async with pool.acquire() as conn:
            await conn.execute('SELECT 1')
        return True
    except Exception:
        return False


async def check_redis(redis: aioredis.Redis) -> bool:
    try:
        await cast(Awaitable[bool], redis.ping())
        return True
    except Exception:
        return False


@router.get(
    path='/live',
    name='Liveness check',
    description='Check whether the application is ready to receive requests',
    response_model=LiveResp,
)
async def live() -> LiveResp:
    return LiveResp(status='ok')


@router.get(
    path='/ready',
    name='Ready check',
    description='Check the database and cache are ready to accept requests',
    response_model=ReadyResp,
)
async def ready(pool: DbPool, redis: RedisCli) -> ReadyResp:
    db_ok, cache_ok = await asyncio.gather(
        check_postgres(pool),
        check_redis(redis),
    )
    return ReadyResp(db=db_ok, cache=cache_ok)
