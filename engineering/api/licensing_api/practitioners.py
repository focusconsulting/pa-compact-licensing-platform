"""The signed-in PA's own practitioner record, where every ``/me`` route about their record starts."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.errors import AppError, ErrorCode
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.user import User


async def own_practitioner(
    session: AsyncSession, caller: User, *, for_update: bool = False
) -> Practitioner:
    """The caller's practitioner record, or ``404 NOT_FOUND`` when they have none."""
    statement = select(Practitioner).where(col(Practitioner.user_id) == caller.id)
    if for_update:
        statement = statement.with_for_update()
    practitioner = (await session.scalars(statement)).one_or_none()
    if practitioner is None:
        raise AppError(404, ErrorCode.NotFound, ['You have no practitioner record'])
    return practitioner


async def own_practitioner_id(session: AsyncSession, caller: User) -> int:
    """The caller's practitioner ID, or ``404 NOT_FOUND`` when they have none."""
    practitioner_id = (
        await session.scalars(
            select(col(Practitioner.id)).where(col(Practitioner.user_id) == caller.id)
        )
    ).one_or_none()
    if practitioner_id is None:
        raise AppError(404, ErrorCode.NotFound, ['You have no practitioner record'])
    return practitioner_id
