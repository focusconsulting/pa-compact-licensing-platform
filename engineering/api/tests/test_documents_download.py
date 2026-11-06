"""Who may see and download a document, and what a download records (Rule 4 §4.5)."""

import uuid
from dataclasses import dataclass
from datetime import date

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.repo.audit_log import AuditLogEntry
from licensing_api.repo.document import Document, DocumentOwnerType, ScanStatus, storage_key_for
from licensing_api.repo.participation_application import ParticipationApplication
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.privilege_request import PrivilegeRequest
from licensing_api.repo.sii_report import SiiReport
from licensing_api.repo.user import User
from licensing_api.storage import Storage
from tests.conftest import TEST_SETTINGS
from tests.factories import (
    make_adverse_action,
    make_issued_privilege,
    make_practitioner,
    make_user,
    system_user_id,
)

_BUCKET = TEST_SETTINGS.s3_documents_bucket

# Who sees each document, by the callers _world creates. The PA's SQL is KS and they hold a
# privilege in OK; OK reported the adverse action and CO the SII report. MO holds nothing.
_EXPECTED = {
    'practitioner': {'pa', 'KS', 'OK', 'commission'},
    'application': {'pa', 'KS', 'commission'},
    'privilege_request': {'pa', 'OK', 'commission'},
    'adverse_action': {'KS', 'OK', 'commission'},
    'sii_report': {'KS', 'OK', 'CO', 'commission'},
    'state': {'KS', 'commission'},
    'unattached_by_staff': {'KS', 'commission'},
    'unattached_by_pa': {'pa', 'commission'},
}
_STATES = ('KS', 'OK', 'CO', 'MO')


@dataclass
class World:
    emails: dict[str, str]
    documents: dict[str, Document]


async def _document(
    session: AsyncSession,
    created_by: int,
    *,
    owner_type: DocumentOwnerType | None = None,
    owner_id: int | None = None,
    owner_key: str | None = None,
    uploaded_in_state: str | None = None,
    scan_status: ScanStatus = ScanStatus.CLEAN,
    version_id: str | None = 'v1',
) -> Document:
    public_id = uuid.uuid4()
    document = Document(
        public_id=public_id,
        owner_type=owner_type,
        owner_id=owner_id,
        owner_key=owner_key,
        uploaded_in_state=uploaded_in_state,
        kind='proof',
        file_name='order.pdf',
        content_type='application/pdf',
        size_bytes=1,
        storage_key=storage_key_for(public_id),
        scan_status=scan_status,
        scanned_version_id=version_id,
        created_by=created_by,
    )
    session.add(document)
    await session.flush()
    return document


async def _staff(session: AsyncSession, state_code: str) -> User:
    return await make_user(
        session,
        role='state_staff',
        state_code=state_code,
        permissions={state_code: ['read_private', 'write']},
    )


async def _world(session: AsyncSession) -> World:
    system = await system_user_id(session)
    privilege = await make_issued_privilege(session)
    practitioner = await session.get(Practitioner, privilege.practitioner_id)
    request = await session.get(PrivilegeRequest, privilege.privilege_request_id)
    assert practitioner is not None and request is not None
    application = await session.get(ParticipationApplication, request.participation_application_id)
    pa = await session.get(User, practitioner.user_id)
    assert application is not None and pa is not None
    action = await make_adverse_action(session, privilege)
    sii = SiiReport(
        practitioner_id=practitioner.id,  # type: ignore[arg-type]  # a loaded row has an id
        reporting_state_code='CO',
        description='Investigation opened.',
        contact_name='CO Board',
        contact_email='board@co.example.gov',
        determined_on=date(2026, 7, 1),
        created_by=system,
    )
    session.add(sii)
    await session.flush()
    staff = {code: await _staff(session, code) for code in _STATES}
    commission = await make_user(session, role='compact_admin')
    other_pa = await session.get(User, (await make_practitioner(session)).user_id)
    assert other_pa is not None

    owner = DocumentOwnerType
    documents = {
        'practitioner': await _document(
            session, system, owner_type=owner.PRACTITIONER, owner_id=practitioner.id
        ),
        'application': await _document(
            session, system, owner_type=owner.PARTICIPATION_APPLICATION, owner_id=application.id
        ),
        'privilege_request': await _document(
            session, system, owner_type=owner.PRIVILEGE_REQUEST, owner_id=request.id
        ),
        'adverse_action': await _document(
            session, system, owner_type=owner.ADVERSE_ACTION, owner_id=action.id
        ),
        'sii_report': await _document(
            session, system, owner_type=owner.SII_REPORT, owner_id=sii.id
        ),
        'state': await _document(session, system, owner_type=owner.STATE, owner_key='KS'),
        'unattached_by_staff': await _document(
            session,
            staff['KS'].id,  # type: ignore[arg-type]  # flushed rows have ids
            uploaded_in_state='KS',
        ),
        'unattached_by_pa': await _document(session, pa.id),  # type: ignore[arg-type]  # flushed rows have ids
    }
    emails = {
        'pa': pa.email,
        'other_pa': other_pa.email,
        'commission': commission.email,
        **{code: user.email for code, user in staff.items()},
    }
    return World(emails=emails, documents=documents)


def _details_url(caller: str, document: Document) -> str:
    if caller in ('pa', 'other_pa'):
        return f'/api/me/documents/{document.public_id}'
    if caller == 'commission':
        return f'/api/commission/documents/{document.public_id}'
    return f'/api/states/{caller.lower()}/documents/{document.public_id}'


def test_each_caller_sees_exactly_the_documents_in_their_scope(
    client, auth_header, route_db_session
):
    world = client.portal.call(_world, route_db_session)

    seen = {
        name: {
            caller
            for caller, email in world.emails.items()
            if client.get(_details_url(caller, document), headers=auth_header(email)).status_code
            == 200
        }
        for name, document in world.documents.items()
    }

    assert seen == _EXPECTED


def test_out_of_scope_is_not_found(client, auth_header, route_db_session):
    world = client.portal.call(_world, route_db_session)
    application = world.documents['application']

    response = client.get(
        f'/api/states/MO/documents/{application.public_id}/download',
        headers=auth_header(world.emails['MO']),
    )

    assert (response.status_code, response.json()['code']) == (404, 'NOT_FOUND')


def test_state_staff_need_read_private(client, auth_header, route_db_session):
    staff = client.portal.call(
        lambda: make_user(
            route_db_session, role='state_staff', state_code='KS', permissions={'KS': ['write']}
        )
    )

    response = client.get(
        f'/api/states/KS/documents/{uuid.uuid4()}', headers=auth_header(staff.email)
    )

    assert response.status_code == 403


async def _stored(
    session: AsyncSession, storage: Storage, created_by: int, uploaded_in_state: str | None = None
) -> Document:
    """A clean, scanned document whose upload link was used again after the scan."""
    document = await _document(
        session, created_by, uploaded_in_state=uploaded_in_state, version_id=None
    )
    scanned = storage._client.put_object(
        Bucket=_BUCKET, Key=document.storage_key, Body=b'%PDF-1.7 scanned'
    )['VersionId']
    storage._client.put_object(Bucket=_BUCKET, Key=document.storage_key, Body=b'%PDF-1.7 later')
    document.scanned_version_id = scanned
    await session.flush()
    return document


def _audit_rows(client, session: AsyncSession, document: Document) -> list[AuditLogEntry]:
    async def read() -> list[AuditLogEntry]:
        statement = select(AuditLogEntry).where(
            col(AuditLogEntry.entity_type) == 'documents',
            col(AuditLogEntry.entity_id) == document.id,
        )
        return list((await session.scalars(statement)).all())

    return client.portal.call(read)


def test_a_pa_downloads_the_scanned_version_unaudited(
    client, auth_header, route_db_session, storage
):
    pa = client.portal.call(lambda: make_user(route_db_session, role='licensee'))
    document = client.portal.call(_stored, route_db_session, storage, pa.id)

    response = client.get(
        f'/api/me/documents/{document.public_id}/download', headers=auth_header(pa.email)
    )

    assert response.status_code == 200
    assert httpx.get(response.json()['data']['url']).content == b'%PDF-1.7 scanned'
    assert _audit_rows(client, route_db_session, document) == []


def test_every_staff_download_is_audited(client, auth_header, route_db_session, storage):
    staff = client.portal.call(_staff, route_db_session, 'KS')
    commission = client.portal.call(lambda: make_user(route_db_session, role='compact_admin'))
    document = client.portal.call(_stored, route_db_session, storage, staff.id, 'KS')

    for url, user in [
        (f'/api/states/KS/documents/{document.public_id}/download', staff),
        (f'/api/commission/documents/{document.public_id}/download', commission),
    ]:
        response = client.get(url, headers=auth_header(user.email))
        assert httpx.get(response.json()['data']['url']).content == b'%PDF-1.7 scanned'

    rows = _audit_rows(client, route_db_session, document)
    assert [(row.action, row.actor_user_id) for row in rows] == [
        ('document.downloaded', staff.id),
        ('document.downloaded', commission.id),
    ]


def test_only_a_clean_document_downloads(client, auth_header, route_db_session):
    pa = client.portal.call(lambda: make_user(route_db_session, role='licensee'))

    async def documents() -> list[Document]:
        return [
            await _document(route_db_session, pa.id, scan_status=status, version_id=version)  # type: ignore[arg-type]  # flushed rows have ids
            for status, version in [
                (ScanStatus.PENDING, None),
                (ScanStatus.INFECTED, 'v1'),
                (ScanStatus.ERROR, None),
                (ScanStatus.CLEAN, None),
            ]
        ]

    responses = [
        client.get(
            f'/api/me/documents/{document.public_id}/download', headers=auth_header(pa.email)
        )
        for document in client.portal.call(documents)
    ]

    assert {(r.status_code, r.json()['code']) for r in responses} == {(409, 'DOCUMENT_NOT_CLEAN')}


def test_an_unattached_upload_belongs_to_the_state_it_was_uploaded_for(
    client, auth_header, route_db_session
):
    # A KS staff member who also holds grants in OK, uploading for OK.
    uploader = client.portal.call(
        lambda: make_user(
            route_db_session,
            role='state_staff',
            state_code='KS',
            permissions={'KS': ['read_private'], 'OK': ['read_private', 'write']},
        )
    )
    ks = client.portal.call(_staff, route_db_session, 'KS')
    ok = client.portal.call(_staff, route_db_session, 'OK')
    document_id = client.post(
        '/api/states/OK/documents',
        json={
            'file_name': 'order.pdf',
            'content_type': 'application/pdf',
            'size_bytes': 10,
            'kind': 'order',
        },
        headers=auth_header(uploader.email),
    ).json()['data']['document']['id']

    seen_by_ok = client.get(
        f'/api/states/OK/documents/{document_id}', headers=auth_header(ok.email)
    )
    seen_by_ks = client.get(
        f'/api/states/KS/documents/{document_id}', headers=auth_header(ks.email)
    )

    assert (seen_by_ok.status_code, seen_by_ks.status_code) == (200, 404)
