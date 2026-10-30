"""Adverse action and SII events email every other state the PA holds a license or privilege in (FLOW-07)."""

from datetime import date

import pytest

from licensing_api.config import settings
from licensing_api.context import system_context
from licensing_api.notifications import discipline
from licensing_api.repo.adverse_action import AdverseActionTarget
from licensing_api.repo.domain_event import EventType
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.privilege import Privilege
from licensing_api.repo.sii_report import SiiReport
from tests.factories import make_adverse_action, make_issued_privilege
from tests.notification_helpers import OPS, add_contacts, run_handler


@pytest.fixture(autouse=True)
async def _setup(db_session, monkeypatch):
    monkeypatch.setattr(settings, 'commission_ops_email', OPS)
    await add_contacts(db_session, 'KS', 'OK', 'MO')


async def _privilege(db_session) -> Privilege:
    """A KS-licensed PA with a privilege in OK; MO, where they hold nothing, must never be told."""
    privilege = await make_issued_privilege(db_session)
    practitioner = await db_session.get_one(Practitioner, privilege.practitioner_id)
    practitioner.correspondence_email = 'pat@demo.example'
    return privilege


@pytest.mark.parametrize(
    ('event_type', 'template'),
    [
        (EventType.ADVERSE_ACTION_REPORTED, 'adverse_action_reported'),
        (EventType.ADVERSE_ACTION_LIFTED, 'adverse_action_lifted'),
    ],
)
async def test_an_adverse_action_tells_the_pa_the_other_states_and_the_commission(
    db_session, event_type, template
):
    action = await make_adverse_action(db_session, await _privilege(db_session), is_emergency=True)

    queued = await run_handler(db_session, discipline.send_adverse_action, event_type, action)

    context = {'reporting_state_name': 'Oklahoma', 'against_license': False, 'is_emergency': True}
    assert queued == [
        (template, 'pat@demo.example', context | {'first_name': 'Pat'}),
        (f'{template}_staff', 'ks-discipline@demo.example', context),
        (f'{template}_staff', OPS, context),
    ], 'OK reported it, so only KS, where the PA is licensed, is told'


async def test_an_action_against_the_license_says_so(db_session):
    privilege = await _privilege(db_session)
    action = await make_adverse_action(
        db_session,
        privilege,
        against=AdverseActionTarget.QUALIFYING_LICENSE,
        privilege_id=None,
        qualifying_license_id=privilege.qualifying_license_id,
        reporting_state_code='KS',
    )

    queued = await run_handler(
        db_session, discipline.send_adverse_action, EventType.ADVERSE_ACTION_REPORTED, action
    )

    assert [(template, address) for template, address, _ in queued] == [
        ('adverse_action_reported', 'pat@demo.example'),
        ('adverse_action_reported_staff', 'ok-discipline@demo.example'),
        ('adverse_action_reported_staff', OPS),
    ]
    assert queued[0][2]['against_license'] is True


@pytest.mark.parametrize(
    ('event_type', 'template'),
    [(EventType.SII_FLAGGED, 'sii_flagged_state'), (EventType.SII_CLOSED, 'sii_closed_state')],
)
async def test_sii_tells_only_the_other_states_never_the_pa(db_session, event_type, template):
    privilege = await _privilege(db_session)
    report = SiiReport(
        practitioner_id=privilege.practitioner_id,
        reporting_state_code='KS',
        qualifying_license_id=privilege.qualifying_license_id,
        description='Complaint under investigation.',
        contact_name='KS investigator',
        contact_email='investigations@ks.demo.example',
        determined_on=date(2026, 7, 1),
        created_by=(await system_context(db_session)).user_id,
    )
    db_session.add(report)

    queued = await run_handler(db_session, discipline.send_sii, event_type, report)

    assert queued == [
        (template, 'ok-discipline@demo.example', {'reporting_state_name': 'Kansas'}),
    ]
