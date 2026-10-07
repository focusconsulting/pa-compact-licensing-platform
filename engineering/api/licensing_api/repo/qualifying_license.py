from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field

from licensing_api.repo.base import AuditColumns, TimestampTZ


class LicenseStatus(StrEnum):
    """The status the issuing state reports (FLOW-05). Reinstatement returns a license to ``active``."""

    ACTIVE = 'active'
    EXPIRED = 'expired'
    LAPSED = 'lapsed'
    INACTIVE = 'inactive'
    TERMINATED = 'terminated'


class LicenseSource(StrEnum):
    MANUAL = 'manual'
    UPLOAD = 'upload'
    API = 'api'


class QualifyingLicense(AuditColumns, table=True):
    """A state PA license, authored by the issuing state (Rule 4 §4.3(c)(11)). Owner: epic 7.

    ``state_reported_status`` is what the state says; whether the license is in
    effect on a given day is computed (F-02 phase 3). ``terminated_on`` records a
    voluntary termination by the PA (Rule 3 §3.5(a), §3.6(a)).
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'qualifying_licenses'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    public_id: UUID = Field(default_factory=uuid4, unique=True)
    practitioner_id: int | None = Field(default=None, foreign_key='practitioners.id')
    state_code: str = Field(foreign_key='states.code')
    license_number: str
    state_reported_status: str
    status_effective_on: date
    issued_on: date | None = None
    expires_on: date | None = None
    is_unrestricted: bool
    terminated_on: date | None = None
    source: str = LicenseSource.MANUAL
    verified_by: int | None = Field(default=None, foreign_key='users.id')
    verified_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
