"""Who is making a change and in which request: passed to every write helper (ADR-0009)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import ScalarSelect
from sqlmodel import col, select

from licensing_api.auth import AuthClaims, get_auth_claims
from licensing_api.repo.base import AuditColumns
from licensing_api.repo.user import SYSTEM_USER_EMAIL, User


@dataclass(frozen=True)
class Actor:
    """A signed-in user by Cognito ``sub``, or the system user when ``sub`` is None."""

    sub: UUID | None


SYSTEM = Actor(sub=None)


def actor_id(actor: Actor) -> ScalarSelect[int]:
    """``users.id`` for ``actor`` as a subquery, so the write resolves it in the same statement (ADR-0004)."""
    if actor.sub is None:
        return select(col(User.id)).where(col(User.email) == SYSTEM_USER_EMAIL).scalar_subquery()
    return select(col(User.id)).where(col(User.public_id) == actor.sub).scalar_subquery()


class UnknownActorError(LookupError):
    """The actor's ``sub`` matches no user, so the write could not be attributed. The caller's transaction must not commit."""


def require_attributed(actor: Actor, resolved_id: int | None) -> int:
    """The id a write resolved for ``actor``; raises ``UnknownActorError`` when it resolved none.

    For columns that allow NULL (``audit_log.actor_user_id``, ``domain_events.actor_user_id``),
    where an unknown actor would otherwise be recorded as no one.
    """
    if resolved_id is None:
        raise UnknownActorError(f'No user has sub {actor.sub}; the change cannot be attributed')
    return resolved_id


@dataclass(frozen=True)
class ChangeContext:
    actor: Actor
    request_id: str | None


async def change_context(
    request: Request, claims: Annotated[AuthClaims, Depends(get_auth_claims)]
) -> ChangeContext:
    """The context for writes made on behalf of this request's caller."""
    return ChangeContext(actor=Actor(sub=claims.sub), request_id=request_id_of(request))


def stamp_update(entity: AuditColumns, ctx: ChangeContext) -> None:
    """Set ``updated_by`` to the context's actor on a changed row; the flush resolves it (ADR-0004).

    The attribute is expired after the flush: refresh the row before reading it.
    """
    # setattr: the column is typed int, and SQLAlchemy accepts a SQL expression in its place at flush.
    setattr(entity, 'updated_by', actor_id(ctx.actor))  # noqa: B010


def system_context(request_id: str | None = None) -> ChangeContext:
    """The context for writes made by the Worker and jobs, as the system user (ADR-0005)."""
    return ChangeContext(actor=SYSTEM, request_id=request_id)


def request_id_of(request: Request) -> str | None:
    """The ID ``RequestIdMiddleware`` gave this request."""
    return getattr(request.state, 'request_id', None)
