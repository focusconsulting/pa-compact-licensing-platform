import asyncio
import logging
from collections.abc import Awaitable
from typing import Annotated, cast

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from licensing_api.dependencies import get_db_engine, get_redis
from licensing_api.routes.health_schemas import LiveResp, ReadyResp

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/health', tags=['health'])


async def check_postgres(engine: AsyncEngine) -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
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
    engine: Annotated[AsyncEngine, Depends(get_db_engine)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
) -> ReadyResp:
    db_ok, cache_ok = await asyncio.gather(
        check_postgres(engine),
        check_redis(redis),
    )
    return ReadyResp(db=db_ok, cache=cache_ok)
