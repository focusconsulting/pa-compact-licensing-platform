from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, col, select

from licensing_api.context import ChangeContext, actor_id
from licensing_api.repo.base import AuditColumns, TimestampTZ


class NotificationStatus(StrEnum):
    PENDING = 'pending'
    SENT = 'sent'
    FAILED = 'failed'


class Notification(AuditColumns, table=True):
    """An email the worker sends; requests only write the row (D7).

    ``idempotency_key`` makes a repeated request send once. ``sent_at`` is set
    exactly when ``status`` is ``sent`` (``chk_notifications_sent_at``).
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'notifications'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    public_id: UUID = Field(default_factory=uuid4, unique=True)
    template: str
    recipient_user_id: int | None = Field(default=None, foreign_key='users.id')
    recipient_email: str
    context: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    idempotency_key: str = Field(unique=True)
    status: str = NotificationStatus.PENDING
    attempts: int = 0
    last_error: str | None = None
    sent_at: datetime | None = Field(default=None, sa_type=TimestampTZ)


async def notify(
    session: AsyncSession,
    ctx: ChangeContext,
    *,
    template: str,
    recipient_email: str,
    recipient_user_id: int | None = None,
    context: Mapping[str, Any],
    idempotency_key: str,
) -> Notification:
    """Queue one email for the Worker to send (D7), in the caller's transaction.

    A repeated ``idempotency_key`` queues nothing and returns the row already queued
    under it, so a handler that runs twice sends once. The address is copied now: the
    rules send to "the e-mail address currently on-file" (Rule 3 §3.5(b)). Called by
    event handlers, not by routes (FLOW-07).
    """
    statement = (
        insert(Notification)
        .values(
            template=template,
            recipient_user_id=recipient_user_id,
            recipient_email=recipient_email,
            context=dict(context),
            idempotency_key=idempotency_key,
            created_by=actor_id(ctx.actor),
        )
        .on_conflict_do_nothing(index_elements=['idempotency_key'])
        .returning(Notification)
    )
    queued = (await session.scalars(statement)).one_or_none()
    if queued is not None:
        return queued
    existing = select(Notification).where(col(Notification.idempotency_key) == idempotency_key)
    return (await session.scalars(existing)).one()
