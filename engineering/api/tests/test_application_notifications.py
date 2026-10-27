"""Practitioner and application events email the PA, the state, and the Commission (FLOW-07)."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.config import settings
from licensing_api.context import system_context
from licensing_api.events import HandlerRegistry
from licensing_api.handlers import HANDLERS
from licensing_api.notifications import applications
from licensing_api.repo.domain_event import EventType, emit
from licensing_api.repo.notification import Notification
from licensing_api.repo.participation_application import ApplicationStatus, ParticipationApplication
from licensing_api.repo.privilege import AdministratorStatus, DeactivationReason
from tests.factories import (
    make_application,
    make_eligible_application,
    make_practitioner,
    make_privilege,
    make_submitted_request,
    make_user,
)
from tests.notification_helpers import OPS, add_contacts, run_handler


@pytest.fixture(autouse=True)
def _commission_ops(monkeypatch):
    monkeypatch.setattr(settings, 'commission_ops_email', OPS)


@pytest.fixture
async def contacts(db_session):
    """KS and OK contacts for each purpose, plus MO's, which the tests must never reach."""
    await add_contacts(db_session, 'KS', 'OK', 'MO')


_AT = datetime(2026, 7, 1, tzinfo=timezone.utc)


async def _application(session: AsyncSession, **overrides: object) -> ParticipationApplication:
    pa = await make_practitioner(session, correspondence_email='pat@demo.example')
    return await make_application(session, pa, opened_at=_AT, **overrides)


def test_every_handler_is_registered_once():
    registry = HandlerRegistry(HANDLERS)

    assert all(registry.named(h.name) is h for h in applications.APPLICATION_HANDLERS)


async def test_a_new_pa_is_welcomed_at_their_correspondence_email(db_session):
    pa = await make_practitioner(db_session, correspondence_email='pat@demo.example')

    queued = await run_handler(
        db_session, applications.send_welcome, EventType.PRACTITIONER_REGISTERED, pa
    )

    assert queued == [('welcome', 'pat@demo.example', {'first_name': 'Pat'})]


async def test_a_pa_with_no_correspondence_email_is_written_to_at_their_sign_in_email(db_session):
    user = await make_user(db_session, role='licensee', email='signin@demo.example')
    pa = await make_practitioner(db_session, user_id=user.id, legal_first_name=None)

    queued = await run_handler(
        db_session, applications.send_welcome, EventType.PRACTITIONER_REGISTERED, pa
    )

    assert queued == [('welcome', 'signin@demo.example', {'first_name': None})]


async def test_a_submitted_application_emails_the_pa_and_the_qualifying_states_contacts(
    db_session, contacts
):
    application = await _application(db_session, status=ApplicationStatus.SUBMITTED)

    queued = await run_handler(
        db_session,
        applications.send_application_submitted,
        EventType.APPLICATION_SUBMITTED,
        application,
    )

    assert queued == [
        (
            'application_submitted',
            'pat@demo.example',
            {'first_name': 'Pat', 'state_name': 'Kansas'},
        ),
        ('application_submitted_state', 'ks-applications@demo.example', {'state_name': 'Kansas'}),
    ]


async def test_an_information_request_sends_a_link_and_never_the_note(db_session, contacts):
    application = await _application(
        db_session,
        status=ApplicationStatus.INFO_REQUESTED,
        request_note='Upload your NCCPA certificate; the one on file has expired.',
    )

    queued = await run_handler(
        db_session,
        applications.send_application_info_requested,
        EventType.APPLICATION_INFO_REQUESTED,
        application,
    )

    assert queued == [
        (
            'application_info_requested',
            'pat@demo.example',
            {'first_name': 'Pat', 'state_name': 'Kansas'},
        )
    ]


async def test_a_resubmission_emails_only_the_qualifying_states_contacts(db_session, contacts):
    application = await _application(db_session, status=ApplicationStatus.SUBMITTED)

    queued = await run_handler(
        db_session,
        applications.send_application_resubmitted,
        EventType.APPLICATION_RESUBMITTED,
        application,
    )

    assert queued == [
        ('application_resubmitted_state', 'ks-applications@demo.example', {'state_name': 'Kansas'})
    ]


async def test_an_eligible_decision_emails_the_pa_and_the_commission(db_session, contacts):
    application = await make_eligible_application(
        db_session, await make_practitioner(db_session, correspondence_email='pat@demo.example')
    )

    queued = await run_handler(
        db_session,
        applications.send_application_decided,
        EventType.APPLICATION_ELIGIBLE,
        application,
    )

    assert queued == [
        ('application_eligible', 'pat@demo.example', {'first_name': 'Pat', 'state_name': 'Kansas'}),
        ('application_decided_commission', OPS, {'state_name': 'Kansas', 'eligible': True}),
    ]


async def test_a_denial_names_its_reason_and_no_commission_email_goes_while_unset(
    db_session, monkeypatch
):
    monkeypatch.setattr(settings, 'commission_ops_email', '')
    application = await _application(
        db_session,
        status=ApplicationStatus.DENIED,
        denial_reason_code='nccpa_not_current',
        decided_at=_AT,
        decided_by=(await system_context(db_session)).user_id,
    )

    queued = await run_handler(
        db_session, applications.send_application_decided, EventType.APPLICATION_DENIED, application
    )

    assert queued == [
        (
            'application_denied',
            'pat@demo.example',
            {
                'first_name': 'Pat',
                'state_name': 'Kansas',
                'denial_reason': 'Does not hold current NCCPA certification',
            },
        )
    ], 'no Commission email while commission_ops_email is unset (Q-14)'


async def test_a_withdrawn_application_emails_the_pa_and_the_qualifying_state(db_session, contacts):
    application = await _application(
        db_session, status=ApplicationStatus.WITHDRAWN, withdrawn_at=_AT
    )

    queued = await run_handler(
        db_session,
        applications.send_application_withdrawn,
        EventType.APPLICATION_WITHDRAWN,
        application,
    )

    assert queued == [
        (
            'application_withdrawn',
            'pat@demo.example',
            {'first_name': 'Pat', 'state_name': 'Kansas'},
        ),
        ('application_withdrawn_state', 'ks-applications@demo.example', {'state_name': 'Kansas'}),
    ]


async def test_withdrawn_eligibility_emails_each_remote_state_where_the_pa_held_a_privilege(
    db_session, contacts
):
    pa = await make_practitioner(db_session, correspondence_email='pat@demo.example')
    application = await make_eligible_application(db_session, pa)
    # OK's privilege was already deactivated by the cascade; MO's for an unrelated reason.
    for state, reason in (
        ('OK', DeactivationReason.ELIGIBILITY_WITHDRAWN),
        ('MO', DeactivationReason.STATE_DEACTIVATED),
    ):
        await make_privilege(
            db_session,
            await make_submitted_request(db_session, application, remote_state_code=state),
            administrator_status=AdministratorStatus.INACTIVE,
            deactivation_reason=reason,
            deactivated_at=_AT,
        )
    application.status = ApplicationStatus.ELIGIBILITY_WITHDRAWN
    application.eligibility_withdrawn_at = _AT
    application.eligibility_withdrawal_reason = 'Qualifying license revoked'

    queued = await run_handler(
        db_session,
        applications.send_eligibility_withdrawn,
        EventType.APPLICATION_ELIGIBILITY_WITHDRAWN,
        application,
    )

    assert queued == [
        (
            'application_eligibility_withdrawn',
            'pat@demo.example',
            {'first_name': 'Pat', 'state_name': 'Kansas'},
        ),
        (
            'application_eligibility_withdrawn_state',
            'ok-privileges@demo.example',
            {'state_name': 'Kansas', 'remote_state_name': 'Oklahoma'},
        ),
    ]


async def test_a_handler_that_runs_twice_queues_each_email_once(db_session, contacts):
    application = await _application(db_session, status=ApplicationStatus.SUBMITTED)
    ctx = await system_context(db_session)
    event = await emit(db_session, ctx, EventType.APPLICATION_SUBMITTED, application)

    await applications.send_application_submitted.run(db_session, ctx, event)
    await applications.send_application_submitted.run(db_session, ctx, event)

    keys = (await db_session.scalars(select(col(Notification.idempotency_key)))).all()
    assert sorted(keys) == [
        f'{event.event_id}:application_submitted:pat@demo.example',
        f'{event.event_id}:application_submitted_state:ks-applications@demo.example',
    ]
