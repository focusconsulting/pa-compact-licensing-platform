from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, Select, insert
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, col, select

from licensing_api.repo.base import DOTTED_NAME, TimestampTZ, entity_ref, utc_now

if TYPE_CHECKING:
    # Annotations only: licensing_api.context imports the repo package, so a runtime import would be circular.
    from licensing_api.context import ChangeContext


class AuditLogEntry(SQLModel, table=True):
    """A read of private data or a security event. Changes to records are in history, not here.

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
    """Record a staff read of private data or a security event on ``entity``, in the caller's transaction.

    For example ``ssn.revealed``, ``document.downloaded``, ``user.permissions_changed``.
    A change to a record is not audited: ``history.write`` records it. ``before`` and
    ``after`` are for security events on rows with no history, such as a permission
    change, and never hold an SSN or an expunged value (ADR-0007, ADR-0008).
    """
    if not DOTTED_NAME.fullmatch(action):
        raise ValueError(f'Audit action {action!r} must be "<entity>.<verb>" in lower snake case')
    await session.flush()
    ref = entity_ref(entity)
    statement = (
        insert(AuditLogEntry)
        .values(
            actor_user_id=ctx.user_id,
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
    return (await session.scalars(statement)).one()


def audit_entries(
    *,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    entity_key: str | None = None,
    actor_user_id: int | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> Select[tuple[AuditLogEntry]]:
    """Entries matching every filter given. ``occurred_to`` is exclusive."""
    statement = select(AuditLogEntry)
    filters = {
        col(AuditLogEntry.action): action,
        col(AuditLogEntry.entity_type): entity_type,
        col(AuditLogEntry.entity_id): entity_id,
        col(AuditLogEntry.entity_key): entity_key,
        col(AuditLogEntry.actor_user_id): actor_user_id,
    }
    for column, value in filters.items():
        if value is not None:
            statement = statement.where(column == value)
    if occurred_from is not None:
        statement = statement.where(col(AuditLogEntry.occurred_at) >= occurred_from)
    if occurred_to is not None:
        statement = statement.where(col(AuditLogEntry.occurred_at) < occurred_to)
    return statement
