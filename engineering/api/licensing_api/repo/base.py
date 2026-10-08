from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlmodel import Field, SQLModel


class TimestampTZ(DateTime):
    """Every instant is timestamptz (Principle XIII); SQLModel's default for datetime is a naive TIMESTAMP.

    A class rather than ``DateTime(timezone=True)`` because SQLModel's ``sa_type``
    takes a type class, which SQLAlchemy instantiates without arguments.
    """

    def __init__(self) -> None:
        super().__init__(timezone=True)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuditColumns(SQLModel):
    """Columns every table carries (ADR-0005).

    ``updated_at`` and ``updated_by`` may be left unset on insert: the
    ``set_audit_columns`` trigger copies them from ``created_at`` and ``created_by``.
    On update the trigger stamps ``updated_at``; the caller sets ``updated_by``
    from the token (ADR-0004).
    """

    created_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ)
    created_by: int = Field(foreign_key='users.id')
    updated_at: datetime | None = Field(default=None, nullable=False, sa_type=TimestampTZ)
    updated_by: int | None = Field(default=None, foreign_key='users.id', nullable=False)
