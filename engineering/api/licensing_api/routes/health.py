import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from licensing_api.dependencies import get_db_engine
from licensing_api.permissions import public

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/health', tags=['health'], dependencies=[public()])


class LiveResp(BaseModel):
    """The liveness response: ``status`` is always ``ok``."""

    status: str


class ReadyResp(BaseModel):
    """The readiness response: whether the database answered."""

    db: bool


async def check_postgres(engine: AsyncEngine) -> bool:
    """Whether the database answers ``SELECT 1``; logs the error and returns False if it does not."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text('SELECT 1'))
        return True
    except Exception:
        logger.error('Postgres health check failed', exc_info=True)
        return False


@router.get(
    path='/live',
    name='Liveness check',
    description='Check whether the application is ready to receive requests',
)
async def live() -> LiveResp:
    """Return ``ok`` whenever the application is serving requests."""
    return LiveResp(status='ok')


@router.get(
    path='/ready',
    name='Ready check',
    description='Check the database and other services are ready to accept requests',
)
async def ready(
    engine: Annotated[AsyncEngine, Depends(get_db_engine)],
) -> ReadyResp:
    """Return whether the database answers a query."""
    return ReadyResp(db=await check_postgres(engine))
