"""``just seed demo`` sets up every status, and the status views agree with each one (FLOW-06)."""

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.repo.participation_application import (
    ApplicationStatus,
    ParticipationApplication,
)
from licensing_api.repo.privilege_request import PrivilegeRequest, PrivilegeRequestStatus
from licensing_api.repo.status import (
    CompactEligibility,
    LicenseComputedStatus,
    PrivilegeComputedStatus,
    PrivilegeStatus,
    QualifyingLicenseStatus,
)
from licensing_api.repo.user import User
from seed.demo import ELIGIBILITY, STAFF, AlreadySeeded, Expected, seed

_EVERY_STATUS = {
    'application': set(ApplicationStatus),
    'privilege_request': set(PrivilegeRequestStatus),
    'privilege': set(PrivilegeComputedStatus),
    'license': set(LicenseComputedStatus),
    'eligibility': set(ELIGIBILITY),
}


def _eligibility(is_barred: bool, eligible_again_on: date | None) -> str:
    if is_barred:
        return 'barred' if eligible_again_on is None else 'barred_until'
    return 'not_barred' if eligible_again_on is None else 'bar_ended'


async def _actual(session: AsyncSession, item: Expected) -> str:
    """The status the database shows for ``item``: stored for applications and requests, computed otherwise."""
    if item.kind == 'application':
        return (await session.get_one(ParticipationApplication, item.id)).status
    if item.kind == 'privilege_request':
        return (await session.get_one(PrivilegeRequest, item.id)).status
    if item.kind == 'privilege':
        return (await session.get_one(PrivilegeStatus, item.id)).status
    if item.kind == 'license':
        return (await session.get_one(QualifyingLicenseStatus, item.id)).status
    row = await session.get_one(CompactEligibility, item.id)
    return _eligibility(row.is_barred, row.eligible_again_on)


@pytest.fixture
async def seeded(db_session):
    already = await db_session.scalar(select(User.id).where(col(User.email) == STAFF[0][0]))
    if already is not None:
        pytest.skip('this database already holds the demo seed; `just infra` resets it')
    return await seed(db_session)


async def test_every_status_is_seeded(seeded):
    covered = {
        kind: {item.status for item in seeded if item.kind == kind} for kind in _EVERY_STATUS
    }

    assert covered == _EVERY_STATUS


async def test_the_database_shows_each_seeded_status(db_session, seeded):
    wrong = [
        (item, actual)
        for item in seeded
        if (actual := await _actual(db_session, item)) != item.status
    ]

    assert wrong == []


async def test_a_second_run_is_refused(db_session, seeded):
    with pytest.raises(AlreadySeeded):
        await seed(db_session)
