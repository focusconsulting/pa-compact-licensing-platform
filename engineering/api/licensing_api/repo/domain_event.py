from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Column, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from licensing_api.repo.base import TimestampTZ, utc_now


class DomainEvent(SQLModel, table=True):
    """A state change, written in the same transaction as the change itself (the transactional outbox, D2).

    ``payload`` carries IDs, never PII. Every event type is listed in FLOW-07's catalogue.
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'domain_events'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    event_id: UUID = Field(default_factory=uuid4, unique=True)
    type: str
    aggregate_type: str
    aggregate_id: int
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    actor_user_id: int | None = Field(default=None, foreign_key='users.id')
    request_id: str | None = None
    occurred_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ)


class DomainEventDelivery(SQLModel, table=True):
    """One handler's progress on one event. Handlers are idempotent on ``(event_id, handler)``."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'domain_event_deliveries'  # type: ignore[assignment]

    event_id: UUID = Field(primary_key=True, foreign_key='domain_events.event_id')
    handler: str = Field(primary_key=True)
    attempts: int = 0
    last_error: str | None = None
    handled_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    dead_lettered_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    created_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ)
