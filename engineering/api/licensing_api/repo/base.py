from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import DateTime, inspect
from sqlmodel import Field, SQLModel

# '<owning module>.<what>' in lower snake case: handler names (data dictionary, domain_events) and audit actions.
DOTTED_NAME = re.compile(r'[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*')


class TimestampTZ(DateTime):
    """Every instant is timestamptz (Principle XIII); SQLModel's default for datetime is a naive TIMESTAMP.

    A class rather than ``DateTime(timezone=True)`` because SQLModel's ``sa_type``
    takes a type class, which SQLAlchemy instantiates without arguments.
    """

    def __init__(self) -> None:
        super().__init__(timezone=True)


def utc_now() -> datetime:
    """The current time as a timezone-aware UTC datetime; the default for timestamp columns."""
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


@dataclass(frozen=True)
class EntityRef:
    """A row as the outbox and the audit log reference it: ``id`` for a numeric key, ``key`` for a text one (ADR-0005)."""

    type: str
    id: int | None
    key: str | None


def entity_ref(entity: SQLModel) -> EntityRef:
    """The table and key of a flushed row. Raises ``ValueError`` for an unflushed row or a composite key."""
    state = inspect(entity, raiseerr=True)
    if state.identity is None:
        raise ValueError(f'{type(entity).__name__} has no key yet; flush it before referencing it')
    if len(state.identity) != 1:
        raise ValueError(f'{type(entity).__name__} has a composite key and cannot be referenced')
    table = str(state.mapper.local_table.description)
    value = state.identity[0]
    if isinstance(value, int):
        return EntityRef(type=table, id=value, key=None)
    return EntityRef(type=table, id=None, key=str(value))
