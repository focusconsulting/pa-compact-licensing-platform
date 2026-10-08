from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from licensing_api.repo.base import TimestampTZ, utc_now


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
