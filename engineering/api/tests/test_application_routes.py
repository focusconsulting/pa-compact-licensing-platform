"""A PA's application routes: draft, save, attestations, submit, resubmit, withdraw (SCRUM-111)."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import update
from sqlmodel import col, select

from licensing_api.context import ChangeContext
from licensing_api.repo.application_transition import move
from licensing_api.repo.attestation import Attestation, ParticipationApplicationAttestation
from licensing_api.repo.document import Document, DocumentOwnerType
from licensing_api.repo.domain_event import DomainEvent, EventType
from licensing_api.repo.history import ParticipationApplicationHistory
from licensing_api.repo.participation_application import (
    ApplicationStatus,
    ParticipationApplication,
)
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.state import State
from licensing_api.repo.user import User
from tests.factories import (
    make_application,
    make_eligible_application,
    make_practitioner,
    make_user,
    system_user_id,
)

_ME = '/api/me/applications'
_SWORN = {'sworn': True, 'sworn_name': 'Pat Assistant'}


@pytest.fixture
def pa(client, route_db_session):
    """A signed-in PA, with Kansas and Oklahoma live."""

    async def _make() -> tuple[str, Practitioner]:
        for code in ('KS', 'OK'):
            await route_db_session.execute(
                update(State).where(col(State.code) == code).values(is_member=True, is_live=True)
            )
        practitioner = await make_practitioner(route_db_session)
        user = await route_db_session.get(User, practitioner.user_id)
        return user.email, practitioner

    return client.portal.call(_make)


def _db(client, coroutine_function):
    return client.portal.call(coroutine_function)


def _start(client, auth_header, email, state='KS') -> dict:
    response = client.post(_ME, json={'sql_state_code': state}, headers=auth_header(email))
    assert response.status_code == 201, response.json()
    return response.json()['data']


def _accept_all(client, auth_header, email, application_id) -> None:
    current = client.get('/api/public/attestations', params={'applies_to': 'participation'}).json()[
        'data'
    ]
    for attestation in current:
        response = client.post(
            f'{_ME}/{application_id}/attestations',
            json={'code': attestation['code'], 'version': attestation['version']},
            headers=auth_header(email),
        )
        assert response.status_code == 201, response.json()


def _ready(client, auth_header, email) -> dict:
    application = _start(client, auth_header, email)
    _accept_all(client, auth_header, email, application['id'])
    return application


def _events(client, session, application_id) -> list[str]:
    async def _read():
        application = await _row(session, application_id)
        statement = select(DomainEvent.type).where(
            col(DomainEvent.aggregate_type) == 'participation_applications',
            col(DomainEvent.aggregate_id) == application.id,
        )
        return list((await session.scalars(statement)).all())

    return _db(client, _read)


def _histories(client, session, application_id) -> list[ParticipationApplicationHistory]:
    async def _read():
        application = await _row(session, application_id)
        statement = (
            select(ParticipationApplicationHistory)
            .where(col(ParticipationApplicationHistory.entity_id) == application.id)
            .order_by(col(ParticipationApplicationHistory.id))
        )
        return list((await session.scalars(statement)).all())

    return _db(client, _read)


async def _row(session, application_id) -> ParticipationApplication:
    statement = select(ParticipationApplication).where(
        col(ParticipationApplication.public_id) == UUID(application_id)
    )
    return (await session.scalars(statement)).one()


def _set(client, session, application_id, **fields) -> None:
    async def _write():
        application = await _row(session, application_id)
        await session.execute(
            update(ParticipationApplication)
            .where(col(ParticipationApplication.id) == application.id)
            .values(**fields)
        )
        session.expunge_all()

    _db(client, _write)


def _upload(client, session, practitioner, **overrides) -> str:
    async def _make():
        public_id = uuid4()
        fields = {
            'public_id': public_id,
            'kind': 'nccpa_certificate',
            'file_name': 'nccpa.pdf',
            'content_type': 'application/pdf',
            'size_bytes': 1000,
            'storage_key': f'documents/{public_id}',
            'created_by': practitioner.user_id,
            **overrides,
        }
        session.add(Document(**fields))
        await session.flush()
        return str(public_id)

    return _db(client, _make)


def test_a_pa_starts_a_draft_that_writes_no_history_or_event(
    client, auth_header, route_db_session, pa
):
    email, _ = pa

    application = _start(client, auth_header, email)

    assert application | {'id': None} == {
        'id': None,
        'kind': 'initial',
        'status': 'draft',
        'sql_state_code': 'KS',
        'claimed_license_number': None,
        'claimed_license_expires_on': None,
        'opened_at': None,
        'request_note': None,
        'response_note': None,
        'requested_at': None,
        'resubmit_by': None,
        'withdrawn_at': None,
        'sworn_at': None,
        'attestations': [],
        'documents': [],
    }
    assert _histories(client, route_db_session, application['id']) == []
    assert _events(client, route_db_session, application['id']) == []


def test_a_pa_with_an_open_application_continues_it(client, auth_header, pa):
    email, _ = pa
    _start(client, auth_header, email)

    response = client.post(_ME, json={'sql_state_code': 'OK'}, headers=auth_header(email))

    assert response.status_code == 409
    assert response.json()['code'] == 'APPLICATION_OPEN'


def test_only_a_live_state_can_be_designated(client, auth_header, pa):
    email, _ = pa

    response = client.post(_ME, json={'sql_state_code': 'TX'}, headers=auth_header(email))

    assert response.status_code == 409
    assert response.json()['code'] == 'STATE_NOT_LIVE'


def test_an_eligible_pa_cannot_start_another_application(client, auth_header, route_db_session, pa):
    email, practitioner = pa
    _db(client, lambda: make_eligible_application(route_db_session, practitioner))

    response = client.post(_ME, json={'sql_state_code': 'OK'}, headers=auth_header(email))

    assert (response.status_code, response.json()['code']) == (409, 'ALREADY_ELIGIBLE')


def test_a_user_with_no_practitioner_record_has_no_applications(
    client, auth_header, route_db_session
):
    email = _db(client, lambda: make_user(route_db_session, role='licensee')).email

    response = client.get(_ME, headers=auth_header(email))

    assert response.status_code == 404


def test_a_pa_lists_only_their_own_applications_newest_first(
    client, auth_header, route_db_session, pa
):
    email, practitioner = pa

    async def _make():
        other = await make_practitioner(route_db_session)
        await make_application(route_db_session, other)
        await make_application(
            route_db_session,
            practitioner,
            status='withdrawn',
            opened_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            withdrawn_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    _db(client, _make)
    draft = _start(client, auth_header, email, 'OK')

    statuses = [
        (a['id'], a['status']) for a in client.get(_ME, headers=auth_header(email)).json()['data']
    ]

    assert statuses[0] == (draft['id'], 'draft')
    assert [s for _, s in statuses] == ['draft', 'withdrawn']


def test_another_pa_s_application_is_not_found(client, auth_header, route_db_session, pa):
    email, _ = pa
    application = _start(client, auth_header, email)
    stranger = _db(client, lambda: make_practitioner(route_db_session))
    stranger_email = _db(client, lambda: route_db_session.get(User, stranger.user_id)).email

    response = client.get(f'{_ME}/{application["id"]}', headers=auth_header(stranger_email))

    assert response.status_code == 404


def test_a_saved_step_survives_signing_out(client, auth_header, pa):
    email, _ = pa
    application = _start(client, auth_header, email)

    client.patch(
        f'{_ME}/{application["id"]}',
        json={'claimed_license_number': ' PA-12345 ', 'claimed_license_expires_on': '2027-12-31'},
        headers=auth_header(email),
    )
    saved = client.get(f'{_ME}/{application["id"]}', headers=auth_header(email)).json()['data']

    assert (saved['claimed_license_number'], saved['claimed_license_expires_on']) == (
        'PA-12345',
        '2027-12-31',
    )


def test_a_draft_can_change_its_state(client, auth_header, pa):
    email, _ = pa
    application = _start(client, auth_header, email)

    response = client.patch(
        f'{_ME}/{application["id"]}', json={'sql_state_code': 'OK'}, headers=auth_header(email)
    )

    assert response.json()['data']['sql_state_code'] == 'OK'


def test_the_state_cannot_change_once_the_sql_has_the_application(
    client, auth_header, route_db_session, pa
):
    email, _ = pa
    application = _start(client, auth_header, email)
    _set(
        client,
        route_db_session,
        application['id'],
        status='info_requested',
        opened_at=datetime.now(timezone.utc),
    )

    moved = client.patch(
        f'{_ME}/{application["id"]}', json={'sql_state_code': 'OK'}, headers=auth_header(email)
    )
    fixed = client.patch(
        f'{_ME}/{application["id"]}',
        json={'claimed_license_number': 'PA-9'},
        headers=auth_header(email),
    )

    assert (moved.status_code, moved.json()['code']) == (409, 'INVALID_TRANSITION')
    assert fixed.json()['data']['claimed_license_number'] == 'PA-9'


def test_a_submitted_application_cannot_be_changed(client, auth_header, route_db_session, pa):
    email, _ = pa
    application = _start(client, auth_header, email)
    _set(
        client,
        route_db_session,
        application['id'],
        status='submitted',
        opened_at=datetime.now(timezone.utc),
    )

    response = client.patch(
        f'{_ME}/{application["id"]}',
        json={'claimed_license_number': 'PA-9'},
        headers=auth_header(email),
    )

    assert (response.status_code, response.json()['code']) == (409, 'INVALID_TRANSITION')


def test_accepting_an_attestation_shows_on_the_application(client, auth_header, pa):
    email, _ = pa
    application = _start(client, auth_header, email)

    response = client.post(
        f'{_ME}/{application["id"]}/attestations',
        json={'code': 'service_of_process', 'version': 1},
        headers=auth_header(email),
    )

    assert response.status_code == 201
    assert [(a['code'], a['version']) for a in response.json()['data']['attestations']] == [
        ('service_of_process', 1)
    ]


def test_an_old_version_cannot_be_accepted(client, auth_header, route_db_session, pa):
    email, _ = pa
    application = _start(client, auth_header, email)

    async def _reword():
        original = await route_db_session.get(Attestation, ('service_of_process', 1))
        route_db_session.add(
            Attestation(
                **original.model_dump(include={'code', 'applies_to', 'sort_order', 'source'}),
                version=2,
                text='Reworded',
                created_by=await system_user_id(route_db_session),
            )
        )
        await route_db_session.flush()

    _db(client, _reword)

    response = client.post(
        f'{_ME}/{application["id"]}/attestations',
        json={'code': 'service_of_process', 'version': 1},
        headers=auth_header(email),
    )

    assert (response.status_code, response.json()) == (
        409,
        {'code': 'ATTESTATIONS_OUT_OF_DATE', 'details': ['service_of_process']},
    )


@pytest.mark.parametrize(
    'body',
    [
        {'code': 'no_such_thing', 'version': 1},
        {'code': 'supervision_compliance', 'version': 1},
        {'code': 'nccpa_current', 'version': 1},
    ],
)
def test_only_a_participation_attestation_can_be_accepted(client, auth_header, pa, body):
    email, _ = pa
    application = _start(client, auth_header, email)

    response = client.post(
        f'{_ME}/{application["id"]}/attestations', json=body, headers=auth_header(email)
    )

    assert response.status_code == 404


def test_attestations_cannot_change_on_a_submitted_application(
    client, auth_header, route_db_session, pa
):
    email, _ = pa
    application = _start(client, auth_header, email)
    _set(
        client,
        route_db_session,
        application['id'],
        status='submitted',
        opened_at=datetime.now(timezone.utc),
    )

    response = client.post(
        f'{_ME}/{application["id"]}/attestations',
        json={'code': 'service_of_process', 'version': 1},
        headers=auth_header(email),
    )

    assert response.status_code == 409


def test_submitting_opens_the_application_and_records_it_as_sent(
    client, auth_header, route_db_session, pa
):
    email, practitioner = pa
    application = _ready(client, auth_header, email)
    document_id = _upload(client, route_db_session, practitioner)

    response = client.post(
        f'{_ME}/{application["id"]}/submit',
        json={**_SWORN, 'sworn_name': '  Pat Assistant ', 'document_ids': [document_id]},
        headers=auth_header(email),
    )

    data = response.json()['data']
    assert response.status_code == 200
    assert data['status'] == 'submitted'
    assert data['opened_at'] is not None
    assert data['sworn_at'] == data['opened_at']
    assert [d['id'] for d in data['documents']] == [document_id]
    row = _db(client, lambda: _row(route_db_session, application['id']))
    assert (row.sworn_name, row.sworn_ip) == ('Pat Assistant', 'testclient')
    assert _events(client, route_db_session, application['id']) == [EventType.APPLICATION_SUBMITTED]
    [history] = _histories(client, route_db_session, application['id'])
    assert history.previous is None
    assert history.updated['status'] == 'submitted'
    assert history.updated['sql_state_code'] == 'KS'


def test_an_application_is_not_submitted_until_every_attestation_is_accepted(
    client, auth_header, route_db_session, pa
):
    email, _ = pa
    application = _start(client, auth_header, email)
    client.post(
        f'{_ME}/{application["id"]}/attestations',
        json={'code': 'service_of_process', 'version': 1},
        headers=auth_header(email),
    )

    response = client.post(
        f'{_ME}/{application["id"]}/submit', json=_SWORN, headers=auth_header(email)
    )

    assert response.status_code == 409
    assert response.json()['code'] == 'ATTESTATIONS_OUT_OF_DATE'
    assert 'service_of_process' not in response.json()['details']
    assert 'truthfulness' in response.json()['details']
    assert _db(client, lambda: _row(route_db_session, application['id'])).status == 'draft'


def test_an_application_cannot_be_submitted_to_a_state_no_longer_live(
    client, auth_header, route_db_session, pa
):
    email, _ = pa
    application = _ready(client, auth_header, email)

    async def _close():
        await route_db_session.execute(
            update(State).where(col(State.code) == 'KS').values(is_live=False)
        )

    _db(client, _close)

    response = client.post(
        f'{_ME}/{application["id"]}/submit', json=_SWORN, headers=auth_header(email)
    )

    assert (response.status_code, response.json()['code']) == (409, 'STATE_NOT_LIVE')


@pytest.mark.parametrize(
    'owner',
    [
        'someone_else',
        'attached',
        'state',
    ],
)
def test_submit_sends_only_the_pa_s_own_unattached_uploads(
    client, auth_header, route_db_session, pa, owner
):
    email, practitioner = pa
    application = _ready(client, auth_header, email)
    mine = _upload(client, route_db_session, practitioner)
    if owner == 'someone_else':
        other = _db(client, lambda: make_practitioner(route_db_session))
        theirs = _upload(client, route_db_session, other)
    elif owner == 'attached':
        theirs = _upload(
            client,
            route_db_session,
            practitioner,
            owner_type=DocumentOwnerType.PRACTITIONER,
            owner_id=practitioner.id,
        )
    else:
        theirs = _upload(client, route_db_session, practitioner, uploaded_in_state='KS')

    response = client.post(
        f'{_ME}/{application["id"]}/submit',
        json={**_SWORN, 'document_ids': [mine, theirs]},
        headers=auth_header(email),
    )

    assert response.status_code == 404
    row = _db(client, lambda: _row(route_db_session, application['id']))
    assert row.status == 'draft'


@pytest.mark.parametrize(
    'body',
    [
        {'sworn': False, 'sworn_name': 'Pat'},
        {'sworn': True, 'sworn_name': '   '},
        {'sworn_name': 'Pat'},
    ],
)
def test_submit_needs_the_sworn_statement(client, auth_header, pa, body):
    email, _ = pa
    application = _ready(client, auth_header, email)

    response = client.post(
        f'{_ME}/{application["id"]}/submit', json=body, headers=auth_header(email)
    )

    assert response.status_code == 422


def test_resubmitting_keeps_the_clock_and_the_note(client, auth_header, route_db_session, pa):
    email, _ = pa
    application = _ready(client, auth_header, email)
    opened = datetime(2026, 10, 1, tzinfo=timezone.utc)
    _set(
        client,
        route_db_session,
        application['id'],
        status='info_requested',
        opened_at=opened,
        request_note='Upload your NCCPA certificate.',
    )

    response = client.post(
        f'{_ME}/{application["id"]}/submit', json=_SWORN, headers=auth_header(email)
    )

    data = response.json()['data']
    assert data['status'] == 'submitted'
    assert datetime.fromisoformat(data['opened_at']) == opened
    assert data['request_note'] == 'Upload your NCCPA certificate.'
    assert _events(client, route_db_session, application['id']) == [
        EventType.APPLICATION_RESUBMITTED
    ]


def _asked(client, auth_header, route_db_session, email) -> dict:
    """An application the PA submitted on Oct 14 that the state then asked about, as epic 7 will."""
    application = _ready(client, auth_header, email)
    response = client.post(
        f'{_ME}/{application["id"]}/submit', json=_SWORN, headers=auth_header(email)
    )
    assert response.status_code == 200, response.json()
    _set(
        client,
        route_db_session,
        application['id'],
        opened_at=datetime(2026, 10, 14, 15, tzinfo=timezone.utc),
    )

    async def _ask():
        row = await _row(route_db_session, application['id'])
        ctx = ChangeContext(await system_user_id(route_db_session), 'req-ask')
        await move(
            route_db_session,
            ctx,
            row,
            ApplicationStatus.INFO_REQUESTED,
            EventType.APPLICATION_INFO_REQUESTED,
            request_note='Upload your NCCPA certificate.',
        )
        await route_db_session.commit()

    _db(client, _ask)
    return application


def test_a_request_shows_when_the_state_asked_and_the_last_day_to_resubmit(
    client, auth_header, route_db_session, pa
):
    email, _ = pa
    application = _asked(client, auth_header, route_db_session, email)

    data = client.get(f'{_ME}/{application["id"]}', headers=auth_header(email)).json()['data']

    assert data['requested_at'] is not None
    # 60 days from Oct 14 (Rule 3 §3.7(a)(1)), as B-n4 and B12 show.
    assert data['resubmit_by'] == '2026-12-13'


def test_resubmitting_needs_every_statement_accepted_again(
    client, auth_header, route_db_session, pa
):
    email, _ = pa
    application = _asked(client, auth_header, route_db_session, email)
    url = f'{_ME}/{application["id"]}/submit'

    refused = client.post(url, json=_SWORN, headers=auth_header(email))
    _accept_all(client, auth_header, email, application['id'])
    _accept_all(client, auth_header, email, application['id'])
    resubmitted = client.post(url, json=_SWORN, headers=auth_header(email))

    assert (refused.status_code, refused.json()['code']) == (409, 'ATTESTATIONS_OUT_OF_DATE')
    assert len(refused.json()['details']) == 4
    assert resubmitted.json()['data']['status'] == 'submitted'
    assert resubmitted.json()['data']['requested_at'] is None

    async def _acceptances():
        row = await _row(route_db_session, application['id'])
        statement = select(ParticipationApplicationAttestation).where(
            col(ParticipationApplicationAttestation.participation_application_id) == row.id
        )
        return len((await route_db_session.scalars(statement)).all())

    # Each statement once to submit and once to resubmit; accepting twice in a row adds nothing.
    assert _db(client, _acceptances) == 8


def test_a_pa_replies_to_the_state_s_request_and_history_keeps_the_reply(
    client, auth_header, route_db_session, pa
):
    email, _ = pa
    application = _asked(client, auth_header, route_db_session, email)
    url = f'{_ME}/{application["id"]}'

    cleared = client.patch(url, json={'response_note': '  '}, headers=auth_header(email))
    replied = client.patch(
        url, json={'response_note': ' Attached my certificate. '}, headers=auth_header(email)
    )
    _accept_all(client, auth_header, email, application['id'])
    client.post(f'{url}/submit', json=_SWORN, headers=auth_header(email))

    assert cleared.json()['data']['response_note'] is None
    assert replied.json()['data']['response_note'] == 'Attached my certificate.'
    assert _histories(client, route_db_session, application['id'])[-1].updated['response_note'] == (
        'Attached my certificate.'
    )


def test_only_a_request_takes_a_reply(client, auth_header, pa):
    email, _ = pa
    application = _start(client, auth_header, email)

    response = client.patch(
        f'{_ME}/{application["id"]}',
        json={'response_note': 'Hello.'},
        headers=auth_header(email),
    )

    assert (response.status_code, response.json()['code']) == (409, 'INVALID_TRANSITION')


def test_a_submitted_application_cannot_be_submitted_again(
    client, auth_header, route_db_session, pa
):
    email, _ = pa
    application = _ready(client, auth_header, email)
    client.post(f'{_ME}/{application["id"]}/submit', json=_SWORN, headers=auth_header(email))

    response = client.post(
        f'{_ME}/{application["id"]}/submit', json=_SWORN, headers=auth_header(email)
    )

    assert (response.status_code, response.json()['code']) == (409, 'INVALID_TRANSITION')


def test_a_pa_withdraws_a_submitted_application(client, auth_header, route_db_session, pa):
    email, _ = pa
    application = _ready(client, auth_header, email)
    client.post(f'{_ME}/{application["id"]}/submit', json=_SWORN, headers=auth_header(email))

    response = client.post(f'{_ME}/{application["id"]}/withdraw', headers=auth_header(email))

    assert response.json()['data']['status'] == 'withdrawn'
    assert response.json()['data']['withdrawn_at'] is not None
    assert _events(client, route_db_session, application['id']) == [
        EventType.APPLICATION_SUBMITTED,
        EventType.APPLICATION_WITHDRAWN,
    ]
    assert (
        _histories(client, route_db_session, application['id'])[-1].updated['status'] == 'withdrawn'
    )


def test_a_draft_is_never_withdrawn(client, auth_header, pa):
    email, _ = pa
    application = _start(client, auth_header, email)

    response = client.post(f'{_ME}/{application["id"]}/withdraw', headers=auth_header(email))

    assert (response.status_code, response.json()['code']) == (409, 'INVALID_TRANSITION')


def test_the_license_expiry_is_a_date(client, auth_header, pa):
    email, _ = pa
    application = _start(client, auth_header, email)

    response = client.patch(
        f'{_ME}/{application["id"]}',
        json={'claimed_license_expires_on': 'soon'},
        headers=auth_header(email),
    )

    assert response.status_code == 422
