"""What the API task is running, for the system admin: its version, uptime, and database.

This sits behind ``system_admin`` rather than on the public health checks, which answer anyone
through CloudFront: a version there tells an attacker what is running (OWASP ASVS V14.3).
"""

import logging
import time
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from licensing_api.config import Settings, get_settings
from licensing_api.dependencies import get_db_engine
from licensing_api.permissions import Permission, require
from licensing_api.repo.user import User
from licensing_api.responses import Data, example

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/status')


class DatabaseStatus(BaseModel):
    """Whether the database answered, how fast, and the newest migration applied to it."""

    reachable: bool
    latency_ms: float | None
    latest_migration: str | None


class StatusOut(BaseModel):
    """The task answering this request; another task behind the load balancer may differ."""

    model_config = ConfigDict(
        json_schema_extra=example(
            version='3f2a9c1d8e7b6a5f4e3d2c1b0a9f8e7d6c5b4a39',
            environment='STAGING',
            started_at='2026-11-16T21:46:19Z',
            uptime_seconds=3600,
            database={
                'reachable': True,
                'latency_ms': 1.8,
                'latest_migration': '20261112_110000_practitioner_other_names',
            },
        )
    )

    version: str
    environment: Literal['LOCAL_DEV', 'STAGING', 'PROD']
    started_at: datetime
    uptime_seconds: int
    database: DatabaseStatus


async def _database(engine: AsyncEngine) -> DatabaseStatus:
    try:
        async with engine.connect() as conn:
            began = time.perf_counter()
            await conn.execute(text('SELECT 1'))
            latency_ms = round((time.perf_counter() - began) * 1000, 1)
            # Raw SQL: yoyo owns this table, and the API has no model for it.
            latest = await conn.scalar(text('SELECT max(migration_id) FROM _yoyo_migration'))
    except (SQLAlchemyError, OSError):
        logger.error('Status check could not reach the database', exc_info=True)
        return DatabaseStatus(reachable=False, latency_ms=None, latest_migration=None)
    return DatabaseStatus(reachable=True, latency_ms=latency_ms, latest_migration=latest)


@router.get(
    '',
    name='Get the system status',
    description=(
        'The deployed version, environment, when this task started and how long it has run, and '
        "the database's response time and newest migration. Needs `system_admin`."
    ),
)
async def get_status(
    request: Request,
    _: Annotated[User, require(Permission.SYSTEM_ADMIN)],
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[AsyncEngine, Depends(get_db_engine)],
) -> Data[StatusOut]:
    """Read from app state set at startup, and one round trip to the database."""
    state = request.app.state
    return Data(
        data=StatusOut(
            version=settings.app_version,
            environment=settings.environment,
            started_at=state.started_at,
            uptime_seconds=int(time.monotonic() - state.started_monotonic),
            database=await _database(engine),
        )
    )
