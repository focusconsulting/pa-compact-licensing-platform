"""The relationship predicates: which PAs a state may see (ADR-0020)."""

from datetime import date, datetime, timezone

import pytest
from sqlmodel import col, select

from licensing_api.repo.participation_application import ApplicationStatus
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.privilege_request import PrivilegeRequestStatus
from licensing_api.repo.scope import holds_license_in, is_remote_for, is_sql_for, related_to
from tests.factories import (
    make_application,
    make_eligible_application,
    make_practitioner,
    make_qualifying_license,
    make_submitted_request,
)


async def _matching(session, condition, *candidates: Practitioner) -> set[int | None]:
    rows = await session.scalars(
        select(Practitioner.id).where(
            condition, col(Practitioner.id).in_([p.id for p in candidates])
        )
    )
    return set(rows.all())


AT = datetime(2026, 6, 1, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ('status', 'fields', 'related'),
    [
        (ApplicationStatus.DRAFT, {}, False),
        (ApplicationStatus.SUBMITTED, {'opened_at': AT}, True),
        (ApplicationStatus.WITHDRAWN, {'opened_at': AT, 'withdrawn_at': AT}, True),
    ],
)
async def test_a_state_is_the_sql_once_an_application_leaves_draft(
    db_session, status, fields, related
):
    practitioner = await make_practitioner(db_session)
    await make_application(db_session, practitioner, sql_state_code='NE', status=status, **fields)

    assert await _matching(db_session, is_sql_for('ne'), practitioner) == (
        {practitioner.id} if related else set()
    )
    assert await _matching(db_session, is_sql_for('KS'), practitioner) == set()


async def test_a_state_is_remote_once_the_request_is_paid_and_after_it_is_withdrawn(db_session):
    unpaid, paid, withdrawn, abandoned = [await make_practitioner(db_session) for _ in range(4)]
    unpaid_fields = {'submitted_at': None, 'ql_expires_on_snapshot': None}
    for practitioner, fields in [
        (unpaid, {'status': PrivilegeRequestStatus.PENDING_PAYMENT, **unpaid_fields}),
        (paid, {}),
        (withdrawn, {'status': PrivilegeRequestStatus.WITHDRAWN, 'withdrawn_at': AT}),
        (
            abandoned,
            {'status': PrivilegeRequestStatus.WITHDRAWN, 'withdrawn_at': AT, **unpaid_fields},
        ),
    ]:
        application = await make_eligible_application(db_session, practitioner)
        await make_submitted_request(db_session, application, **fields)

    candidates = (unpaid, paid, withdrawn, abandoned)
    assert await _matching(db_session, is_remote_for('ok'), *candidates) == {
        paid.id,
        withdrawn.id,
    }
    assert await _matching(db_session, is_remote_for('MO'), *candidates) == set()


async def test_a_state_holding_a_license_is_related_whatever_its_status(db_session):
    active, expired, other = [await make_practitioner(db_session) for _ in range(3)]
    await make_qualifying_license(db_session, active, state_code='MO')
    await make_qualifying_license(
        db_session, expired, state_code='MO', state_reported_status='expired'
    )
    await make_qualifying_license(db_session, other, state_code='NE', expires_on=date(2028, 1, 1))

    assert await _matching(db_session, holds_license_in('mo'), active, expired, other) == {
        active.id,
        expired.id,
    }


async def test_related_to_is_any_relationship(db_session):
    sql, remote, licensed, draft_only = [await make_practitioner(db_session) for _ in range(4)]
    await make_application(
        db_session, sql, sql_state_code='MO', status=ApplicationStatus.SUBMITTED, opened_at=AT
    )
    await make_submitted_request(
        db_session,
        await make_eligible_application(db_session, remote),
        remote_state_code='MO',
    )
    await make_qualifying_license(db_session, licensed, state_code='MO')
    await make_application(db_session, draft_only, sql_state_code='MO')

    assert await _matching(db_session, related_to('MO'), sql, remote, licensed, draft_only) == {
        sql.id,
        remote.id,
        licensed.id,
    }
