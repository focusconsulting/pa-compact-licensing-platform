"""The computed status functions against every FLOW-06 case (F-02 phase 3).

Each test builds its scenario with the factories and asks the function for the
status as of an explicit date, so no test depends on today's date.
"""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select, text

from licensing_api.repo.adverse_action import AdverseActionTarget
from licensing_api.repo.privilege import AdministratorStatus, DeactivationReason
from licensing_api.repo.qualifying_license import LicenseStatus, QualifyingLicense
from licensing_api.repo.status import (
    CompactEligibility,
    LicenseComputedStatus,
    PrivilegeComputedStatus,
    PrivilegeStatus,
)
from tests.factories import make_adverse_action, make_issued_privilege, make_practitioner

# make_issued_privilege pins the privilege, and its qualifying license, to expire on this day.
_EXPIRES_ON = date(2027, 12, 31)


async def _privilege_status(db_session, privilege_id: int, as_of: date) -> tuple[str, str | None]:
    result = await db_session.execute(
        text(
            'SELECT status, status_reason FROM privilege_status_on(:as_of) WHERE privilege_id = :id'
        ),
        {'as_of': as_of, 'id': privilege_id},
    )
    status, reason = result.one()
    return status, reason


async def _license_status(db_session, license_id: int, as_of: date) -> str:
    result = await db_session.execute(
        text(
            'SELECT status FROM qualifying_license_status_on(:as_of) '
            'WHERE qualifying_license_id = :id'
        ),
        {'as_of': as_of, 'id': license_id},
    )
    return result.scalar_one()


async def _eligibility(db_session, practitioner_id: int, as_of: date) -> tuple[bool, date | None]:
    result = await db_session.execute(
        text(
            'SELECT is_barred, eligible_again_on FROM compact_eligibility_on(:as_of) '
            'WHERE practitioner_id = :id'
        ),
        {'as_of': as_of, 'id': practitioner_id},
    )
    is_barred, eligible_again_on = result.one()
    return is_barred, eligible_again_on


async def _deactivate(db_session, privilege, reason: DeactivationReason) -> None:
    privilege.administrator_status = AdministratorStatus.INACTIVE
    privilege.deactivation_reason = reason
    privilege.deactivated_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
    privilege.updated_by = privilege.created_by
    await db_session.flush()


async def _license_action(db_session, privilege, **overrides):
    """An adverse action against the privilege's qualifying license."""
    return await make_adverse_action(
        db_session,
        privilege,
        against=AdverseActionTarget.QUALIFYING_LICENSE,
        privilege_id=None,
        qualifying_license_id=privilege.qualifying_license_id,
        reporting_state_code='KS',
        **overrides,
    )


# --- privilege status ------------------------------------------------------


@pytest.mark.parametrize(
    ('as_of', 'expected'),
    [
        (date(2027, 6, 1), PrivilegeComputedStatus.ACTIVE),
        (_EXPIRES_ON, PrivilegeComputedStatus.ACTIVE),  # inclusive
        (date(2028, 1, 1), PrivilegeComputedStatus.EXPIRED),
    ],
    ids=['before-expiry', 'on-expiry-date', 'day-after-expiry'],
)
async def test_a_privilege_is_active_through_its_expiry_date(db_session, as_of, expected):
    privilege = await make_issued_privilege(db_session)

    assert await _privilege_status(db_session, privilege.id, as_of) == (expected, None)


async def test_renewing_the_license_does_not_extend_the_privilege(db_session):
    privilege = await make_issued_privilege(db_session)
    license = await db_session.get(QualifyingLicense, privilege.qualifying_license_id)
    license.expires_on = date(2029, 12, 31)
    license.updated_by = license.created_by
    await db_session.flush()

    # The license is renewed and still reported active, but adopted Rule 3 §3.5(a)
    # pins the privilege to the expiry in effect when the PA applied: no grace.
    assert await _license_status(db_session, license.id, date(2028, 1, 1)) == LicenseStatus.ACTIVE
    assert await _privilege_status(db_session, privilege.id, date(2028, 1, 1)) == (
        PrivilegeComputedStatus.EXPIRED,
        None,
    )


@pytest.mark.parametrize('reason', list(DeactivationReason))
async def test_a_deactivated_privilege_is_inactive_with_its_reason(db_session, reason):
    privilege = await make_issued_privilege(db_session)
    await _deactivate(db_session, privilege, reason)

    assert await _privilege_status(db_session, privilege.id, date(2027, 6, 1)) == (
        PrivilegeComputedStatus.INACTIVE,
        reason,
    )


async def test_inactive_takes_precedence_over_expired(db_session):
    privilege = await make_issued_privilege(db_session)
    await _deactivate(db_session, privilege, DeactivationReason.STATE_DEACTIVATED)

    assert await _privilege_status(db_session, privilege.id, date(2028, 6, 1)) == (
        PrivilegeComputedStatus.INACTIVE,
        DeactivationReason.STATE_DEACTIVATED,
    )


@pytest.mark.parametrize(
    ('as_of', 'expected'),
    [
        (date(2026, 6, 30), PrivilegeComputedStatus.ACTIVE),  # before it starts
        (date(2026, 7, 1), PrivilegeComputedStatus.ENCUMBERED),
        (date(2026, 12, 31), PrivilegeComputedStatus.ENCUMBERED),  # inclusive end
        (date(2027, 1, 1), PrivilegeComputedStatus.ACTIVE),  # lifted
    ],
    ids=['before-action', 'action-starts', 'last-day-of-action', 'day-after-lift'],
)
async def test_an_action_against_the_privilege_encumbers_it_while_in_force(
    db_session, as_of, expected
):
    privilege = await make_issued_privilege(db_session)
    await make_adverse_action(db_session, privilege, effective_until=date(2026, 12, 31))

    assert await _privilege_status(db_session, privilege.id, as_of) == (expected, None)


async def test_expired_takes_precedence_over_encumbered(db_session):
    privilege = await make_issued_privilege(db_session)
    await make_adverse_action(db_session, privilege)

    assert await _privilege_status(db_session, privilege.id, date(2028, 1, 1)) == (
        PrivilegeComputedStatus.EXPIRED,
        None,
    )


async def test_an_action_against_the_license_reaches_privileges_only_through_deactivation(
    db_session,
):
    # FLOW-05: the cascade deactivates every privilege; this function does not infer it.
    privilege = await make_issued_privilege(db_session)
    await _license_action(db_session, privilege)

    assert await _privilege_status(db_session, privilege.id, date(2026, 8, 1)) == (
        PrivilegeComputedStatus.ACTIVE,
        None,
    )


@pytest.mark.parametrize(
    ('instant', 'expected'),
    [
        # 04:30 UTC on 1 January is 23:30 on 31 December in New York (EST): still the expiry date.
        (datetime(2028, 1, 1, 4, 30, tzinfo=timezone.utc), PrivilegeComputedStatus.ACTIVE),
        (datetime(2028, 1, 1, 5, 30, tzinfo=timezone.utc), PrivilegeComputedStatus.EXPIRED),
    ],
    ids=['late-evening-in-new-york', 'after-midnight-in-new-york'],
)
async def test_expiry_follows_the_reference_time_zone(db_session, instant, expected):
    privilege = await make_issued_privilege(db_session)

    result = await db_session.execute(
        text(
            'SELECT status FROM privilege_status_on(compact_date_at(:instant)) '
            'WHERE privilege_id = :id'
        ),
        {'instant': instant, 'id': privilege.id},
    )

    assert result.scalar_one() == expected


# --- qualifying license status ---------------------------------------------


async def test_a_license_is_active_through_its_expiry_date(db_session):
    privilege = await make_issued_privilege(db_session)
    license_id = privilege.qualifying_license_id

    assert (
        await _license_status(db_session, license_id, _EXPIRES_ON) == LicenseComputedStatus.ACTIVE
    )
    assert await _license_status(db_session, license_id, date(2028, 1, 1)) == (
        LicenseComputedStatus.EXPIRED
    )


async def test_a_license_shows_the_state_reported_status(db_session):
    privilege = await make_issued_privilege(db_session)
    license = await db_session.get(QualifyingLicense, privilege.qualifying_license_id)
    license.state_reported_status = LicenseStatus.LAPSED
    license.updated_by = license.created_by
    await db_session.flush()

    assert await _license_status(db_session, license.id, date(2027, 6, 1)) == (
        LicenseComputedStatus.LAPSED
    )


@pytest.mark.parametrize(
    ('as_of', 'expected'),
    [
        (date(2026, 12, 31), LicenseComputedStatus.ACTIVE),
        (date(2027, 1, 1), LicenseComputedStatus.TERMINATED),
    ],
    ids=['day-before-termination', 'termination-date'],
)
async def test_a_voluntarily_terminated_license_is_terminated_from_that_date(
    db_session, as_of, expected
):
    privilege = await make_issued_privilege(db_session)
    license = await db_session.get(QualifyingLicense, privilege.qualifying_license_id)
    license.terminated_on = date(2027, 1, 1)
    license.updated_by = license.created_by
    await db_session.flush()

    assert await _license_status(db_session, license.id, as_of) == expected


async def test_an_action_against_the_license_encumbers_it_while_in_force(db_session):
    privilege = await make_issued_privilege(db_session)
    await _license_action(db_session, privilege)

    assert await _license_status(db_session, privilege.qualifying_license_id, date(2026, 8, 1)) == (
        LicenseComputedStatus.ENCUMBERED
    )


# --- compact eligibility: the two-year bar (ML §4.A.8) ---------------------


async def test_a_practitioner_with_no_actions_is_not_barred(db_session):
    practitioner = await make_practitioner(db_session)

    assert await _eligibility(db_session, practitioner.id, date(2026, 10, 7)) == (False, None)


async def test_an_open_ended_action_against_the_license_bars_with_no_date(db_session):
    privilege = await make_issued_privilege(db_session)
    await _license_action(db_session, privilege)

    assert await _eligibility(db_session, privilege.practitioner_id, date(2026, 8, 1)) == (
        True,
        None,
    )


@pytest.mark.parametrize(
    ('as_of', 'is_barred'),
    [
        (date(2026, 12, 31), True),  # the last restricted day
        (date(2028, 12, 31), True),  # the day before two years have elapsed
        (date(2029, 1, 1), False),  # two years from the first unrestricted day, 1 January 2027
    ],
    ids=['last-restricted-day', 'day-before-bar-ends', 'bar-ends'],
)
async def test_the_bar_lasts_two_years_from_the_first_unrestricted_day(
    db_session, as_of, is_barred
):
    privilege = await make_issued_privilege(db_session)
    await _license_action(db_session, privilege, effective_until=date(2026, 12, 31))

    assert await _eligibility(db_session, privilege.practitioner_id, as_of) == (
        is_barred,
        date(2029, 1, 1),
    )


async def test_the_bar_from_a_leap_day_ends_on_the_last_day_of_february(db_session):
    # Restricted through 28 February 2028, so unrestricted from 29 February 2028.
    # Postgres adds two years to 29 February as 28 February 2030.
    privilege = await make_issued_privilege(db_session)
    await _license_action(db_session, privilege, effective_until=date(2028, 2, 28))

    assert await _eligibility(db_session, privilege.practitioner_id, date(2030, 3, 1)) == (
        False,
        date(2030, 2, 28),
    )


async def test_the_latest_ending_action_sets_the_bar(db_session):
    privilege = await make_issued_privilege(db_session)
    await _license_action(db_session, privilege, effective_until=date(2026, 12, 31))
    await _license_action(db_session, privilege, effective_until=date(2027, 6, 30))

    assert await _eligibility(db_session, privilege.practitioner_id, date(2027, 7, 1)) == (
        True,
        date(2029, 7, 1),
    )


async def test_an_action_that_has_not_started_does_not_bar(db_session):
    privilege = await make_issued_privilege(db_session)
    await _license_action(db_session, privilege)

    assert await _eligibility(db_session, privilege.practitioner_id, date(2026, 6, 30)) == (
        False,
        None,
    )


async def test_an_action_against_a_privilege_does_not_bar(db_session):
    # FLOW-05: lifting a privilege-level action restores that privilege, so only
    # actions against the qualifying license start the bar.
    privilege = await make_issued_privilege(db_session)
    await make_adverse_action(db_session, privilege)

    assert await _eligibility(db_session, privilege.practitioner_id, date(2026, 8, 1)) == (
        False,
        None,
    )


# --- views -----------------------------------------------------------------


async def test_the_views_evaluate_as_of_today(db_session):
    privilege = await make_issued_privilege(db_session, expires_on=date(2099, 12, 31))

    status = await db_session.get(PrivilegeStatus, privilege.id)
    license_status = await db_session.execute(
        text('SELECT status FROM v_qualifying_license_status WHERE qualifying_license_id = :id'),
        {'id': privilege.qualifying_license_id},
    )
    eligibility = await db_session.execute(
        select(CompactEligibility).where(
            CompactEligibility.practitioner_id == privilege.practitioner_id
        )
    )

    assert status is not None
    assert status.status == PrivilegeComputedStatus.ACTIVE
    assert license_status.scalar_one() in set(LicenseComputedStatus)
    assert eligibility.scalar_one().is_barred is False
