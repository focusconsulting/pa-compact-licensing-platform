from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field

from licensing_api.repo.base import AuditColumns, TimestampTZ


class AdministratorStatus(StrEnum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'


class DeactivationReason(StrEnum):
    """Why a privilege was deactivated (FLOW-05, FLOW-06). None of these reactivates on its own."""

    QUALIFYING_LICENSE_ADVERSE_ACTION = 'qualifying_license_adverse_action'
    ELIGIBILITY_WITHDRAWN = 'eligibility_withdrawn'
    QUALIFYING_LICENSE_INACTIVE = 'qualifying_license_inactive'
    QUALIFYING_LICENSE_TERMINATED = 'qualifying_license_terminated'
    # A new state of qualifying license terminates existing privileges (Rule 3 §3.6(d)).
    SQL_CHANGED = 'sql_changed'
    STATE_DEACTIVATED = 'state_deactivated'


class Privilege(AuditColumns, table=True):
    """A compact privilege issued by a remote state (Rule 4 §4.3(d)). Owner: epic 8.

    ``expires_on`` is pinned from the request and inclusive. Whether a privilege
    is active, expired, encumbered, or inactive is computed (F-02 phase 3); only
    the state's own ``administrator_status`` is stored, with a reason and time
    exactly when it is ``inactive``.
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'privileges'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    public_id: UUID = Field(default_factory=uuid4, unique=True)
    privilege_request_id: int = Field(foreign_key='privilege_requests.id', unique=True)
    practitioner_id: int = Field(foreign_key='practitioners.id')
    remote_state_code: str = Field(foreign_key='states.code')
    qualifying_license_id: int = Field(foreign_key='qualifying_licenses.id')
    privilege_number: str = Field(unique=True)
    state_privilege_identifier: str | None = None
    issued_at: datetime = Field(sa_type=TimestampTZ)
    expires_on: date
    administrator_status: str = AdministratorStatus.ACTIVE
    deactivation_reason: str | None = None
    deactivated_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    deactivation_note: str | None = None
