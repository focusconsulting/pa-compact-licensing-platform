from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import Column, insert
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel

from licensing_api.context import ChangeContext, actor_id, require_attributed
from licensing_api.repo.base import DOTTED_NAME, TimestampTZ, entity_ref, utc_now


class AuditLogEntry(SQLModel, table=True):
    """One action a person or the system took, including staff reads of private data.

    Append-only: the ``prevent_mutation`` trigger rejects updates and deletes
    outside an expungement transaction (ADR-0008). A full SSN reveal is recorded
    here without the value (ADR-0007).
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'audit_log'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    occurred_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ)
    actor_user_id: int | None = Field(default=None, foreign_key='users.id')
    action: str
    entity_type: str
    # entity_id for records with a numeric id; entity_key for records keyed by text, such as a state.
    entity_id: int | None = None
    entity_key: str | None = None
    before: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    after: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    reason: str | None = None
    request_id: str | None = None


async def write(
    session: AsyncSession,
    ctx: ChangeContext,
    action: str,
    entity: SQLModel,
    *,
    before: Mapping[str, Any] | None = None,
    after: Mapping[str, Any] | None = None,
    reason: str | None = None,
) -> AuditLogEntry:
    """Record an action on ``entity``, including a staff read of private data, in the caller's transaction.

    ``action`` is ``<entity>.<verb>``, e.g. ``ssn.revealed``. ``before`` and ``after``
    must never hold an SSN or an expunged value (ADR-0007, ADR-0008).
    """
    if not DOTTED_NAME.fullmatch(action):
        raise ValueError(f'Audit action {action!r} must be "<entity>.<verb>" in lower snake case')
    await session.flush()
    ref = entity_ref(entity)
    statement = (
        insert(AuditLogEntry)
        .values(
            actor_user_id=actor_id(ctx.actor),
            action=action,
            entity_type=ref.type,
            entity_id=ref.id,
            entity_key=ref.key,
            before=dict(before) if before is not None else None,
            after=dict(after) if after is not None else None,
            reason=reason,
            request_id=ctx.request_id,
        )
        .returning(AuditLogEntry)
    )
    entry = (await session.scalars(statement)).one()
    require_attributed(ctx.actor, entry.actor_user_id)
    return entry
