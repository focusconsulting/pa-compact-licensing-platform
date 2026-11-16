"""The documents bucket over the S3 API: RustFS locally, S3 in AWS (ADR-0017).

Browsers move the bytes through presigned links; the API only signs, reads the scan tag, and
reads the start of a file to check its type. ``boto3`` blocks, so I/O runs in a thread.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING
from urllib.parse import quote

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from licensing_api.config import Settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

logger = logging.getLogger(__name__)

# The object tag GuardDuty Malware Protection writes, and the local scanner imitates.
SCAN_TAG = 'GuardDutyMalwareScanStatus'

# S3 answers a missing key with NoSuchKey; a HEAD-style miss, or one without s3:ListBucket, with 404.
_MISSING = frozenset({'NoSuchKey', '404'})


@dataclass(frozen=True)
class CurrentVersion:
    """An object's current version and its scan tag, ``None`` until the scan writes one.

    An upload link can be used again until it expires, and each use makes a new version, so a
    scan result belongs to one version, not to the key.
    """

    version_id: str | None
    scan_status: str | None


@dataclass(frozen=True)
class PresignedUpload:
    """Where a browser POSTs one file, and the form fields it sends before the file."""

    url: str
    fields: dict[str, str]


class Storage:
    """One bucket. The ``boto3`` client is thread-safe, so one instance serves a process."""

    def __init__(self, client: S3Client, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    def presign_upload(
        self, key: str, *, content_type: str, size_bytes: int, expires: timedelta
    ) -> PresignedUpload:
        """A POST form the bucket accepts only for exactly ``size_bytes`` of ``content_type`` at ``key``."""
        post = self._client.generate_presigned_post(
            self._bucket,
            key,
            Fields={'Content-Type': content_type},
            Conditions=[
                {'Content-Type': content_type},
                ['content-length-range', size_bytes, size_bytes],
            ],
            ExpiresIn=int(expires.total_seconds()),
        )
        return PresignedUpload(url=post['url'], fields=post['fields'])

    def presign_download(
        self, key: str, *, file_name: str, content_type: str, version_id: str, expires: timedelta
    ) -> str:
        """A GET link to one version that makes the browser save the file rather than open it."""
        return self._client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self._bucket,
                'Key': key,
                'VersionId': version_id,
                'ResponseContentDisposition': _attachment(file_name),
                'ResponseContentType': content_type,
            },
            ExpiresIn=int(expires.total_seconds()),
        )

    async def current_version(self, key: str) -> CurrentVersion | None:
        """The object's current version and scan tag, or ``None`` for a missing object."""

        def read() -> CurrentVersion:
            response = self._client.get_object_tagging(Bucket=self._bucket, Key=key)
            status = next(
                (tag['Value'] for tag in response['TagSet'] if tag['Key'] == SCAN_TAG), None
            )
            return CurrentVersion(version_id=response.get('VersionId'), scan_status=status)

        return await self._call('get_object_tagging', key, read, missing=None)

    async def read_start(self, key: str, size: int, *, version_id: str | None = None) -> bytes:
        """The first ``size`` bytes of a version (the current one by default), or ``b''`` if missing."""

        def read() -> bytes:
            byte_range = f'bytes=0-{size - 1}'
            if version_id:
                response = self._client.get_object(
                    Bucket=self._bucket, Key=key, Range=byte_range, VersionId=version_id
                )
            else:
                response = self._client.get_object(Bucket=self._bucket, Key=key, Range=byte_range)
            return response['Body'].read()

        return await self._call('get_object', key, read, missing=b'')

    async def _call[T](self, operation: str, key: str, call: Callable[[], T], *, missing: T) -> T:
        log: dict[str, object] = {'operation': operation, 'storage_key': key}
        started = time.monotonic()
        try:
            result = await asyncio.to_thread(call)
        except ClientError as error:
            code = error.response.get('Error', {}).get('Code', '')
            log['duration_ms'] = round((time.monotonic() - started) * 1000)
            if code in _MISSING:
                logger.info('Storage call', extra={**log, 'outcome': 'missing'})
                return missing
            logger.warning(
                'Storage call failed', extra={**log, 'outcome': 'failed', 'error_code': code}
            )
            raise
        log['duration_ms'] = round((time.monotonic() - started) * 1000)
        logger.info('Storage call', extra={**log, 'outcome': 'ok'})
        return result


def _attachment(file_name: str) -> str:
    # RFC 6266: an ASCII fallback for old clients, then the exact name, UTF-8 and percent-encoded.
    fallback = ''.join(
        c if c.isascii() and c.isprintable() and c not in '"\\' else '_' for c in file_name
    )
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(file_name, safe="")}'


def create_storage(settings: Settings) -> Storage:
    """The documents bucket for these settings; path-style addressing when the endpoint is RustFS.

    Credentials come from boto3's own chain, never from settings: the task role in AWS, the
    standard ``AWS_*`` variables locally.
    """
    client = boto3.client(
        's3',
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path' if settings.s3_endpoint_url else 'virtual'},
            connect_timeout=5,
            read_timeout=10,
            retries={'mode': 'standard', 'max_attempts': 3},
        ),
    )
    return Storage(client, settings.s3_documents_bucket)
