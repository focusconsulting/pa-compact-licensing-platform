"""The PA's dashboard: their license, applications, privileges, and what they can do next (SCRUM-112).

Every timeline is read from history rows, never from events, and every status is the one the
database stores or computes on read (D1).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.days import compact_today, days_between
from licensing_api.dependencies import get_db_session
from licensing_api.errors import AppError, ErrorCode
from licensing_api.permissions import Permission, require
from licensing_api.repo.history import ParticipationApplicationHistory, PrivilegeHistory
from licensing_api.repo.participation_application import (
    ApplicationKind,
    ApplicationStatus,
    ParticipationApplication,
)
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.privilege import Privilege
from licensing_api.repo.qualifying_license import QualifyingLicense
from licensing_api.repo.reference import RefDenialReason
from licensing_api.repo.status import CompactEligibility, PrivilegeStatus, QualifyingLicenseStatus
from licensing_api.repo.user import User
from licensing_api.responses import Data, example

me = APIRouter(prefix='/dashboard')


class ActionKind(StrEnum):
    """The one thing the dashboard offers next."""

    APPLY_FOR_PARTICIPATION = 'apply_for_participation'
    APPLY_FOR_PRIVILEGES = 'apply_for_privileges'


class UnavailableReason(StrEnum):
    """Why the PA cannot apply for privileges yet."""

    APPLICATION_IN_REVIEW = 'application_in_review'
    INFORMATION_REQUESTED = 'information_requested'
    NOT_YET_ELIGIBLE = 'not_yet_eligible'
    # Within two years of a restriction ending (ML §4.A(8)).
    TWO_YEAR_BAR = 'two_year_bar'
    ELIGIBILITY_WITHDRAWN = 'eligibility_withdrawn'


class Action(BaseModel):
    """The primary action, and when it is unavailable, every reason why."""

    kind: ActionKind
    available: bool
    reasons: list[UnavailableReason]


class ApplicationEvent(BaseModel):
    """One step in an application's history. ``note`` is the state's request when it asked for information."""

    status: ApplicationStatus
    at: datetime
    note: str | None = None


class ApplicationSummary(BaseModel):
    """An application, its decision, and its timeline, oldest first."""

    id: UUID
    kind: ApplicationKind
    status: ApplicationStatus
    sql_state_code: str
    claimed_license_number: str | None
    opened_at: datetime | None
    decided_at: datetime | None
    withdrawn_at: datetime | None
    denial_reason: str | None
    denial_reason_detail: str | None
    timeline: list[ApplicationEvent]


class QualifyingLicenseSummary(BaseModel):
    """The license the PA's eligibility rests on, and when its state verified it."""

    state_code: str
    license_number: str
    expires_on: date | None
    status: str
    verified_by_state: str | None
    verified_at: datetime | None


class PrivilegeEvent(BaseModel):
    """One change to a privilege: its issue, or a change of administrator status."""

    administrator_status: str
    at: datetime
    reason: str | None = None


class PrivilegeSummary(BaseModel):
    """A privilege as its holder sees it. ``expires_in_days`` counts from today in the compact's time zone."""

    id: UUID
    remote_state_code: str
    privilege_number: str
    status: str
    issued_at: datetime
    expires_on: date
    expires_in_days: int
    history: list[PrivilegeEvent]


_AT = datetime.fromisoformat('2026-10-14T15:00:00Z')


class Dashboard(BaseModel):
    """Everything the PA's dashboard shows, read from the database on each request."""

    model_config = ConfigDict(
        json_schema_extra=example(
            qualifying_license=None,
            applications=[
                {
                    'id': UUID('3d7e2a91-6b0c-4f58-a2e4-9c1b8f0d5e36'),
                    'kind': ApplicationKind.INITIAL,
                    'status': ApplicationStatus.SUBMITTED,
                    'sql_state_code': 'KS',
                    'claimed_license_number': 'PA-000123',
                    'opened_at': _AT,
                    'decided_at': None,
                    'withdrawn_at': None,
                    'denial_reason': None,
                    'denial_reason_detail': None,
                    'timeline': [{'status': ApplicationStatus.SUBMITTED, 'at': _AT}],
                }
            ],
            privileges=[],
            primary_action={
                'kind': ActionKind.APPLY_FOR_PRIVILEGES,
                'available': False,
                'reasons': [UnavailableReason.APPLICATION_IN_REVIEW],
            },
        )
    )

    qualifying_license: QualifyingLicenseSummary | None
    applications: list[ApplicationSummary] = Field(description='Newest first')
    privileges: list[PrivilegeSummary]
    primary_action: Action


@me.get(
    '',
    name='Get my dashboard',
    description='Your license, applications, privileges, and what you can do next.',
)
async def get_my_dashboard(
    caller: Annotated[User, require(Permission.MANAGE_OWN_RECORD)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[Dashboard]:
    """One read of the PA's records; nothing is cached."""
    practitioner_id = (
        await session.scalars(
            select(col(Practitioner.id)).where(col(Practitioner.user_id) == caller.id)
        )
    ).one_or_none()
    if practitioner_id is None:
        raise AppError(404, ErrorCode.NotFound, ['You have no practitioner record'])
    applications = list(
        (
            await session.scalars(
                select(ParticipationApplication)
                .where(col(ParticipationApplication.practitioner_id) == practitioner_id)
                .order_by(
                    col(ParticipationApplication.created_at).desc(),
                    col(ParticipationApplication.id).desc(),
                )
            )
        ).all()
    )
    barred = await session.get(CompactEligibility, practitioner_id)
    return Data(
        data=Dashboard(
            qualifying_license=await _license(session, applications),
            applications=[await _application(session, a) for a in applications],
            privileges=await _privileges(session, practitioner_id),
            primary_action=_primary_action(applications, barred is not None and barred.is_barred),
        )
    )


def _primary_action(applications: list[ParticipationApplication], barred: bool) -> Action:
    """Apply for privileges once eligible, or once an application could make the PA eligible; else apply to participate.

    A pending change of state of qualifying license does not block privileges: the PA stays
    eligible through their current state until the new one decides (Rule 3 §3.6).
    """
    statuses = [a.status for a in applications]
    eligible = ApplicationStatus.ELIGIBLE in statuses
    pending = None
    if not eligible:
        if ApplicationStatus.SUBMITTED in statuses:
            pending = UnavailableReason.APPLICATION_IN_REVIEW
        elif ApplicationStatus.INFO_REQUESTED in statuses:
            pending = UnavailableReason.INFORMATION_REQUESTED
        elif statuses[:1] == [ApplicationStatus.ELIGIBILITY_WITHDRAWN]:
            pending = UnavailableReason.ELIGIBILITY_WITHDRAWN
        else:
            return Action(kind=ActionKind.APPLY_FOR_PARTICIPATION, available=True, reasons=[])
    reasons = [] if eligible else [UnavailableReason.NOT_YET_ELIGIBLE, pending]
    if barred:
        reasons.append(UnavailableReason.TWO_YEAR_BAR)
    return Action(kind=ActionKind.APPLY_FOR_PRIVILEGES, available=not reasons, reasons=reasons)


async def _license(
    session: AsyncSession, applications: list[ParticipationApplication]
) -> QualifyingLicenseSummary | None:
    """The license linked to the current eligible application, or else to the newest one that has one."""
    linked = sorted(
        (a for a in applications if a.qualifying_license_id is not None),
        key=lambda a: a.status != ApplicationStatus.ELIGIBLE,
    )
    if not linked:
        return None
    application = linked[0]
    license = await session.get(QualifyingLicense, application.qualifying_license_id)
    status = await session.get(QualifyingLicenseStatus, application.qualifying_license_id)
    assert license is not None and status is not None
    return QualifyingLicenseSummary(
        state_code=license.state_code,
        license_number=license.license_number,
        expires_on=license.expires_on,
        status=status.status,
        verified_by_state=application.sql_state_code if application.license_verified_at else None,
        verified_at=application.license_verified_at,
    )


async def _application(
    session: AsyncSession, application: ParticipationApplication
) -> ApplicationSummary:
    rows = (
        await session.scalars(
            select(ParticipationApplicationHistory)
            .where(col(ParticipationApplicationHistory.entity_id) == application.id)
            .order_by(
                col(ParticipationApplicationHistory.changed_at),
                col(ParticipationApplicationHistory.id),
            )
        )
    ).all()
    timeline = [_application_event(row.changed_at, row.updated or {}) for row in rows]
    denial = (
        await session.get(RefDenialReason, application.denial_reason_code)
        if application.denial_reason_code
        else None
    )
    return ApplicationSummary(
        id=application.public_id,
        kind=ApplicationKind(application.kind),
        status=ApplicationStatus(application.status),
        sql_state_code=application.sql_state_code,
        claimed_license_number=application.claimed_license_number,
        opened_at=application.opened_at,
        decided_at=application.decided_at,
        withdrawn_at=application.withdrawn_at,
        denial_reason=denial.label if denial else None,
        denial_reason_detail=application.denial_reason_detail,
        timeline=[event for event in timeline if event is not None],
    )


def _application_event(at: datetime, updated: dict[str, Any]) -> ApplicationEvent | None:
    """A history row that changed the status is a step; one that changed only other fields is not."""
    if 'status' not in updated:
        return None
    status = ApplicationStatus(updated['status'])
    note = updated.get('request_note') if status == ApplicationStatus.INFO_REQUESTED else None
    return ApplicationEvent(status=status, at=at, note=note)


async def _privileges(session: AsyncSession, practitioner_id: int) -> list[PrivilegeSummary]:
    today = await compact_today(session)
    rows = (
        await session.execute(
            select(Privilege, PrivilegeStatus.status)
            .join(PrivilegeStatus, col(PrivilegeStatus.privilege_id) == col(Privilege.id))
            .where(col(Privilege.practitioner_id) == practitioner_id)
            .order_by(col(Privilege.issued_at).desc(), col(Privilege.id).desc())
        )
    ).all()
    summaries = []
    for privilege, status in rows:
        history = (
            await session.scalars(
                select(PrivilegeHistory)
                .where(col(PrivilegeHistory.entity_id) == privilege.id)
                .order_by(col(PrivilegeHistory.changed_at), col(PrivilegeHistory.id))
            )
        ).all()
        summaries.append(
            PrivilegeSummary(
                id=privilege.public_id,
                remote_state_code=privilege.remote_state_code,
                privilege_number=privilege.privilege_number,
                status=status,
                issued_at=privilege.issued_at,
                expires_on=privilege.expires_on,
                expires_in_days=days_between(today, privilege.expires_on),
                history=[
                    PrivilegeEvent(
                        administrator_status=row.updated['administrator_status'],
                        at=row.changed_at,
                        reason=row.updated.get('deactivation_reason'),
                    )
                    for row in history
                    if row.updated and 'administrator_status' in row.updated
                ],
            )
        )
    return summaries
