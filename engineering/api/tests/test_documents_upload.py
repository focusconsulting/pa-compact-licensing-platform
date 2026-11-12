"""Uploading a document: the API's limits, the link it returns, and what it records."""

import uuid

import httpx
import pytest
from sqlmodel import col, select

from licensing_api.context import ChangeContext
from licensing_api.documents import MAX_BYTES
from licensing_api.repo.document import Document, DocumentOwnerType, ScanStatus
from licensing_api.repo.document_owner import attach
from licensing_api.repo.domain_event import DomainEvent, EventType
from licensing_api.repo.history import DocumentHistory
from tests.factories import make_practitioner, make_user

_ME = '/api/me/documents'


def _body(**overrides) -> dict:
    return {
        'file_name': 'certificate.pdf',
        'content_type': 'application/pdf',
        'size_bytes': 1000,
        'kind': 'nccpa_certificate',
        **overrides,
    }


def _licensee(client, session) -> str:
    return client.portal.call(lambda: make_user(session, role='licensee')).email


def _post_file(upload: dict, body: bytes, content_type: str) -> httpx.Response:
    return httpx.post(
        upload['url'], data=upload['fields'], files={'file': ('f', body, content_type)}
    )


def test_a_pa_uploads_20_mib_straight_to_storage(client, auth_header, route_db_session):
    email = _licensee(client, route_db_session)

    response = client.post(_ME, json=_body(size_bytes=MAX_BYTES), headers=auth_header(email))

    assert response.status_code == 201
    data = response.json()['data']
    assert data['document'] | {'id': None, 'created_at': None} == {
        'id': None,
        'file_name': 'certificate.pdf',
        'content_type': 'application/pdf',
        'size_bytes': MAX_BYTES,
        'kind': 'nccpa_certificate',
        'scan_status': 'pending',
        'created_at': None,
    }
    assert data['upload']['fields']['key'] == f'documents/{data["document"]["id"]}'
    stored = _post_file(data['upload'], b'%PDF-' + b'0' * (MAX_BYTES - 5), 'application/pdf')
    assert stored.status_code == 204


def test_the_upload_records_the_document_its_history_and_an_event(
    client, auth_header, route_db_session
):
    email = _licensee(client, route_db_session)

    document_id = client.post(_ME, json=_body(), headers=auth_header(email)).json()['data'][
        'document'
    ]['id']

    async def _recorded():
        document = (
            await route_db_session.scalars(
                select(Document).where(col(Document.public_id) == uuid.UUID(document_id))
            )
        ).one()
        histories = (
            await route_db_session.scalars(
                select(DocumentHistory).where(col(DocumentHistory.entity_id) == document.id)
            )
        ).all()
        events = (
            await route_db_session.scalars(
                select(DomainEvent).where(
                    col(DomainEvent.aggregate_type) == 'documents',
                    col(DomainEvent.aggregate_id) == document.id,
                )
            )
        ).all()
        return document, histories, events

    document, histories, events = client.portal.call(_recorded)
    assert document.storage_key == f'documents/{document_id}'
    assert (document.scan_status, document.owner_type) == (ScanStatus.PENDING, None)
    assert len(histories) == 1
    assert [event.type for event in events] == [EventType.DOCUMENT_UPLOADED]


def test_21_mb_is_refused(client, auth_header, route_db_session):
    email = _licensee(client, route_db_session)

    response = client.post(_ME, json=_body(size_bytes=21_000_000), headers=auth_header(email))

    assert response.status_code == 422
    assert response.json()['details'][0].startswith('body.size_bytes')


@pytest.mark.parametrize(
    ('file_name', 'content_type'),
    [
        ('scan.PNG', 'image/png'),
        ('photo.jpeg', 'image/jpeg'),
        ('photo.jpg', 'image/jpeg'),
        ('roster.csv', 'text/csv'),
        (
            'order.docx',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        ),
    ],
)
def test_each_allowed_type_is_accepted(
    client, auth_header, route_db_session, file_name, content_type
):
    email = _licensee(client, route_db_session)

    response = client.post(
        _ME, json=_body(file_name=file_name, content_type=content_type), headers=auth_header(email)
    )

    assert response.status_code == 201


@pytest.mark.parametrize(
    'overrides',
    [
        {'content_type': 'text/html', 'file_name': 'page.html'},
        {'file_name': 'certificate.exe'},
        {'file_name': '../certificate.pdf'},
        {'size_bytes': 0},
        {'kind': 'Not A Slug'},
        {'owner_id': 1},
    ],
    ids=['type', 'extension', 'path', 'empty', 'kind', 'unknown field'],
)
def test_a_bad_request_is_refused(client, auth_header, route_db_session, overrides):
    email = _licensee(client, route_db_session)

    response = client.post(_ME, json=_body(**overrides), headers=auth_header(email))

    assert response.status_code == 422
    assert response.json()['code'] == 'VALIDATION_ERROR'


def test_state_staff_upload_where_they_may_write(client, auth_header, route_db_session):
    staff = client.portal.call(
        lambda: make_user(
            route_db_session, role='state_staff', state_code='KS', permissions={'KS': ['write']}
        )
    )

    allowed = client.post(
        '/api/states/KS/documents', json=_body(), headers=auth_header(staff.email)
    )
    elsewhere = client.post(
        '/api/states/OK/documents', json=_body(), headers=auth_header(staff.email)
    )

    assert allowed.status_code == 201
    assert elsewhere.status_code == 403


def test_only_the_uploader_sees_an_unattached_document(client, auth_header, route_db_session):
    uploader = _licensee(client, route_db_session)
    other = _licensee(client, route_db_session)
    document_id = client.post(_ME, json=_body(), headers=auth_header(uploader)).json()['data'][
        'document'
    ]['id']

    mine = client.get(f'{_ME}/{document_id}', headers=auth_header(uploader))
    theirs = client.get(f'{_ME}/{document_id}', headers=auth_header(other))
    missing = client.get(f'{_ME}/{uuid.uuid4()}', headers=auth_header(uploader))

    assert mine.status_code == 200
    assert mine.json()['data']['scan_status'] == 'pending'
    assert (theirs.status_code, theirs.json()['code']) == (404, 'NOT_FOUND')
    assert missing.status_code == 404


def test_state_staff_see_their_own_upload(client, auth_header, route_db_session):
    staff = client.portal.call(
        lambda: make_user(
            route_db_session,
            role='state_staff',
            state_code='KS',
            permissions={'KS': ['read_private', 'write']},
        )
    )
    headers = auth_header(staff.email)
    document_id = client.post('/api/states/KS/documents', json=_body(), headers=headers).json()[
        'data'
    ]['document']['id']

    response = client.get(f'/api/states/KS/documents/{document_id}', headers=headers)

    assert response.json()['data']['id'] == document_id


async def test_attach_gives_a_document_to_its_owner_once(db_session):
    practitioner = await make_practitioner(db_session)
    ctx = ChangeContext(user_id=practitioner.user_id, request_id=None)
    document = Document(
        kind='nccpa_certificate',
        file_name='c.pdf',
        content_type='application/pdf',
        size_bytes=1,
        storage_key=f'documents/{uuid.uuid4()}',
        created_by=practitioner.user_id,
    )
    db_session.add(document)
    await db_session.flush()

    await attach(
        db_session,
        ctx,
        document,
        owner_type=DocumentOwnerType.PRACTITIONER,
        owner_id=practitioner.id,
    )
    histories = (
        await db_session.scalars(
            select(DocumentHistory).where(col(DocumentHistory.entity_id) == document.id)
        )
    ).all()

    assert (document.owner_type, document.owner_id) == ('practitioner', practitioner.id)
    assert histories[-1].updated == {'owner_type': 'practitioner', 'owner_id': practitioner.id}
    with pytest.raises(ValueError, match='already attached'):
        await attach(
            db_session, ctx, document, owner_type=DocumentOwnerType.PRACTITIONER, owner_id=1
        )
