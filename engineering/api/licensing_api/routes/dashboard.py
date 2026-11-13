"""The PA's dashboard: their license, applications, privileges, and what they can do next (SCRUM-112).

Every timeline is read from history rows, never from events, and every status is the one the
database stores or computes on read (D1).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.days import (
    add_days,
    compact_date_at,
    compact_today,
    days_between,
    reference_time_zone,
)
from licensing_api.dependencies import get_db_session
from licensing_api.permissions import Permission, require
from licensing_api.practitioners import own_practitioner_id
from licensing_api.repo.adverse_action import AdverseAction
from licensing_api.repo.history import ParticipationApplicationHistory, PrivilegeHistory
from licensing_api.repo.participation_application import (
    ApplicationKind,
    ApplicationStatus,
    ParticipationApplication,
)
from licensing_api.repo.privilege import AdministratorStatus, Privilege
from licensing_api.repo.qualifying_license import QualifyingLicense
from licensing_api.repo.reference import RefDenialReason
from licensing_api.repo.status import (
    CompactEligibility,
    PrivilegeComputedStatus,
    PrivilegeStatus,
    QualifyingLicenseStatus,
)
from licensing_api.repo.user import SYSTEM_USER_EMAIL, User
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


# Rule 3 §3.7(a)(1): the state must have what it asked for within 60 days of the application.
_RESUBMIT_WITHIN_DAYS = 60


class EventKind(StrEnum):
    """What a step was, for the PA to read: worked out from history, never stored."""

    APPLIED = 'applied'
    # The first submit of an application after an earlier one was submitted.
    APPLIED_AGAIN = 'applied_again'
    RESUBMITTED = 'resubmitted'
    INFO_REQUESTED = 'info_requested'
    WITHDRAWN_BY_PA = 'withdrawn_by_pa'
    # Withdrawn by the system user: the 60 days ran out (Rule 3 §3.7(a)(1)).
    WITHDRAWN_BY_DEADLINE = 'withdrawn_by_deadline'
    ELIGIBLE = 'eligible'
    DENIED = 'denied'
    ELIGIBILITY_WITHDRAWN = 'eligibility_withdrawn'
    SUPERSEDED = 'superseded'


class ApplicationEvent(BaseModel):
    """One step in an application's history. ``note`` is the state's request when it asked for information."""

    kind: EventKind
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
    resubmit_by: date | None = Field(
        description='While information is requested, the last day the state must have it'
    )
    timeline: list[ApplicationEvent]


class QualifyingLicenseSummary(BaseModel):
    """The license the PA's eligibility rests on, and when its state, ``state_code``, verified it."""

    state_code: str
    license_number: str
    expires_on: date | None
    status: str
    verified_at: datetime | None


class PrivilegeEvent(BaseModel):
    """The day a privilege's status changed, and to what. ``reason`` is the deactivation reason when ``inactive``."""

    status: PrivilegeComputedStatus
    on: date
    reason: str | None = None


class PrivilegeSummary(BaseModel):
    """A privilege as its holder sees it. ``history`` is oldest first."""

    id: UUID
    remote_state_code: str
    privilege_number: str
    status: PrivilegeComputedStatus
    issued_at: datetime
    expires_on: date
    expires_in_days: int | None = Field(
        description="Days from today in the compact's time zone; null once it is inactive or expired"
    )
    history: list[PrivilegeEvent]


_AT = datetime.fromisoformat('2026-10-14T15:00:00Z')
_EXAMPLE_APPLICATION = ApplicationSummary(
    id=UUID('3d7e2a91-6b0c-4f58-a2e4-9c1b8f0d5e36'),
    kind=ApplicationKind.INITIAL,
    status=ApplicationStatus.SUBMITTED,
    sql_state_code='KS',
    claimed_license_number='PA-000123',
    opened_at=_AT,
    decided_at=None,
    withdrawn_at=None,
    denial_reason=None,
    denial_reason_detail=None,
    resubmit_by=None,
    timeline=[ApplicationEvent(kind=EventKind.APPLIED, status=ApplicationStatus.SUBMITTED, at=_AT)],
)
_EXAMPLE_ACTION = Action(
    kind=ActionKind.APPLY_FOR_PRIVILEGES,
    available=False,
    reasons=[UnavailableReason.APPLICATION_IN_REVIEW],
)


class Dashboard(BaseModel):
    """Everything the PA's dashboard shows, read from the database on each request."""

    model_config = ConfigDict(
        json_schema_extra=example(
            qualifying_license=None,
            applications=[_EXAMPLE_APPLICATION],
            privileges=[],
            primary_action=_EXAMPLE_ACTION,
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
    practitioner_id = await own_practitioner_id(session, caller)
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
    system_user = (
        await session.scalars(select(col(User.id)).where(col(User.email) == SYSTEM_USER_EMAIL))
    ).one()
    time_zone = await reference_time_zone(session)
    return Data(
        data=Dashboard(
            qualifying_license=await _license(session, applications),
            applications=[
                await _application(
                    session,
                    a,
                    applied_before=any(older.opened_at for older in applications[i + 1 :]),
                    system_user=system_user,
                    time_zone=time_zone,
                )
                for i, a in enumerate(applications)
            ],
            privileges=await _privileges(session, practitioner_id),
            primary_action=_primary_action(applications, barred is not None and barred.is_barred),
        )
    )


def _primary_action(applications: list[ParticipationApplication], barred: bool) -> Action:
    """Apply for privileges once eligible, or once an application could make the PA eligible; else apply to participate.

    A pending change of state of qualifying license does not block privileges: the PA stays
    eligible through their current state until the new one decides (Rule 3 §3.6). A barred PA
    cannot be eligible (ML §4.A(8)), so applying to participate waits too.
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
            reasons = [UnavailableReason.TWO_YEAR_BAR] if barred else []
            return Action(
                kind=ActionKind.APPLY_FOR_PARTICIPATION, available=not reasons, reasons=reasons
            )
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
    # A foreign key holds the license, and its status view has a row for every license.
    license, status = (
        await session.execute(
            select(QualifyingLicense, QualifyingLicenseStatus.status)
            .join(
                QualifyingLicenseStatus,
                col(QualifyingLicenseStatus.qualifying_license_id) == col(QualifyingLicense.id),
            )
            .where(col(QualifyingLicense.id) == application.qualifying_license_id)
        )
    ).one()
    return QualifyingLicenseSummary(
        state_code=license.state_code,
        license_number=license.license_number,
        expires_on=license.expires_on,
        status=status,
        verified_at=application.license_verified_at,
    )


async def _application(
    session: AsyncSession,
    application: ParticipationApplication,
    *,
    applied_before: bool,
    system_user: int,
    time_zone: ZoneInfo,
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
    # A step dated apart from when it was recorded, such as the day the state reviewed it, shows on that day.
    timeline: list[ApplicationEvent] = []
    for row in rows:
        updated = row.updated or {}
        if 'status' not in updated:
            continue
        status = ApplicationStatus(updated['status'])
        timeline.append(
            ApplicationEvent(
                kind=_kind(status, timeline, applied_before, row.changed_by == system_user),
                status=status,
                at=row.effective_at or row.changed_at,
                note=updated.get('request_note')
                if status == ApplicationStatus.INFO_REQUESTED
                else None,
            )
        )
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
        resubmit_by=add_days(
            compact_date_at(application.opened_at, time_zone), _RESUBMIT_WITHIN_DAYS
        )
        if application.status == ApplicationStatus.INFO_REQUESTED and application.opened_at
        else None,
        timeline=timeline,
    )


def _kind(
    status: ApplicationStatus,
    earlier: list[ApplicationEvent],
    applied_before: bool,
    by_system: bool,
) -> EventKind:
    """A submit is the first, a repeat, or a resubmit; a withdrawal is the PA's or the deadline's."""
    if status == ApplicationStatus.SUBMITTED:
        if earlier:
            return EventKind.RESUBMITTED
        return EventKind.APPLIED_AGAIN if applied_before else EventKind.APPLIED
    if status == ApplicationStatus.WITHDRAWN:
        return EventKind.WITHDRAWN_BY_DEADLINE if by_system else EventKind.WITHDRAWN_BY_PA
    return EventKind(status.value)


async def _privileges(session: AsyncSession, practitioner_id: int) -> list[PrivilegeSummary]:
    today = await compact_today(session)
    time_zone = await reference_time_zone(session)
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
        current = PrivilegeComputedStatus(status)
        running = current in (PrivilegeComputedStatus.ACTIVE, PrivilegeComputedStatus.ENCUMBERED)
        summaries.append(
            PrivilegeSummary(
                id=privilege.public_id,
                remote_state_code=privilege.remote_state_code,
                privilege_number=privilege.privilege_number,
                status=current,
                issued_at=privilege.issued_at,
                expires_on=privilege.expires_on,
                expires_in_days=days_between(today, privilege.expires_on) if running else None,
                history=await _privilege_history(session, privilege, today, time_zone),
            )
        )
    return summaries


async def _privilege_history(
    session: AsyncSession, privilege: Privilege, today: date, time_zone: ZoneInfo
) -> list[PrivilegeEvent]:
    """Each day the privilege's status changed, by the precedence ``v_privilege_status`` uses (FLOW-06).

    The status comes from more than its history rows: an adverse action against the privilege
    encumbers it while in force, and expiry is a date passing, which writes no row.
    """
    deactivations: list[tuple[date, str, str | None]] = [
        (
            compact_date_at(row.effective_at or row.changed_at, time_zone),
            row.updated['administrator_status'],
            row.updated.get('deactivation_reason'),
        )
        for row in (
            await session.scalars(
                select(PrivilegeHistory)
                .where(col(PrivilegeHistory.entity_id) == privilege.id)
                .order_by(col(PrivilegeHistory.changed_at), col(PrivilegeHistory.id))
            )
        ).all()
        if row.updated and 'administrator_status' in row.updated
    ]
    actions = (
        await session.scalars(
            select(AdverseAction).where(col(AdverseAction.privilege_id) == privilege.id)
        )
    ).all()
    issued_on = compact_date_at(privilege.issued_at, time_zone)
    days = {issued_on, add_days(privilege.expires_on, 1)}
    days |= {day for day, _, _ in deactivations}
    for action in actions:
        days.add(action.effective_from)
        if action.effective_until is not None:
            days.add(add_days(action.effective_until, 1))

    events: list[PrivilegeEvent] = []
    for day in sorted(d for d in days if issued_on <= d <= today):
        administrator_status, reason = AdministratorStatus.ACTIVE.value, None
        for changed_on, changed_to, changed_reason in deactivations:
            if changed_on <= day:
                administrator_status, reason = changed_to, changed_reason
        if administrator_status == AdministratorStatus.INACTIVE:
            event = PrivilegeEvent(status=PrivilegeComputedStatus.INACTIVE, on=day, reason=reason)
        elif day > privilege.expires_on:
            event = PrivilegeEvent(status=PrivilegeComputedStatus.EXPIRED, on=day)
        elif any(
            a.effective_from <= day and (a.effective_until is None or day <= a.effective_until)
            for a in actions
        ):
            event = PrivilegeEvent(status=PrivilegeComputedStatus.ENCUMBERED, on=day)
        else:
            event = PrivilegeEvent(status=PrivilegeComputedStatus.ACTIVE, on=day)
        if not events or (events[-1].status, events[-1].reason) != (event.status, event.reason):
            events.append(event)
    return events
