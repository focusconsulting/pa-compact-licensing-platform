from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field

from licensing_api.repo.base import AuditColumns, TimestampTZ


class ApplicationKind(StrEnum):
    INITIAL = 'initial'
    # Designating a new state of qualifying license (Rule 3 §3.6(a)).
    CHANGE_SQL = 'change_sql'


class ApplicationStatus(StrEnum):
    """The participation application's states (FLOW-06)."""

    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    INFO_REQUESTED = 'info_requested'
    ELIGIBLE = 'eligible'
    DENIED = 'denied'
    WITHDRAWN = 'withdrawn'
    ELIGIBILITY_WITHDRAWN = 'eligibility_withdrawn'


OPEN_APPLICATION_STATUSES = frozenset(
    {ApplicationStatus.DRAFT, ApplicationStatus.SUBMITTED, ApplicationStatus.INFO_REQUESTED}
)


class ParticipationApplication(AuditColumns, table=True):
    """A PA's application to participate in the compact, decided by their state of qualifying license (FLOW-02).

    Owner: epic 6. The database enforces the decision rules: an eligible decision
    needs the license verified and the background check's completion date; a
    denial needs a reason; a practitioner has at most one open application.
    ``cbc_completed_on`` is a date only, never a result (Rule 4 §4.2).
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'participation_applications'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    public_id: UUID = Field(default_factory=uuid4, unique=True)
    practitioner_id: int = Field(foreign_key='practitioners.id')
    kind: str = ApplicationKind.INITIAL
    sql_state_code: str = Field(foreign_key='states.code')
    qualifying_license_id: int | None = Field(default=None, foreign_key='qualifying_licenses.id')
    status: str = ApplicationStatus.DRAFT
    opened_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    request_note: str | None = None
    license_verified_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    license_verified_by: int | None = Field(default=None, foreign_key='users.id')
    cbc_completed_on: date | None = None
    decided_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    decided_by: int | None = Field(default=None, foreign_key='users.id')
    denial_reason_code: str | None = Field(default=None, foreign_key='ref_denial_reasons.code')
    denial_reason_detail: str | None = None
    withdrawn_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    eligibility_withdrawn_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    eligibility_withdrawal_reason: str | None = None
