from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field

from licensing_api.repo.base import AuditColumns


class DocumentOwnerType(StrEnum):
    PRACTITIONER = 'practitioner'
    PARTICIPATION_APPLICATION = 'participation_application'
    PRIVILEGE_REQUEST = 'privilege_request'
    ADVERSE_ACTION = 'adverse_action'
    SII_REPORT = 'sii_report'


class ScanStatus(StrEnum):
    PENDING = 'pending'
    CLEAN = 'clean'
    INFECTED = 'infected'
    ERROR = 'error'


class Document(AuditColumns, table=True):
    """A file in object storage, owned by one record (D9). ``created_by`` is the uploader.

    The owner is polymorphic (``owner_type`` + ``owner_id``), so there is no
    foreign key; the owner's permissions decide who may download it. The rules
    require keeping every document a state submits (Rule 4 §4.3(e)(4)).
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'documents'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    public_id: UUID = Field(default_factory=uuid4, unique=True)
    owner_type: str
    owner_id: int
    kind: str
    storage_key: str = Field(unique=True)
    file_name: str
    content_type: str
    size_bytes: int
    scan_status: str = ScanStatus.PENDING
