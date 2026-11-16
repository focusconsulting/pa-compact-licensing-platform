"""What the application wizard reads before it writes: attestations, states, and the PA's unattached uploads."""

from uuid import uuid4

from sqlalchemy import update
from sqlmodel import col

from licensing_api.repo.document import Document, DocumentOwnerType
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.state import State
from licensing_api.repo.user import User
from tests.factories import make_practitioner


def _upload(client, session, practitioner: Practitioner, **overrides) -> str:
    async def _make() -> str:
        public_id = uuid4()
        session.add(
            Document(
                **{
                    'public_id': public_id,
                    'kind': 'nccpa_certificate',
                    'file_name': 'nccpa.pdf',
                    'content_type': 'application/pdf',
                    'size_bytes': 1000,
                    'storage_key': f'documents/{public_id}',
                    'created_by': practitioner.user_id,
                    **overrides,
                }
            )
        )
        await session.flush()
        return str(public_id)

    return client.portal.call(_make)


def test_anyone_reads_the_current_participation_attestations_in_order(client):
    response = client.get('/api/public/attestations', params={'applies_to': 'participation'})

    data = response.json()['data']
    assert [a['code'] for a in data] == [
        'service_of_process',
        'no_pending_investigation',
        'background_check',
        'truthfulness',
    ]
    assert data[1] == {
        'code': 'no_pending_investigation',
        'version': 1,
        'applies_to': 'participation',
        'text': 'I am not aware of any pending investigation of my license in my state of qualifying license.',
    }


def test_attestations_are_listed_only_for_a_known_purpose(client):
    response = client.get('/api/public/attestations', params={'applies_to': 'renewal'})

    assert response.status_code == 422


def test_anyone_reads_which_states_are_live(client, route_db_session):
    async def _go_live():
        await route_db_session.execute(
            update(State).where(col(State.code) == 'KS').values(is_member=True, is_live=True)
        )

    client.portal.call(_go_live)

    states = {s['code']: s for s in client.get('/api/public/states').json()['data']}

    assert states['KS'] == {'code': 'KS', 'name': 'Kansas', 'is_member': True, 'is_live': True}
    assert len(states) == 56


def test_a_pa_lists_only_their_own_unattached_uploads(client, auth_header, route_db_session):
    practitioner = client.portal.call(lambda: make_practitioner(route_db_session))
    email = client.portal.call(lambda: route_db_session.get(User, practitioner.user_id)).email
    mine = _upload(client, route_db_session, practitioner)
    _upload(
        client,
        route_db_session,
        practitioner,
        owner_type=DocumentOwnerType.PRACTITIONER,
        owner_id=practitioner.id,
    )
    _upload(client, route_db_session, practitioner, uploaded_in_state='KS')
    other = client.portal.call(lambda: make_practitioner(route_db_session))
    _upload(client, route_db_session, other)

    response = client.get('/api/me/documents/unattached', headers=auth_header(email))

    assert [d['id'] for d in response.json()['data']] == [mine]
