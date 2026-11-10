"""Documents: upload links and each document's details (backlog D9, F-12).

The browser uploads straight to the bucket with the link a ``POST`` returns; the API never
handles the bytes. A new document is ``pending`` until the Worker records its malware scan.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.context import ChangeContext, change_context
from licensing_api.dependencies import get_db_session, get_storage
from licensing_api.documents import EXTENSIONS, MAX_BYTES, UPLOAD_LINK_LIFETIME, DocumentType
from licensing_api.errors import AppError, ErrorCode
from licensing_api.permissions import Permission, require
from licensing_api.repo import history
from licensing_api.repo.base import utc_now
from licensing_api.repo.document import Document, ScanStatus, storage_key_for
from licensing_api.repo.domain_event import EventType, emit
from licensing_api.repo.user import User
from licensing_api.responses import Data, example
from licensing_api.storage import Storage

me = APIRouter(prefix='/documents')
states = APIRouter(prefix='/documents')

StateCode = Annotated[str, Path(pattern=r'^[A-Za-z]{2}$', description='Two-letter state code')]
DocumentId = Annotated[UUID, Path(description="The document's ID")]

_EXAMPLE_ID = UUID('0b9c7a52-4f1e-4d38-9f43-2a5d6f1c8e70')
_EXAMPLE_CREATED = datetime.fromisoformat('2026-11-05T15:04:05Z')
_DOCUMENT_EXAMPLE = {
    'id': _EXAMPLE_ID,
    'file_name': 'nccpa-certificate.pdf',
    'content_type': DocumentType.PDF,
    'size_bytes': 482113,
    'kind': 'nccpa_certificate',
    'scan_status': ScanStatus.PENDING,
    'created_at': _EXAMPLE_CREATED,
}
_FORM_EXAMPLE = {
    'url': 'https://example-documents.s3.amazonaws.com/',
    'fields': {'key': f'documents/{_EXAMPLE_ID}', 'Content-Type': DocumentType.PDF},
    'expires_at': _EXAMPLE_CREATED,
}


class DocumentUploadIn(BaseModel):
    """The file the browser is about to upload. The bucket refuses any other size or type."""

    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra=example(
            file_name='nccpa-certificate.pdf',
            content_type=DocumentType.PDF,
            size_bytes=482113,
            kind='nccpa_certificate',
        ),
    )

    file_name: str = Field(min_length=1, max_length=255, pattern=r'^[^/\\\x00-\x1f\x7f]+$')
    content_type: DocumentType
    size_bytes: int = Field(ge=1, le=MAX_BYTES)
    # Free text until Q-07 settles the list of document kinds.
    kind: str = Field(pattern=r'^[a-z][a-z0-9_]{0,49}$')

    @model_validator(mode='after')
    def _extension_matches_type(self) -> DocumentUploadIn:
        if not self.file_name.lower().endswith(EXTENSIONS[self.content_type]):
            raise ValueError(
                f'file_name must end in {" or ".join(EXTENSIONS[self.content_type])} '
                f'for {self.content_type}'
            )
        return self


class DocumentOut(BaseModel):
    """A document's details. ``scan_status`` is ``clean`` once it may be downloaded."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra=example(**_DOCUMENT_EXAMPLE),
    )

    id: UUID = Field(validation_alias='public_id')
    file_name: str
    content_type: str
    size_bytes: int
    kind: str
    scan_status: ScanStatus
    created_at: datetime


class UploadForm(BaseModel):
    """POST the ``fields`` and then the file, as ``multipart/form-data`` field ``file``, to ``url``."""

    model_config = ConfigDict(json_schema_extra=example(**_FORM_EXAMPLE))

    url: str
    fields: dict[str, str]
    expires_at: datetime


class DocumentUpload(BaseModel):
    """The new ``pending`` document and the form that uploads its file."""

    model_config = ConfigDict(
        json_schema_extra=example(document=_DOCUMENT_EXAMPLE, upload=_FORM_EXAMPLE)
    )

    document: DocumentOut
    upload: UploadForm


_UPLOAD_DESCRIPTION = (
    'Creates a `pending` document and returns a form, valid for five minutes, that uploads '
    'exactly `size_bytes` of `content_type` straight to storage. The file is scanned for '
    'malware before anyone can download it.'
)


@me.post(
    '',
    status_code=201,
    name='Upload my document',
    description=_UPLOAD_DESCRIPTION,
)
async def upload_my_document(
    body: DocumentUploadIn,
    _caller: Annotated[User, require(Permission.MANAGE_OWN_RECORD)],
    ctx: Annotated[ChangeContext, Depends(change_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[Storage, Depends(get_storage)],
) -> Data[DocumentUpload]:
    """A PA's upload, unattached until a record they submit attaches it."""
    return Data(data=await _upload(session, ctx, storage, body))


@states.post(
    '',
    status_code=201,
    name="Upload a state's document",
    description=_UPLOAD_DESCRIPTION,
)
async def upload_state_document(
    state_code: StateCode,
    body: DocumentUploadIn,
    _caller: Annotated[User, require(Permission.WRITE, state_param='state_code')],
    ctx: Annotated[ChangeContext, Depends(change_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[Storage, Depends(get_storage)],
) -> Data[DocumentUpload]:
    """A state staff member's upload, such as an order to attach to an adverse action (FLOW-05)."""
    return Data(data=await _upload(session, ctx, storage, body))


@me.get(
    '/{document_id}',
    name='Get my document',
    description="A document's details, including whether its malware scan has finished.",
)
async def get_my_document(
    document_id: DocumentId,
    caller: Annotated[User, require(Permission.MANAGE_OWN_RECORD)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[DocumentOut]:
    """Only the uploader sees an unattached document; ``404`` for anyone else (Principle II)."""
    return Data(data=DocumentOut.model_validate(await _uploaded_by(session, caller, document_id)))


@states.get(
    '/{document_id}',
    name="Get a state's document",
    description="A document's details, including whether its malware scan has finished.",
)
async def get_state_document(
    state_code: StateCode,
    document_id: DocumentId,
    caller: Annotated[User, require(Permission.WRITE, state_param='state_code')],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[DocumentOut]:
    """Only the uploader sees an unattached document; ``404`` for anyone else (Principle II)."""
    return Data(data=DocumentOut.model_validate(await _uploaded_by(session, caller, document_id)))


async def _upload(
    session: AsyncSession, ctx: ChangeContext, storage: Storage, body: DocumentUploadIn
) -> DocumentUpload:
    public_id = uuid4()
    document = Document(
        public_id=public_id,
        kind=body.kind,
        file_name=body.file_name,
        content_type=body.content_type,
        size_bytes=body.size_bytes,
        storage_key=storage_key_for(public_id),
        created_by=ctx.user_id,
    )
    session.add(document)
    await history.write(session, ctx, document, before=None)
    await emit(session, ctx, EventType.DOCUMENT_UPLOADED, document)
    await session.commit()
    form = storage.presign_upload(
        document.storage_key,
        content_type=document.content_type,
        size_bytes=document.size_bytes,
        expires=UPLOAD_LINK_LIFETIME,
    )
    return DocumentUpload(
        document=DocumentOut.model_validate(document),
        upload=UploadForm(
            url=form.url, fields=form.fields, expires_at=utc_now() + UPLOAD_LINK_LIFETIME
        ),
    )


async def _uploaded_by(session: AsyncSession, caller: User, document_id: UUID) -> Document:
    statement = select(Document).where(
        col(Document.public_id) == document_id, col(Document.created_by) == caller.id
    )
    document = (await session.scalars(statement)).one_or_none()
    if document is None:
        raise AppError(404, ErrorCode.NotFound, ['No such document'])
    return document
