"""History tables: one append-only row per change to an entity (ADR-0005, ADR-0008).

F-05's ``history.write()`` fills ``previous``, ``updated``, and ``removed`` with
the changed fields. Rows can only be redacted, inside an expungement transaction.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from licensing_api.repo.base import TimestampTZ, utc_now


class HistoryRecord(SQLModel):
    """Columns shared by every history table. Each subclass adds ``entity_id`` pointing at its entity.

    JSON fields use ``sa_type``, not ``sa_column``: a Column object cannot be shared by several tables.
    """

    id: int | None = Field(default=None, primary_key=True)
    changed_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ)
    changed_by: int = Field(foreign_key='users.id')
    # When the change took effect, if different from when it was recorded.
    effective_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    previous: dict[str, Any] | None = Field(default=None, sa_type=JSONB)
    updated: dict[str, Any] | None = Field(default=None, sa_type=JSONB)
    removed: dict[str, Any] | None = Field(default=None, sa_type=JSONB)


class PractitionerHistory(HistoryRecord, table=True):
    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'practitioners_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='practitioners.id')


class QualifyingLicenseHistory(HistoryRecord, table=True):
    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'qualifying_licenses_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='qualifying_licenses.id')


class ParticipationApplicationHistory(HistoryRecord, table=True):
    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'participation_applications_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='participation_applications.id')


class PrivilegeRequestHistory(HistoryRecord, table=True):
    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'privilege_requests_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='privilege_requests.id')


class PrivilegeHistory(HistoryRecord, table=True):
    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'privileges_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='privileges.id')


class AdverseActionHistory(HistoryRecord, table=True):
    """Every update a reporting state makes to an adverse action (Rule 4 §4.4(b)(3))."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'adverse_actions_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='adverse_actions.id')


class SiiReportHistory(HistoryRecord, table=True):
    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'sii_reports_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='sii_reports.id')
