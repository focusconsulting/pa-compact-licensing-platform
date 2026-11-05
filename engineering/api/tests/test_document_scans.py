"""Recording malware scans: the tests write the tag GuardDuty would, on objects in RustFS."""

import asyncio
import logging
import uuid
from datetime import timedelta

import pytest
from botocore.stub import Stubber
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.documents import matches_type
from licensing_api.repo.base import utc_now
from licensing_api.repo.document import Document, ScanStatus, storage_key_for
from licensing_api.repo.domain_event import DomainEvent, EventType
from licensing_api.repo.history import DocumentHistory
from licensing_api.scans import SCAN_TIMEOUT, check_document_scans
from licensing_api.storage import SCAN_TAG, CurrentVersion, Storage, create_storage
from tests.conftest import TEST_SETTINGS
from tests.factories import system_user_id

_PDF = b'%PDF-1.7 certificate'
_BUCKET = TEST_SETTINGS.s3_documents_bucket


async def _document(
    session: AsyncSession,
    storage: Storage,
    *,
    body: bytes = _PDF,
    content_type: str = 'application/pdf',
    tag: str | None = None,
    uploaded: bool = True,
    age: timedelta = timedelta(0),
) -> tuple[Document, str | None]:
    """A pending document, its object in RustFS (unless not ``uploaded``), and that object's version."""
    public_id = uuid.uuid4()
    key = storage_key_for(public_id)
    version = None
    if uploaded:
        version = storage._client.put_object(
            Bucket=_BUCKET, Key=key, Body=body, ContentType=content_type
        )['VersionId']
        if tag:
            storage._client.put_object_tagging(
                Bucket=_BUCKET, Key=key, Tagging={'TagSet': [{'Key': SCAN_TAG, 'Value': tag}]}
            )
    document = Document(
        public_id=public_id,
        kind='proof',
        file_name='proof.pdf',
        content_type=content_type,
        size_bytes=len(body),
        storage_key=key,
        created_by=await system_user_id(session),
        created_at=utc_now() - age,
    )
    session.add(document)
    await session.flush()
    return document, version


@pytest.mark.parametrize(
    ('tag', 'body', 'status', 'reason'),
    [
        ('NO_THREATS_FOUND', _PDF, ScanStatus.CLEAN, None),
        ('NO_THREATS_FOUND', b'MZ not a pdf', ScanStatus.ERROR, 'type_mismatch'),
        ('THREATS_FOUND', _PDF, ScanStatus.INFECTED, 'threats_found'),
        ('UNSUPPORTED', _PDF, ScanStatus.ERROR, 'unsupported'),
        ('ACCESS_DENIED', _PDF, ScanStatus.ERROR, 'access_denied'),
        ('FAILED', _PDF, ScanStatus.ERROR, 'failed'),
    ],
)
async def test_each_scan_result_is_recorded(
    db_session, rolled_back_sessions, storage, caplog, tag, body, status, reason
):
    document, version = await _document(db_session, storage, body=body, tag=tag)

    with caplog.at_level(logging.INFO, logger='licensing_api.scans'):
        recorded = await check_document_scans(rolled_back_sessions, storage, batch_size=1)
    await db_session.refresh(document)

    assert recorded == 1
    assert (document.scan_status, document.scanned_version_id) == (status, version)
    assert document.scanned_at is not None
    record = caplog.records[-1]
    assert (record.getMessage(), record.__dict__['outcome'], record.__dict__['reason']) == (
        'Document scanned',
        status,
        reason,
    )


async def test_a_result_writes_history_and_an_event(db_session, rolled_back_sessions, storage):
    document, _ = await _document(db_session, storage, tag='THREATS_FOUND')

    await check_document_scans(rolled_back_sessions, storage, batch_size=1)
    histories = (
        await db_session.scalars(
            select(DocumentHistory).where(col(DocumentHistory.entity_id) == document.id)
        )
    ).all()
    events = (
        await db_session.scalars(
            select(DomainEvent).where(
                col(DomainEvent.aggregate_type) == 'documents',
                col(DomainEvent.aggregate_id) == document.id,
            )
        )
    ).all()

    assert histories[-1].updated is not None
    assert histories[-1].updated['scan_status'] == 'infected'
    assert [(event.type, event.payload) for event in events] == [
        (EventType.DOCUMENT_SCANNED, {'scan_status': 'infected'})
    ]


async def test_only_the_scanned_version_counts(db_session, rolled_back_sessions, storage):
    document, _ = await _document(db_session, storage, tag='NO_THREATS_FOUND')
    # The upload link is used again before the Worker looks: the new version has no result yet.
    replaced = storage._client.put_object(
        Bucket=_BUCKET, Key=document.storage_key, Body=_PDF, ContentType='application/pdf'
    )['VersionId']

    await check_document_scans(rolled_back_sessions, storage, batch_size=1)
    await db_session.refresh(document)
    pending = document.scan_status
    storage._client.put_object_tagging(
        Bucket=_BUCKET,
        Key=document.storage_key,
        Tagging={'TagSet': [{'Key': SCAN_TAG, 'Value': 'NO_THREATS_FOUND'}]},
    )
    document.scan_checked_at = None
    await db_session.flush()
    await check_document_scans(rolled_back_sessions, storage, batch_size=1)
    await db_session.refresh(document)

    assert pending == ScanStatus.PENDING
    assert (document.scan_status, document.scanned_version_id) == (ScanStatus.CLEAN, replaced)


async def test_a_document_waits_for_its_scan_and_is_not_rechecked_at_once(
    db_session, rolled_back_sessions, storage, caplog
):
    document, _ = await _document(db_session, storage)

    with caplog.at_level(logging.INFO, logger='licensing_api.storage'):
        first = await check_document_scans(rolled_back_sessions, storage, batch_size=1)
        calls = len(caplog.records)
        await db_session.refresh(document)
        checked_at = document.scan_checked_at
        second = await check_document_scans(rolled_back_sessions, storage, batch_size=1)

    await db_session.refresh(document)
    assert (first, second) == (0, 0)
    assert (document.scan_status, document.scanned_at) == (ScanStatus.PENDING, None)
    assert checked_at is not None
    # The second pass found nothing due, so it never called storage.
    assert len(caplog.records) == calls


@pytest.mark.parametrize(('uploaded', 'reason'), [(True, 'timed_out'), (False, 'never_uploaded')])
async def test_no_result_within_the_timeout_is_an_error(
    db_session, rolled_back_sessions, storage, caplog, uploaded, reason
):
    document, _ = await _document(
        db_session, storage, uploaded=uploaded, age=SCAN_TIMEOUT + timedelta(seconds=1)
    )

    with caplog.at_level(logging.INFO, logger='licensing_api.scans'):
        await check_document_scans(rolled_back_sessions, storage, batch_size=1)
    await db_session.refresh(document)

    assert document.scan_status == ScanStatus.ERROR
    assert caplog.records[-1].__dict__['reason'] == reason


async def test_a_link_never_used_waits_until_the_timeout(db_session, rolled_back_sessions, storage):
    document, _ = await _document(db_session, storage, uploaded=False)

    await check_document_scans(rolled_back_sessions, storage, batch_size=1)
    await db_session.refresh(document)

    assert document.scan_status == ScanStatus.PENDING


@pytest.mark.parametrize(
    ('version_id', 'start', 'reason'),
    [(None, b'a,b\n', 'unversioned'), ('v1', b'', 'missing')],
    ids=['no version', 'version gone'],
)
async def test_a_clean_tag_is_not_enough_without_the_bytes_of_one_version(
    db_session, rolled_back_sessions, storage, caplog, monkeypatch, version_id, start, reason
):
    document, _ = await _document(db_session, storage, body=b'a,b\n', content_type='text/csv')
    tagged = create_storage(TEST_SETTINGS)

    async def current_version(key: str) -> CurrentVersion:
        return CurrentVersion(version_id=version_id, scan_status='NO_THREATS_FOUND')

    async def read_start(key: str, size: int, *, version_id: str | None = None) -> bytes:
        return start

    monkeypatch.setattr(tagged, 'current_version', current_version)
    monkeypatch.setattr(tagged, 'read_start', read_start)

    with caplog.at_level(logging.INFO, logger='licensing_api.scans'):
        await check_document_scans(rolled_back_sessions, tagged, batch_size=1)
    await db_session.refresh(document)

    assert document.scan_status == ScanStatus.ERROR
    assert caplog.records[-1].__dict__['reason'] == reason


async def test_a_storage_error_leaves_the_document_pending(
    db_session, rolled_back_sessions, storage, caplog
):
    document, _ = await _document(db_session, storage)
    failing = create_storage(TEST_SETTINGS)

    with (
        Stubber(failing._client) as stubber,
        caplog.at_level(logging.WARNING, logger='licensing_api.scans'),
    ):
        stubber.add_client_error('get_object_tagging', service_error_code='SlowDown')
        recorded = await check_document_scans(rolled_back_sessions, failing, batch_size=1)
    await db_session.refresh(document)

    assert recorded == 0
    assert document.scan_status == ScanStatus.PENDING
    assert document.scan_checked_at is not None
    assert (caplog.records[-1].getMessage(), caplog.records[-1].__dict__['outcome']) == (
        'Document scan check failed',
        'failed',
    )


async def test_two_workers_record_each_result_once(committed_sessions, storage):
    """Commits for real, so the row locks between Workers are real. The documents end ``clean``,
    and their history, which is append-only, stays in the database."""
    async with committed_sessions() as session, session.begin():
        documents = [
            (await _document(session, storage, tag='NO_THREATS_FOUND'))[0] for _ in range(4)
        ]

    results = await asyncio.gather(
        check_document_scans(committed_sessions, storage),
        check_document_scans(committed_sessions, storage),
    )

    async with committed_sessions() as session:
        statuses = (
            await session.scalars(
                select(col(Document.scan_status)).where(
                    col(Document.id).in_([document.id for document in documents])
                )
            )
        ).all()
    assert sum(results) >= 4
    assert set(statuses) == {ScanStatus.CLEAN}
    async with committed_sessions() as session:
        histories = (
            await session.scalars(
                select(DocumentHistory).where(
                    col(DocumentHistory.entity_id).in_([document.id for document in documents])
                )
            )
        ).all()
    assert len(histories) == 4


@pytest.mark.parametrize(
    ('content_type', 'start', 'matches'),
    [
        ('image/png', b'\x89PNG\r\n\x1a\n...', True),
        ('image/jpeg', b'\xff\xd8\xff\xe0', True),
        ('image/jpeg', b'GIF89a', False),
        (
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            b'PK\x03\x04',
            True,
        ),
        ('text/csv', 'name,état\n'.encode(), True),
        ('text/csv', 'é'.encode()[:1], True),
        ('text/csv', b'a,b\n\x00', False),
        ('text/csv', b'\xff\xfe', False),
    ],
    ids=['png', 'jpeg', 'gif as jpeg', 'docx', 'csv', 'csv cut mid-character', 'nul', 'not utf-8'],
)
def test_a_file_must_start_like_its_type(content_type, start, matches):
    assert matches_type(content_type, start) is matches
