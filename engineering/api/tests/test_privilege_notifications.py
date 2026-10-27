"""Privilege, payment, and qualifying license events email the PA, the states, and the Commission (FLOW-07)."""

from datetime import datetime, timezone

import pytest

from licensing_api.config import settings
from licensing_api.context import system_context
from licensing_api.notifications import privileges
from licensing_api.repo.domain_event import EventType
from licensing_api.repo.privilege import AdministratorStatus, DeactivationReason
from licensing_api.repo.privilege_request import PrivilegeRequestStatus
from licensing_api.repo.qualifying_license import LicenseStatus, QualifyingLicense
from tests.factories import (
    make_eligible_application,
    make_practitioner,
    make_privilege,
    make_qualifying_license,
    make_submitted_request,
)
from tests.notification_helpers import OPS, add_contacts, run_handler

_AT = datetime(2026, 7, 1, tzinfo=timezone.utc)
_PA = {'first_name': 'Pat', 'remote_state_name': 'Oklahoma'}


@pytest.fixture(autouse=True)
async def _setup(db_session, monkeypatch):
    monkeypatch.setattr(settings, 'commission_ops_email', OPS)
    await add_contacts(db_session, 'KS', 'OK', 'MO', 'CO')


async def _request(db_session, **overrides):
    pa = await make_practitioner(db_session, correspondence_email='pat@demo.example')
    application = await make_eligible_application(db_session, pa)
    return await make_submitted_request(db_session, application, **overrides)


async def test_a_paid_request_sends_the_pa_a_receipt_and_tells_the_remote_state(db_session):
    request = await _request(db_session)

    queued = await run_handler(
        db_session, privileges.send_privilege_requested, EventType.PRIVILEGE_REQUESTED, request
    )

    assert queued == [
        ('privilege_requested', 'pat@demo.example', _PA),
        (
            'privilege_requested_state',
            'ok-privileges@demo.example',
            {'remote_state_name': 'Oklahoma'},
        ),
    ]


async def test_a_declined_payment_tells_only_the_pa(db_session):
    request = await _request(
        db_session, status=PrivilegeRequestStatus.PENDING_PAYMENT, submitted_at=None
    )

    queued = await run_handler(
        db_session, privileges.send_payment_declined, EventType.PAYMENT_DECLINED, request
    )

    assert queued == [('payment_declined', 'pat@demo.example', _PA)]


async def test_an_issued_privilege_gives_the_pa_its_number_and_tells_the_sql_and_commission(
    db_session,
):
    privilege = await make_privilege(
        db_session, await _request(db_session), privilege_number='PA-OK-000042'
    )

    queued = await run_handler(
        db_session, privileges.send_privilege_issued, EventType.PRIVILEGE_ISSUED, privilege
    )

    staff = {'remote_state_name': 'Oklahoma'}
    assert queued == [
        (
            'privilege_issued',
            'pat@demo.example',
            _PA | {'privilege_number': 'PA-OK-000042', 'expires_on': '2027-12-31'},
        ),
        ('privilege_issued_staff', 'ks-applications@demo.example', staff),
        ('privilege_issued_staff', OPS, staff),
    ]


async def test_a_denied_request_gives_the_pa_the_reason(db_session):
    request = await _request(
        db_session,
        status=PrivilegeRequestStatus.DENIED,
        decided_at=_AT,
        decided_by=(await system_context(db_session)).user_id,
        denial_reason_code='nccpa_not_current',
    )

    queued = await run_handler(
        db_session, privileges.send_privilege_denied, EventType.PRIVILEGE_DENIED, request
    )

    staff = {'remote_state_name': 'Oklahoma'}
    assert queued == [
        (
            'privilege_denied',
            'pat@demo.example',
            _PA | {'denial_reason': 'Does not hold current NCCPA certification'},
        ),
        ('privilege_denied_staff', 'ks-applications@demo.example', staff),
        ('privilege_denied_staff', OPS, staff),
    ]


async def test_a_deactivation_gives_the_pa_the_states_note_and_tells_the_remote_state(db_session):
    privilege = await make_privilege(
        db_session,
        await _request(db_session),
        privilege_number='PA-OK-000042',
        administrator_status=AdministratorStatus.INACTIVE,
        deactivation_reason=DeactivationReason.STATE_DEACTIVATED,
        deactivated_at=_AT,
        deactivation_note='Supervision agreement lapsed.',
    )

    queued = await run_handler(
        db_session,
        privileges.send_privilege_deactivated,
        EventType.PRIVILEGE_DEACTIVATED,
        privilege,
    )

    staff = {'remote_state_name': 'Oklahoma', 'privilege_number': 'PA-OK-000042'}
    assert queued == [
        (
            'privilege_deactivated',
            'pat@demo.example',
            staff | {'first_name': 'Pat', 'note': 'Supervision agreement lapsed.'},
        ),
        ('privilege_deactivated_state', 'ok-privileges@demo.example', staff),
    ]


@pytest.mark.parametrize(
    ('event_type', 'template'),
    [
        (EventType.PRIVILEGE_EXPIRING, 'privilege_expiring'),
        (EventType.PRIVILEGE_EXPIRED, 'privilege_expired'),
    ],
)
async def test_expiry_tells_only_the_pa(db_session, event_type, template):
    privilege = await make_privilege(
        db_session, await _request(db_session), privilege_number='PA-OK-000042'
    )

    queued = await run_handler(db_session, privileges.send_privilege_expiry, event_type, privilege)

    assert queued == [
        (
            template,
            'pat@demo.example',
            _PA | {'privilege_number': 'PA-OK-000042', 'expires_on': '2027-12-31'},
        )
    ]


async def test_a_license_change_tells_the_pa_and_each_remote_state_whose_privilege_rests_on_it(
    db_session,
):
    pa = await make_practitioner(db_session, correspondence_email='pat@demo.example')
    application = await make_eligible_application(db_session, pa)
    # OK's privilege is active; MO's the cascade just deactivated; CO's ended for another reason.
    for state, overrides in (
        ('OK', {}),
        (
            'MO',
            {
                'administrator_status': AdministratorStatus.INACTIVE,
                'deactivation_reason': DeactivationReason.QUALIFYING_LICENSE_INACTIVE,
                'deactivated_at': _AT,
            },
        ),
        (
            'CO',
            {
                'administrator_status': AdministratorStatus.INACTIVE,
                'deactivation_reason': DeactivationReason.STATE_DEACTIVATED,
                'deactivated_at': _AT,
            },
        ),
    ):
        request = await make_submitted_request(db_session, application, remote_state_code=state)
        await make_privilege(db_session, request, **overrides)
    license = await db_session.get_one(QualifyingLicense, application.qualifying_license_id)
    license.state_reported_status = LicenseStatus.INACTIVE

    queued = await run_handler(
        db_session,
        privileges.send_license_status_changed,
        EventType.QUALIFYING_LICENSE_STATUS_CHANGED,
        license,
    )

    context = {'state_name': 'Kansas', 'status': 'inactive'}
    assert queued == [
        ('license_status_changed', 'pat@demo.example', context | {'first_name': 'Pat'}),
        ('license_status_changed_state', 'mo-privileges@demo.example', context),
        ('license_status_changed_state', 'ok-privileges@demo.example', context),
    ]


async def test_a_change_to_a_license_no_pa_has_claimed_emails_no_one(db_session):
    pa = await make_practitioner(db_session)
    license = await make_qualifying_license(db_session, pa, practitioner_id=None)

    queued = await run_handler(
        db_session,
        privileges.send_license_status_changed,
        EventType.QUALIFYING_LICENSE_STATUS_CHANGED,
        license,
    )

    assert queued == []
