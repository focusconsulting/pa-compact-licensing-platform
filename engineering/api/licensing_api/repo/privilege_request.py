from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field

from licensing_api.repo.base import AuditColumns, TimestampTZ


class PrivilegeRequestStatus(StrEnum):
    """A privilege request's states (FLOW-06).

    ``withdrawn`` replaces FLOW-06's ``abandoned``: Rule 3 §3.7(b)(1) says an
    incomplete request is "deemed incomplete and to have been withdrawn".
    """

    PENDING_PAYMENT = 'pending_payment'
    SUBMITTED = 'submitted'
    ISSUED = 'issued'
    DENIED = 'denied'
    WITHDRAWN = 'withdrawn'


OPEN_REQUEST_STATUSES = frozenset(
    {PrivilegeRequestStatus.PENDING_PAYMENT, PrivilegeRequestStatus.SUBMITTED}
)


class PrivilegeRequest(AuditColumns, table=True):
    """A PA's request for a compact privilege in one remote state (FLOW-03). Owner: epic 8.

    ``ql_expires_on_snapshot`` is the qualifying license's expiry when the PA
    applied; the privilege, if issued, expires that day whatever happens to the
    license later (Rule 3 §3.5(a)). The database requires it, and ``submitted_at``,
    once the request leaves ``pending_payment``. A practitioner has at most one
    open request per remote state.
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'privilege_requests'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    public_id: UUID = Field(default_factory=uuid4, unique=True)
    participation_application_id: int = Field(foreign_key='participation_applications.id')
    practitioner_id: int = Field(foreign_key='practitioners.id')
    remote_state_code: str = Field(foreign_key='states.code')
    qualifying_license_id: int = Field(foreign_key='qualifying_licenses.id')
    status: str = PrivilegeRequestStatus.PENDING_PAYMENT
    ql_expires_on_snapshot: date | None = None
    submitted_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    decided_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    decided_by: int | None = Field(default=None, foreign_key='users.id')
    denial_reason_code: str | None = Field(default=None, foreign_key='ref_denial_reasons.code')
    denial_reason_detail: str | None = None
    withdrawn_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
