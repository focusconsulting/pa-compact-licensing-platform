from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

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
