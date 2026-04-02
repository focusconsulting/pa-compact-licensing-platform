import asyncio
from collections.abc import Awaitable
from typing import cast

import asyncpg
import redis.asyncio as aioredis
from fastapi import APIRouter

from licensing_api.config import settings
from licensing_api.routes.health_schemas import LiveResp, ReadyResp

router = APIRouter(prefix='/health', tags=['health'])


async def check_postgres() -> bool:
    try:
        conn = await asyncpg.connect(settings.db_url)
        await conn.execute('SELECT 1')
        await conn.close()
        return True
    except Exception:
        return False


async def check_redis() -> bool:
    try:
        client = aioredis.from_url(settings.redis_url)
        await cast(Awaitable[bool], client.ping())
        await client.aclose()
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
async def ready() -> ReadyResp:
    db_ok, cache_ok = await asyncio.gather(check_postgres(), check_redis())
    return ReadyResp(db=db_ok, cache=cache_ok)
