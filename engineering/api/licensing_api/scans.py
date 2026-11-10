"""Recording each document's malware scan, from the tag GuardDuty writes (backlog D9, F-12).

The Worker runs ``check_document_scans`` in a loop of its own. A document stays ``pending`` until
its current version carries a result; only ``clean`` documents can ever be downloaded.
"""

from __future__ import annotations

import logging
import time
from datetime import timedelta

from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import col, select

from licensing_api.context import system_context
from licensing_api.documents import matches_type
from licensing_api.repo import history
from licensing_api.repo.base import utc_now
from licensing_api.repo.document import Document, ScanStatus
from licensing_api.repo.domain_event import EventType, emit
from licensing_api.storage import CurrentVersion, Storage

logger = logging.getLogger(__name__)

# GuardDuty scans within minutes; a document with no result by then never gets one, such as
# an upload link that was never used.
SCAN_TIMEOUT = timedelta(minutes=15)
# A pending document is looked at again after this long, so a few uploads do not keep the
# Worker calling S3 on every loop.
RECHECK_INTERVAL = timedelta(seconds=5)
# Enough for every type's signature, and for a CSV's first lines.
_START_BYTES = 8192

# GuardDuty's other results (UNSUPPORTED, ACCESS_DENIED, FAILED) all mean the file was not
# shown to be safe.
_TAG_RESULTS = {'NO_THREATS_FOUND': ScanStatus.CLEAN, 'THREATS_FOUND': ScanStatus.INFECTED}


async def check_document_scans(
    session_factory: async_sessionmaker[AsyncSession], storage: Storage, *, batch_size: int = 20
) -> int:
    """Look for scan results on up to ``batch_size`` due documents; return how many were recorded."""
    recorded = 0
    for _ in range(batch_size):
        outcome = await _check_one(session_factory, storage)
        if outcome is None:
            break
        recorded += outcome
    return recorded


async def _check_one(
    session_factory: async_sessionmaker[AsyncSession], storage: Storage
) -> bool | None:
    """Check one due document in its own transaction. ``None`` when none is due."""
    async with session_factory() as session, session.begin():
        due = (
            select(Document)
            .where(
                col(Document.scan_status) == ScanStatus.PENDING,
                or_(
                    col(Document.scan_checked_at).is_(None),
                    col(Document.scan_checked_at) <= func.now() - RECHECK_INTERVAL,
                ),
            )
            .order_by(col(Document.scan_checked_at).nulls_first(), col(Document.id))
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        document = (await session.scalars(due)).one_or_none()
        if document is None:
            return None
        log = {'document_id': str(document.public_id)}
        started = time.monotonic()
        try:
            current = await storage.current_version(document.storage_key)
            status, reason = await _result(storage, document, current)
        except (ClientError, BotoCoreError) as error:
            # Storage already logged the call; the document is looked at again later.
            logger.warning(
                'Document scan check failed',
                extra={**log, 'outcome': 'failed', 'error_type': type(error).__name__},
            )
            document.scan_checked_at = utc_now()
            return False
        if status is None:
            document.scan_checked_at = utc_now()
            return False

        ctx = await system_context(session)
        before = history.snapshot(document)
        now = utc_now()
        document.scan_status = status
        document.scanned_at = now
        document.scan_checked_at = now
        document.scanned_version_id = current.version_id if current else None
        document.updated_by = ctx.user_id
        await history.write(session, ctx, document, before=before)
        await emit(session, ctx, EventType.DOCUMENT_SCANNED, document, {'scan_status': status})
        duration_ms = round((time.monotonic() - started) * 1000)
        logger.info(
            'Document scanned',
            extra={**log, 'outcome': status, 'reason': reason, 'duration_ms': duration_ms},
        )
        return True


async def _result(
    storage: Storage, document: Document, current: CurrentVersion | None
) -> tuple[ScanStatus | None, str | None]:
    """The scan result to record and why, or ``(None, None)`` to wait for one."""
    if current is None or current.scan_status is None:
        if utc_now() - document.created_at >= SCAN_TIMEOUT:
            return ScanStatus.ERROR, 'timed_out' if current else 'never_uploaded'
        return None, None
    status = _TAG_RESULTS.get(current.scan_status, ScanStatus.ERROR)
    if status is not ScanStatus.CLEAN:
        return status, current.scan_status.lower()
    # Fail closed: downloads serve only the recorded version, so clean needs one.
    if not current.version_id:
        return ScanStatus.ERROR, 'unversioned'
    start = await storage.read_start(
        document.storage_key, _START_BYTES, version_id=current.version_id
    )
    # Empty when the version vanished after its tag was read; an empty CSV would otherwise pass.
    if not start:
        return ScanStatus.ERROR, 'missing'
    if not matches_type(document.content_type, start):
        return ScanStatus.ERROR, 'type_mismatch'
    return ScanStatus.CLEAN, None
