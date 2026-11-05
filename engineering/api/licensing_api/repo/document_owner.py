"""Giving an uploaded document to the record that owns it.

Its own module because ``history`` imports ``document``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from licensing_api.repo import history
from licensing_api.repo.document import Document, DocumentOwnerType

if TYPE_CHECKING:
    # Annotations only: licensing_api.context imports the repo package, so a runtime import would be circular.
    from licensing_api.context import ChangeContext


async def attach(
    session: AsyncSession,
    ctx: ChangeContext,
    document: Document,
    *,
    owner_type: DocumentOwnerType,
    owner_id: int | None = None,
    owner_key: str | None = None,
) -> None:
    """Make ``document`` part of its owner's record, in the caller's transaction.

    Writes history; the caller's own event (``application.submitted``, say) covers the change.
    The caller checks the document is one its user may attach, such as one they uploaded. A
    document is attached once: the rules keep every document a state submits on the record
    it was submitted to (Rule 4 §4.3(e)(4)), so it never moves.
    """
    if document.is_attached:
        raise ValueError(f'Document {document.public_id} is already attached')
    before = history.snapshot(document)
    document.owner_type = owner_type
    document.owner_id = owner_id
    document.owner_key = owner_key
    document.updated_by = ctx.user_id
    await history.write(session, ctx, document, before=before)
