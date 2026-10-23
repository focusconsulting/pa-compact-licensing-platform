"""Demo data for sprint reviews: a practitioner for every application, request, privilege, and license status.

Run by ``just seed demo`` on a migrated database. Local tooling, never a migration
(constitution Principle IV), and outside the image (``.dockerignore``). Dates count
from ``compact_today()``, so each status holds on the day it runs. Rows get
history but no events, so no email goes out. ``docs/demo.md`` lists who to sign in as.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel, col

from licensing_api.config import settings
from licensing_api.context import ChangeContext, system_context
from licensing_api.days import add_days, compact_today
from licensing_api.repo import history
from licensing_api.repo.adverse_action import AdverseAction, AdverseActionTarget
from licensing_api.repo.fee import Fee, FeeType
from licensing_api.repo.participation_application import (
    ApplicationKind,
    ApplicationStatus,
    ParticipationApplication,
)
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.privilege import AdministratorStatus, DeactivationReason, Privilege
from licensing_api.repo.privilege_request import PrivilegeRequest, PrivilegeRequestStatus
from licensing_api.repo.qualifying_license import LicenseStatus, QualifyingLicense
from licensing_api.repo.sii_report import SiiReport
from licensing_api.repo.state import State
from licensing_api.repo.status import LicenseComputedStatus, PrivilegeComputedStatus
from licensing_api.repo.user import User

LIVE_STATES = ('KS', 'OK', 'MO', 'CO')
# The four outcomes of v_compact_eligibility (ML §4.A.8).
ELIGIBILITY = ('not_barred', 'barred', 'barred_until', 'bar_ended')
# State staff who sign in through the Cognito mock (engineering/mocks/cognito/db/local_licensing.json).
STAFF = (
    ('kansas.staff@example.com', 'Kim', 'Kansas', 'state_staff', 'KS', ['read_private', 'write']),
    ('kansas.admin@example.com', 'Kai', 'Kansas', 'state_admin', 'KS', ['read_private', 'admin']),
    (
        'oklahoma.staff@example.com',
        'Ola',
        'Oklahoma',
        'state_staff',
        'OK',
        ['read_private', 'write'],
    ),
)

_APPROVED = (
    ApplicationStatus.ELIGIBLE,
    ApplicationStatus.ELIGIBILITY_WITHDRAWN,
    ApplicationStatus.SUPERSEDED,
)
_DECIDED = (*_APPROVED, ApplicationStatus.DENIED)


def _id(row: Any) -> int:
    """A flushed row's primary key."""
    assert row.id is not None
    return row.id


class AlreadySeeded(Exception):
    """The demo seed has already run on this database; reset it with ``just infra`` first."""


@dataclass(frozen=True)
class Expected:
    """A status the seed set up, which ``tests/test_demo_seed.py`` checks against the database."""

    kind: str  # application, privilege_request, privilege, license, or eligibility
    id: int
    status: str


class _Demo:
    """Builds valid rows with history, dated relative to today, and records the status each should show."""

    def __init__(self, session: AsyncSession, ctx: ChangeContext, today: date) -> None:
        self.session = session
        self.ctx = ctx
        self.today = today
        self.expected: list[Expected] = []
        self._licenses = 0

    def day(self, offset: int) -> date:
        return add_days(self.today, offset)

    def at(self, offset: int) -> datetime:
        return datetime.combine(self.day(offset), time(15), tzinfo=timezone.utc)

    def expect(self, kind: str, row: Any, status: str) -> None:
        self.expected.append(Expected(kind, _id(row), status))

    async def add[T: SQLModel](self, row: T) -> T:
        self.session.add(row)
        await history.write(self.session, self.ctx, row, before=None)
        return row

    async def user(
        self,
        email: str,
        given: str,
        family: str,
        role: str,
        state: str | None = None,
        **grants: list[str],
    ) -> User:
        # users.id comes from the database on flush.
        row = User(  # type: ignore[call-arg]
            email=email,
            public_id=None,
            given_name=given,
            family_name=family,
            role=role,
            state_code=state,
            is_active=True,
            permissions=grants,
            created_by=self.ctx.user_id,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def practitioner(
        self, given: str, family: str, sql_state: str | None = None
    ) -> Practitioner:
        user = await self.user(f'{given}.{family}@example.com'.lower(), given, family, 'licensee')
        return await self.add(
            Practitioner(
                user_id=_id(user),
                current_sql_state_code=sql_state,
                legal_first_name=given,
                legal_last_name=family,
                date_of_birth=date(1988, 4, 12),
                correspondence_email=user.email,
                created_by=self.ctx.user_id,
            )
        )

    async def license(
        self, practitioner: Practitioner, status: LicenseComputedStatus, state: str = 'KS'
    ) -> QualifyingLicense:
        """A license showing ``status``. An ``encumbered`` one needs an adverse action from the caller."""
        self._licenses += 1
        reported = status if status in set(LicenseStatus) - {LicenseStatus.EXPIRED} else 'active'
        terminated = status == LicenseComputedStatus.TERMINATED
        row = await self.add(
            QualifyingLicense(
                practitioner_id=_id(practitioner),
                state_code=state,
                license_number=f'{state}-PA-{self._licenses:05d}',
                state_reported_status=reported,
                status_effective_on=self.day(-90 if terminated else -700),
                issued_on=self.day(-700),
                expires_on=self.day(-60 if status == LicenseComputedStatus.EXPIRED else 400),
                terminated_on=self.day(-90) if terminated else None,
                is_unrestricted=True,
                verified_by=self.ctx.user_id,
                verified_at=self.at(-30),
                created_by=self.ctx.user_id,
            )
        )
        self.expect('license', row, status)
        return row

    async def application(
        self,
        practitioner: Practitioner,
        status: ApplicationStatus,
        license: QualifyingLicense | None = None,
        kind: ApplicationKind = ApplicationKind.INITIAL,
    ) -> ParticipationApplication:
        """An application in ``status``, with every field that status's check constraints require."""
        fields: dict[str, Any] = {}
        if status != ApplicationStatus.DRAFT:
            fields['opened_at'] = self.at(-60)
        if status in _APPROVED:
            fields |= {
                'license_verified_at': self.at(-50),
                'license_verified_by': self.ctx.user_id,
                'cbc_completed_on': self.day(-55),
            }
        if status in _DECIDED:
            fields |= {'decided_at': self.at(-45), 'decided_by': self.ctx.user_id}
        fields |= {
            ApplicationStatus.INFO_REQUESTED: {'request_note': 'Upload your NCCPA certificate.'},
            ApplicationStatus.DENIED: {'denial_reason_code': 'nccpa_not_current'},
            ApplicationStatus.WITHDRAWN: {'withdrawn_at': self.at(-50)},
            ApplicationStatus.ELIGIBILITY_WITHDRAWN: {
                'eligibility_withdrawn_at': self.at(-10),
                'eligibility_withdrawal_reason': 'NCCPA certification lapsed.',
            },
            ApplicationStatus.SUPERSEDED: {'superseded_at': self.at(-5)},
        }.get(status, {})
        row = await self.add(
            ParticipationApplication(
                practitioner_id=_id(practitioner),
                kind=kind,
                sql_state_code=license.state_code if license else 'KS',
                qualifying_license_id=_id(license) if license else None,
                status=status,
                created_by=self.ctx.user_id,
                **fields,
            )
        )
        self.expect('application', row, status)
        return row

    async def request(
        self,
        application: ParticipationApplication,
        license: QualifyingLicense,
        remote: str,
        status: PrivilegeRequestStatus,
        ql_expires_on: date | None = None,
    ) -> PrivilegeRequest:
        """A privilege request in ``status``; ``ql_expires_on`` overrides the license expiry it pins."""
        fields: dict[str, Any] = {}
        if status in ('submitted', 'issued', 'denied'):
            fields |= {
                'submitted_at': self.at(-40),
                'ql_expires_on_snapshot': ql_expires_on or license.expires_on,
            }
        if status in ('issued', 'denied'):
            fields |= {'decided_at': self.at(-35), 'decided_by': self.ctx.user_id}
        if status == PrivilegeRequestStatus.DENIED:
            fields['denial_reason_code'] = 'jurisprudence_not_met'
        if status == PrivilegeRequestStatus.WITHDRAWN:
            fields['withdrawn_at'] = self.at(-38)
        row = await self.add(
            PrivilegeRequest(
                participation_application_id=_id(application),
                practitioner_id=application.practitioner_id,
                remote_state_code=remote,
                qualifying_license_id=_id(license),
                status=status,
                created_by=self.ctx.user_id,
                **fields,
            )
        )
        self.expect('privilege_request', row, status)
        return row

    async def privilege(
        self,
        request: PrivilegeRequest,
        status: PrivilegeComputedStatus,
        reason: DeactivationReason | None = None,
    ) -> Privilege:
        """The privilege an issued ``request`` granted. An ``encumbered`` one needs an adverse action."""
        assert request.ql_expires_on_snapshot is not None
        number = await self.session.scalar(
            select(func.next_privilege_number(request.remote_state_code, self.ctx.user_id))
        )
        inactive = status == PrivilegeComputedStatus.INACTIVE
        row = await self.add(
            Privilege(
                privilege_request_id=_id(request),
                practitioner_id=request.practitioner_id,
                remote_state_code=request.remote_state_code,
                qualifying_license_id=request.qualifying_license_id,
                privilege_number=str(number),
                issued_at=self.at(-35),
                expires_on=request.ql_expires_on_snapshot,
                administrator_status=AdministratorStatus.INACTIVE
                if inactive
                else AdministratorStatus.ACTIVE,
                deactivation_reason=reason if inactive else None,
                deactivated_at=self.at(-10) if inactive else None,
                created_by=self.ctx.user_id,
            )
        )
        self.expect('privilege', row, status)
        return row

    async def adverse_action(
        self,
        practitioner: Practitioner,
        reporting: str,
        started: int,
        ended: int | None = None,
        *,
        license: QualifyingLicense | None = None,
        privilege: Privilege | None = None,
    ) -> AdverseAction:
        """A suspension against ``license`` or ``privilege``, from day ``started`` to day ``ended`` (in force if None)."""
        return await self.add(
            AdverseAction(
                practitioner_id=_id(practitioner),
                reporting_state_code=reporting,
                against=AdverseActionTarget.PRIVILEGE
                if privilege
                else AdverseActionTarget.QUALIFYING_LICENSE,
                qualifying_license_id=_id(license) if license else None,
                privilege_id=_id(privilege) if privilege else None,
                action_type_code='suspension',
                summary='Suspended by board order pending review.',
                ordered_on=self.day(started),
                effective_from=self.day(started),
                effective_until=self.day(ended) if ended is not None else None,
                created_by=self.ctx.user_id,
            )
        )

    async def sii(self, practitioner: Practitioner, reporting: str, *, closed: bool) -> SiiReport:
        return await self.add(
            SiiReport(
                practitioner_id=_id(practitioner),
                reporting_state_code=reporting,
                description='Complaint under investigation by the board.',
                contact_name='Board investigator',
                contact_email=f'investigations@{reporting.lower()}.example.com',
                determined_on=self.day(-25),
                closed_at=self.at(-5) if closed else None,
                closed_by=self.ctx.user_id if closed else None,
                created_by=self.ctx.user_id,
            )
        )


async def seed(session: AsyncSession) -> list[Expected]:
    """Load the demo data in the caller's transaction and return the statuses it should show."""
    first_staff = select(col(User.id)).where(col(User.email) == STAFF[0][0])
    if await session.scalar(first_staff) is not None:
        raise AlreadySeeded('The demo seed is already loaded; reset with `just infra` first.')
    demo = _Demo(session, await system_context(session), await compact_today(session))
    await _compact(demo)
    await _applications(demo)
    await _privileges(demo)
    await _discipline(demo)
    return demo.expected


async def _compact(demo: _Demo) -> None:
    for code in LIVE_STATES:
        state = await demo.session.get_one(State, code)
        before = history.snapshot(state)
        state.is_member, state.member_effective_on, state.is_live = True, demo.day(-365), True
        state.updated_by = demo.ctx.user_id
        await history.write(demo.session, demo.ctx, state, before=before)
        fee = Fee(
            state_code=code,
            fee_type=FeeType.PRIVILEGE,
            amount_cents=10000,
            effective_from=demo.day(-365),
            created_by=demo.ctx.user_id,
        )
        await demo.add(fee)
    commission_fee = Fee(
        fee_type=FeeType.PARTICIPATION,
        amount_cents=5000,
        effective_from=demo.day(-365),
        created_by=demo.ctx.user_id,
    )
    await demo.add(commission_fee)
    for email, given, family, role, state_code, grants in STAFF:
        await demo.user(email, given, family, role, state_code, **{state_code: grants})


async def _applications(demo: _Demo) -> None:
    """One practitioner per application status that has no privilege, plus the other license statuses."""
    active = LicenseComputedStatus.ACTIVE
    dana = await demo.practitioner('Dana', 'Draft')
    await demo.license(dana, LicenseComputedStatus.EXPIRED)
    await demo.application(dana, ApplicationStatus.DRAFT)

    sam = await demo.practitioner('Sam', 'Submitted')
    await demo.application(sam, ApplicationStatus.SUBMITTED, await demo.license(sam, active))

    ira = await demo.practitioner('Ira', 'Info')
    await demo.license(ira, LicenseComputedStatus.TERMINATED, 'CO')
    await demo.application(ira, ApplicationStatus.INFO_REQUESTED, await demo.license(ira, active))

    dee = await demo.practitioner('Dee', 'Denied')
    await demo.application(
        dee, ApplicationStatus.DENIED, await demo.license(dee, LicenseComputedStatus.INACTIVE)
    )

    wren = await demo.practitioner('Wren', 'Withdrawn')
    await demo.application(
        wren, ApplicationStatus.WITHDRAWN, await demo.license(wren, LicenseComputedStatus.LAPSED)
    )

    sol = await demo.practitioner('Sol', 'Superseded', sql_state='MO')
    await demo.application(sol, ApplicationStatus.SUPERSEDED, await demo.license(sol, active))
    moved = await demo.license(sol, active, 'MO')
    await demo.application(sol, ApplicationStatus.ELIGIBLE, moved, ApplicationKind.CHANGE_SQL)


async def _privileges(demo: _Demo) -> None:
    """Eligible practitioners with every privilege request status and privilege status."""
    issued = PrivilegeRequestStatus.ISSUED
    avery, avery_license, avery_app = await _eligible(demo, 'Avery', 'Active')
    await demo.privilege(
        await demo.request(avery_app, avery_license, 'OK', issued), PrivilegeComputedStatus.ACTIVE
    )
    await demo.request(avery_app, avery_license, 'MO', PrivilegeRequestStatus.SUBMITTED)
    await demo.request(avery_app, avery_license, 'CO', PrivilegeRequestStatus.PENDING_PAYMENT)
    await demo.sii(avery, 'MO', closed=True)
    demo.expect('eligibility', avery, 'not_barred')

    pia, pia_license, pia_app = await _eligible(demo, 'Pia', 'Expired')
    lapsed = await demo.request(pia_app, pia_license, 'OK', issued, ql_expires_on=demo.day(-30))
    await demo.privilege(lapsed, PrivilegeComputedStatus.EXPIRED)
    await demo.request(pia_app, pia_license, 'MO', PrivilegeRequestStatus.DENIED)
    await demo.request(pia_app, pia_license, 'CO', PrivilegeRequestStatus.WITHDRAWN)

    enzo, enzo_license, enzo_app = await _eligible(demo, 'Enzo', 'Encumbered')
    held = await demo.privilege(
        await demo.request(enzo_app, enzo_license, 'OK', issued), PrivilegeComputedStatus.ENCUMBERED
    )
    await demo.adverse_action(enzo, 'OK', -20, privilege=held)
    await demo.sii(enzo, 'OK', closed=False)

    eli = await demo.practitioner('Eli', 'Withdrawn-Eligibility')
    eli_license = await demo.license(eli, LicenseComputedStatus.ACTIVE)
    eli_app = await demo.application(eli, ApplicationStatus.ELIGIBILITY_WITHDRAWN, eli_license)
    await demo.privilege(
        await demo.request(eli_app, eli_license, 'OK', issued),
        PrivilegeComputedStatus.INACTIVE,
        DeactivationReason.ELIGIBILITY_WITHDRAWN,
    )


async def _discipline(demo: _Demo) -> None:
    """Adverse actions against qualifying licenses: in force, ended within the two-year bar, and ended before it."""
    lex, lex_license, lex_app = await _eligible(
        demo, 'Lex', 'License-Action', LicenseComputedStatus.ENCUMBERED
    )
    await demo.adverse_action(lex, 'KS', -15, license=lex_license)
    # The cascade's result, set directly: deactivate_privileges would emit events (FLOW-05).
    await demo.privilege(
        await demo.request(lex_app, lex_license, 'OK', PrivilegeRequestStatus.ISSUED),
        PrivilegeComputedStatus.INACTIVE,
        DeactivationReason.QUALIFYING_LICENSE_ADVERSE_ACTION,
    )
    demo.expect('eligibility', lex, 'barred')

    for given, family, started, ended, outcome in (
        ('Bea', 'Barred-Until', -500, -365, 'barred_until'),
        ('Ned', 'Bar-Ended', -1500, -1100, 'bar_ended'),
    ):
        practitioner = await demo.practitioner(given, family)
        license = await demo.license(practitioner, LicenseComputedStatus.ACTIVE)
        await demo.adverse_action(practitioner, 'KS', started, ended, license=license)
        demo.expect('eligibility', practitioner, outcome)


async def _eligible(
    demo: _Demo,
    given: str,
    family: str,
    license_status: LicenseComputedStatus = LicenseComputedStatus.ACTIVE,
) -> tuple[Practitioner, QualifyingLicense, ParticipationApplication]:
    """A practitioner whose Kansas application was decided eligible."""
    practitioner = await demo.practitioner(given, family, sql_state='KS')
    license = await demo.license(practitioner, license_status)
    application = await demo.application(practitioner, ApplicationStatus.ELIGIBLE, license)
    return practitioner, license, application


async def _main() -> None:
    engine = create_async_engine(settings.db_url)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session, session.begin():
            expected = await seed(session)
    finally:
        await engine.dispose()
    print(f'Loaded {len(expected)} demo statuses. docs/demo.md lists who to sign in as.')


if __name__ == '__main__':
    asyncio.run(_main())
