"""The PA's dashboard: what it shows, read from the database, and why an action is unavailable (SCRUM-112)."""

from datetime import date, datetime, timezone

import pytest

from licensing_api.context import ChangeContext
from licensing_api.repo import history
from licensing_api.repo.adverse_action import AdverseActionTarget
from licensing_api.repo.application_transition import move
from licensing_api.repo.domain_event import EventType, emit
from licensing_api.repo.participation_application import ApplicationStatus, ParticipationApplication
from licensing_api.repo.privilege import AdministratorStatus, DeactivationReason
from licensing_api.repo.user import User
from tests.factories import (
    make_adverse_action,
    make_application,
    make_eligible_application,
    make_practitioner,
    make_privilege,
    make_submitted_request,
    make_user,
    system_user_id,
)

_ME = '/api/me/dashboard'
_OPENED = datetime(2026, 10, 1, tzinfo=timezone.utc)


@pytest.fixture
def pa(client, route_db_session):
    async def _make():
        practitioner = await make_practitioner(route_db_session)
        return (await route_db_session.get(User, practitioner.user_id)).email, practitioner

    return client.portal.call(_make)


def _call(client, coroutine_function):
    return client.portal.call(coroutine_function)


def _dashboard(client, auth_header, email) -> dict:
    response = client.get(_ME, headers=auth_header(email))
    assert response.status_code == 200, response.json()
    return response.json()['data']


async def _sent(session, practitioner) -> ParticipationApplication:
    """An application submitted the way the route submits it, so its history starts as the route's does."""
    application = await make_application(session, practitioner)
    ctx = ChangeContext(await system_user_id(session), 'req-dash')
    await move(
        session,
        ctx,
        application,
        ApplicationStatus.SUBMITTED,
        EventType.APPLICATION_SUBMITTED,
        opened_at=_OPENED,
    )
    return application


def test_a_pa_with_no_application_is_offered_participation(client, auth_header, pa):
    email, _ = pa

    assert _dashboard(client, auth_header, email) == {
        'qualifying_license': None,
        'applications': [],
        'privileges': [],
        'primary_action': {'kind': 'apply_for_participation', 'available': True, 'reasons': []},
    }


@pytest.mark.parametrize('status', ['draft', 'denied', 'withdrawn'])
def test_a_pa_with_no_application_in_progress_is_offered_participation(
    client, auth_header, route_db_session, pa, status
):
    email, practitioner = pa
    fields = {'opened_at': _OPENED, 'withdrawn_at': _OPENED} if status == 'withdrawn' else {}
    if status == 'denied':
        fields = {
            'opened_at': _OPENED,
            'decided_at': _OPENED,
            'decided_by': practitioner.created_by,
            'denial_reason_code': 'nccpa_not_current',
        }
    _call(client, lambda: make_application(route_db_session, practitioner, status=status, **fields))

    assert (
        _dashboard(client, auth_header, email)['primary_action']['kind']
        == 'apply_for_participation'
    )


@pytest.mark.parametrize(
    ('status', 'reason'),
    [('submitted', 'application_in_review'), ('info_requested', 'information_requested')],
)
def test_privileges_wait_on_an_application_the_state_has(
    client, auth_header, route_db_session, pa, status, reason
):
    email, practitioner = pa
    _call(
        client,
        lambda: make_application(route_db_session, practitioner, status=status, opened_at=_OPENED),
    )

    assert _dashboard(client, auth_header, email)['primary_action'] == {
        'kind': 'apply_for_privileges',
        'available': False,
        'reasons': ['not_yet_eligible', reason],
    }


def test_privileges_are_unavailable_once_eligibility_is_withdrawn(
    client, auth_header, route_db_session, pa
):
    email, practitioner = pa
    _call(
        client,
        lambda: make_eligible_application(
            route_db_session,
            practitioner,
            status=ApplicationStatus.ELIGIBILITY_WITHDRAWN,
            eligibility_withdrawn_at=_OPENED,
            eligibility_withdrawal_reason='License revoked',
        ),
    )

    assert _dashboard(client, auth_header, email)['primary_action']['reasons'] == [
        'not_yet_eligible',
        'eligibility_withdrawn',
    ]


def test_an_eligible_pa_may_apply_for_privileges(client, auth_header, route_db_session, pa):
    email, practitioner = pa
    _call(client, lambda: make_eligible_application(route_db_session, practitioner))

    assert _dashboard(client, auth_header, email)['primary_action'] == {
        'kind': 'apply_for_privileges',
        'available': True,
        'reasons': [],
    }


def test_a_pending_change_of_state_does_not_hold_up_privileges(
    client, auth_header, route_db_session, pa
):
    email, practitioner = pa

    async def _make():
        await make_eligible_application(route_db_session, practitioner)
        await make_application(
            route_db_session, practitioner, kind='change_sql', status='submitted', opened_at=_OPENED
        )

    _call(client, _make)

    assert _dashboard(client, auth_header, email)['primary_action']['available'] is True


def test_the_two_year_bar_holds_up_privileges(client, auth_header, route_db_session, pa):
    email, practitioner = pa

    async def _make():
        application = await make_eligible_application(route_db_session, practitioner)
        privilege = await make_privilege(
            route_db_session, await make_submitted_request(route_db_session, application)
        )
        await make_adverse_action(
            route_db_session,
            privilege,
            against=AdverseActionTarget.QUALIFYING_LICENSE,
            privilege_id=None,
            qualifying_license_id=application.qualifying_license_id,
            reporting_state_code='KS',
            effective_from=date(2026, 1, 1),
        )

    _call(client, _make)

    assert _dashboard(client, auth_header, email)['primary_action'] == {
        'kind': 'apply_for_privileges',
        'available': False,
        'reasons': ['two_year_bar'],
    }


def test_the_timeline_comes_from_history_with_the_state_s_note(
    client, auth_header, route_db_session, pa
):
    email, practitioner = pa

    async def _make():
        application = await _sent(route_db_session, practitioner)
        ctx = ChangeContext(await system_user_id(route_db_session), 'req-dash')
        await move(
            route_db_session,
            ctx,
            application,
            ApplicationStatus.INFO_REQUESTED,
            EventType.APPLICATION_INFO_REQUESTED,
            request_note='Upload your NCCPA certificate.',
        )
        before = history.snapshot(application)
        application.claimed_license_number = 'PA-9'
        await history.write(route_db_session, ctx, application, before=before)

    _call(client, _make)

    [application] = _dashboard(client, auth_header, email)['applications']
    assert [(e['kind'], e['status'], e['note']) for e in application['timeline']] == [
        ('applied', 'submitted', None),
        ('info_requested', 'info_requested', 'Upload your NCCPA certificate.'),
    ]
    # Midnight UTC on Oct 1 is Sep 30 in the compact's time zone; 60 days on (Rule 3 §3.7(a)(1)).
    assert application['resubmit_by'] == '2026-11-29'


async def _step(session, application, to, event, user_id=None, **fields):
    ctx = ChangeContext(user_id or await system_user_id(session), 'req-dash')
    await move(session, ctx, application, to, event, **fields)


def test_a_resubmit_and_the_pa_s_withdrawal_are_told_apart(
    client, auth_header, route_db_session, pa
):
    email, practitioner = pa

    async def _make():
        application = await _sent(route_db_session, practitioner)
        await _step(
            route_db_session,
            application,
            ApplicationStatus.INFO_REQUESTED,
            EventType.APPLICATION_INFO_REQUESTED,
            request_note='Upload your NCCPA certificate.',
        )
        await _step(
            route_db_session,
            application,
            ApplicationStatus.SUBMITTED,
            EventType.APPLICATION_RESUBMITTED,
            user_id=practitioner.user_id,
        )
        await _step(
            route_db_session,
            application,
            ApplicationStatus.WITHDRAWN,
            EventType.APPLICATION_WITHDRAWN,
            user_id=practitioner.user_id,
            withdrawn_at=_OPENED,
        )

    _call(client, _make)

    [application] = _dashboard(client, auth_header, email)['applications']
    assert [e['kind'] for e in application['timeline']] == [
        'applied',
        'info_requested',
        'resubmitted',
        'withdrawn_by_pa',
    ]
    assert application['resubmit_by'] is None


def test_a_later_application_is_applied_again_and_the_deadline_withdraws(
    client, auth_header, route_db_session, pa
):
    email, practitioner = pa

    async def _make():
        first = await _sent(route_db_session, practitioner)
        await _step(
            route_db_session,
            first,
            ApplicationStatus.INFO_REQUESTED,
            EventType.APPLICATION_INFO_REQUESTED,
            request_note='Upload your NCCPA certificate.',
        )
        await _step(
            route_db_session,
            first,
            ApplicationStatus.WITHDRAWN,
            EventType.APPLICATION_WITHDRAWN,
            withdrawn_at=_OPENED,
        )
        await _sent(route_db_session, practitioner)

    _call(client, _make)

    latest, first = _dashboard(client, auth_header, email)['applications']
    assert [e['kind'] for e in latest['timeline']] == ['applied_again']
    assert [e['kind'] for e in first['timeline']] == [
        'applied',
        'info_requested',
        'withdrawn_by_deadline',
    ]


def test_a_denial_shows_its_reason(client, auth_header, route_db_session, pa):
    email, practitioner = pa
    _call(
        client,
        lambda: make_application(
            route_db_session,
            practitioner,
            status='denied',
            opened_at=_OPENED,
            decided_at=_OPENED,
            decided_by=practitioner.created_by,
            denial_reason_code='nccpa_not_current',
            denial_reason_detail='Lapsed in 2025.',
        ),
    )

    [application] = _dashboard(client, auth_header, email)['applications']
    assert (application['denial_reason'], application['denial_reason_detail']) == (
        'Does not hold current NCCPA certification',
        'Lapsed in 2025.',
    )


def test_the_license_shows_who_verified_it(client, auth_header, route_db_session, pa):
    email, practitioner = pa
    _call(client, lambda: make_eligible_application(route_db_session, practitioner))

    license = _dashboard(client, auth_header, email)['qualifying_license']

    assert license['state_code'] == 'KS'
    assert license['verified_by_state'] == 'KS'
    assert license['verified_at'] == '2026-06-01T00:00:00Z'
    assert license['status'] in {'active', 'expired'}


def test_a_license_not_yet_verified_names_no_state(client, auth_header, route_db_session, pa):
    email, practitioner = pa

    async def _make():
        eligible = await make_eligible_application(route_db_session, practitioner)
        eligible.status = ApplicationStatus.SUPERSEDED
        eligible.superseded_at = _OPENED
        await make_application(
            route_db_session,
            practitioner,
            kind='change_sql',
            status='submitted',
            opened_at=_OPENED,
            qualifying_license_id=eligible.qualifying_license_id,
        )

    _call(client, _make)

    assert _dashboard(client, auth_header, email)['qualifying_license']['verified_by_state'] is None


def test_a_privilege_shows_days_to_expiry_and_its_history(
    client, auth_header, route_db_session, pa
):
    email, practitioner = pa

    async def _make():
        application = await make_eligible_application(route_db_session, practitioner)
        privilege = await make_privilege(
            route_db_session, await make_submitted_request(route_db_session, application)
        )
        ctx = ChangeContext(await system_user_id(route_db_session), 'req-dash')
        await history.write(route_db_session, ctx, privilege, before=None)
        await emit(route_db_session, ctx, EventType.PRIVILEGE_ISSUED, privilege)
        before = history.snapshot(privilege)
        privilege.administrator_status = AdministratorStatus.INACTIVE
        privilege.deactivation_reason = DeactivationReason.STATE_DEACTIVATED
        privilege.deactivated_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
        await history.write(route_db_session, ctx, privilege, before=before)
        before = history.snapshot(privilege)
        privilege.deactivation_note = 'Moved away.'
        await history.write(route_db_session, ctx, privilege, before=before)
        await emit(route_db_session, ctx, EventType.PRIVILEGE_DEACTIVATED, privilege)
        return privilege

    privilege = _call(client, _make)

    [shown] = _dashboard(client, auth_header, email)['privileges']
    assert shown['privilege_number'] == privilege.privilege_number
    assert shown['status'] == 'inactive'
    assert isinstance(shown['expires_in_days'], int)
    assert [(h['administrator_status'], h['reason']) for h in shown['history']] == [
        ('active', None),
        ('inactive', 'state_deactivated'),
    ]


def test_a_user_with_no_practitioner_record_has_no_dashboard(client, auth_header, route_db_session):
    email = _call(client, lambda: make_user(route_db_session, role='licensee')).email

    assert client.get(_ME, headers=auth_header(email)).status_code == 404


def test_the_dashboard_reads_the_database_on_each_request(
    client, auth_header, route_db_session, pa
):
    email, practitioner = pa
    assert _dashboard(client, auth_header, email)['applications'] == []

    _call(client, lambda: _sent(route_db_session, practitioner))

    assert [a['status'] for a in _dashboard(client, auth_header, email)['applications']] == [
        'submitted'
    ]
