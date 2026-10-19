"""Who is making a change and in which request: passed to every write helper (ADR-0009)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.auth import AuthClaims, get_auth_claims
from licensing_api.dependencies import get_db_session
from licensing_api.errors import AppError, ErrorCode
from licensing_api.repo.user import (
    SYSTEM_USER_EMAIL,
    User,
    get_user_by_email,
    get_user_by_public_id,
)


@dataclass(frozen=True)
class ChangeContext:
    """``user_id`` is the ``users.id`` written to audit columns, history, events, and the audit log."""

    user_id: int
    request_id: str | None


async def current_user(
    claims: Annotated[AuthClaims, Depends(get_auth_claims)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    """The active user the token belongs to, linking the token's ``sub`` on first sign-in (ADR-0009).

    A user is linked by email only while they have no ``sub``: a user already linked to
    another ``sub`` (the same email in the other Cognito pool, D4) is not this caller.
    FastAPI runs this once per request, however many dependencies ask for it.
    """
    user = await get_user_by_public_id(session, claims.sub)
    if user is None:
        user = await get_user_by_email(session, claims.email)
        if user is None or user.public_id is not None:
            raise AppError(403, ErrorCode.UserNotFound, ['User not found'])
        if user.is_active:
            user.public_id = claims.sub
            await session.commit()
    if not user.is_active:
        raise AppError(403, ErrorCode.UserInactive, ['User is inactive'])
    return user


async def change_context(
    request: Request, user: Annotated[User, Depends(current_user)]
) -> ChangeContext:
    """The context for writes made on behalf of this request's caller."""
    return ChangeContext(user_id=user.id, request_id=request_id_of(request))


async def system_context(session: AsyncSession, request_id: str | None = None) -> ChangeContext:
    """The context for writes made by the Worker and jobs, as the system user (ADR-0005)."""
    statement = select(col(User.id)).where(col(User.email) == SYSTEM_USER_EMAIL)
    return ChangeContext(user_id=(await session.scalars(statement)).one(), request_id=request_id)


def request_id_of(request: Request) -> str | None:
    """The ID ``RequestIdMiddleware`` gave this request."""
    return getattr(request.state, 'request_id', None)
