from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlmodel import Field

from licensing_api.repo.base import AuditColumns, TimestampTZ, utc_now


class SiiReport(AuditColumns, table=True):
    """A report that significant investigative information exists about a PA (Rule 4 §4.4(c)-(d)). Owner: epic 9.

    Tier: states and Commission only; never the PA or the public (ML §8.C). Kept
    apart from ``adverse_actions`` so no adverse-action query can return it by
    accident. Either the state of qualifying license or a remote state may report.
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'sii_reports'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    public_id: UUID = Field(default_factory=uuid4, unique=True)
    practitioner_id: int = Field(foreign_key='practitioners.id')
    reporting_state_code: str = Field(foreign_key='states.code')
    qualifying_license_id: int | None = Field(default=None, foreign_key='qualifying_licenses.id')
    privilege_id: int | None = Field(default=None, foreign_key='privileges.id')
    description: str
    contact_name: str
    contact_email: str | None = None
    contact_phone: str | None = None
    public_complaint_document_id: int | None = Field(default=None, foreign_key='documents.id')
    determined_on: date
    reported_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ)
    closed_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    closed_by: int | None = Field(default=None, foreign_key='users.id')
