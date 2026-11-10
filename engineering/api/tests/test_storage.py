"""The documents bucket, against RustFS: what a presigned link lets a browser do, and what it refuses."""

import logging
import uuid
from datetime import timedelta

import httpx
import pytest
from botocore.exceptions import ClientError
from botocore.stub import Stubber

from licensing_api.config import Settings
from licensing_api.storage import SCAN_TAG, Storage, create_storage
from tests.conftest import TEST_SETTINGS

_MINUTE = timedelta(minutes=1)


def _key() -> str:
    return f'tests/{uuid.uuid4()}'


def _post(
    storage: Storage,
    key: str,
    body: bytes,
    *,
    declared: int,
    content_type: str,
    sent_type: str | None = None,
) -> httpx.Response:
    upload = storage.presign_upload(
        key, content_type=content_type, size_bytes=declared, expires=_MINUTE
    )
    fields = {**upload.fields, 'Content-Type': sent_type or content_type}
    return httpx.post(
        upload.url, data=fields, files={'file': ('f', body, sent_type or content_type)}
    )


def test_the_bucket_accepts_exactly_the_declared_size_and_type(storage):
    response = _post(storage, _key(), b'%PDF-1.7 x', declared=10, content_type='application/pdf')

    assert response.status_code == 204


@pytest.mark.parametrize('size', [9, 11], ids=['smaller', 'larger'])
def test_the_bucket_refuses_any_other_size(storage, size):
    response = _post(storage, _key(), b'x' * size, declared=10, content_type='application/pdf')

    assert response.status_code == 400
    assert 'Entity' in response.text


async def test_the_bucket_refuses_another_content_type(storage):
    key = _key()
    response = _post(
        storage, key, b'x' * 10, declared=10, content_type='application/pdf', sent_type='text/html'
    )

    # S3 answers 403 and RustFS 400; either way nothing is stored.
    assert response.status_code in (400, 403)
    assert await storage.read_start(key, 1) == b''


def test_a_download_link_saves_the_file_under_its_name(storage):
    key = _key()
    _post(storage, key, b'%PDF-1.7 x', declared=10, content_type='application/pdf')

    url = storage.presign_download(
        key, file_name='Ordre "final" é.pdf', content_type='application/pdf', expires=_MINUTE
    )
    response = httpx.get(url)

    assert response.content == b'%PDF-1.7 x'
    assert response.headers['content-type'] == 'application/pdf'
    assert response.headers['content-disposition'] == (
        'attachment; filename="Ordre _final_ _.pdf"; '
        "filename*=UTF-8''Ordre%20%22final%22%20%C3%A9.pdf"
    )


async def test_the_scan_tag_is_read_once_written(storage, caplog):
    key = _key()
    _post(storage, key, b'%PDF-1.7 x', declared=10, content_type='application/pdf')

    with caplog.at_level(logging.INFO, logger='licensing_api.storage'):
        before = await storage.scan_tag(key)
    storage._client.put_object_tagging(
        Bucket='documents',
        Key=key,
        Tagging={
            'TagSet': [
                {'Key': 'other', 'Value': 'x'},
                {'Key': SCAN_TAG, 'Value': 'NO_THREATS_FOUND'},
            ]
        },
    )

    assert before is None
    assert await storage.scan_tag(key) == 'NO_THREATS_FOUND'
    record = caplog.records[-1]
    assert (record.message, record.__dict__['outcome'], record.__dict__['operation']) == (
        'Storage call',
        'ok',
        'get_object_tagging',
    )
    assert record.__dict__['duration_ms'] >= 0


async def test_the_start_of_a_file_is_read(storage):
    key = _key()
    _post(storage, key, b'%PDF-1.7 x', declared=10, content_type='application/pdf')

    assert await storage.read_start(key, 5) == b'%PDF-'


async def test_a_missing_object_has_no_tag_and_no_bytes(storage, caplog):
    with caplog.at_level(logging.INFO, logger='licensing_api.storage'):
        assert await storage.scan_tag(_key()) is None
        assert await storage.read_start(_key(), 5) == b''

    assert [record.__dict__['outcome'] for record in caplog.records] == ['missing', 'missing']


async def test_any_other_error_is_logged_and_raised(caplog):
    storage = create_storage(TEST_SETTINGS)

    with (
        Stubber(storage._client) as stubber,
        caplog.at_level(logging.WARNING, logger='licensing_api.storage'),
        pytest.raises(ClientError),
    ):
        stubber.add_client_error('get_object_tagging', service_error_code='AccessDenied')
        await storage.scan_tag('anything')

    record = caplog.records[-1]
    assert (record.__dict__['outcome'], record.__dict__['error_code']) == ('failed', 'AccessDenied')


@pytest.mark.parametrize(
    ('endpoint', 'style'), [('http://localhost:9300', 'path'), (None, 'virtual')]
)
def test_rustfs_is_addressed_by_path_and_s3_by_host(endpoint, style):
    storage = create_storage(Settings(s3_endpoint_url=endpoint))

    assert storage._client.meta.config.s3 == {'addressing_style': style}
