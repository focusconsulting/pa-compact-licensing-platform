from __future__ import annotations

from sqlmodel import Field

from licensing_api.repo.base import AuditColumns

COMPACT_SETTINGS_ID = 1


class CompactSettings(AuditColumns, table=True):
    """The single row of compact-wide configuration.

    ``time_zone`` is the reference time zone that decides which calendar day an
    instant falls on, for every status and day count (ADR-0006). Later epics add
    the Commission fee and similar settings here.
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'compact_settings'  # type: ignore[assignment]

    id: int = Field(default=COMPACT_SETTINGS_ID, primary_key=True)
    time_zone: str = 'America/New_York'
