from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field

from licensing_api.repo.base import AuditColumns, TimestampTZ


class DocumentOwnerType(StrEnum):
    """The kind of record a document belongs to (``owner_type``)."""

    PRACTITIONER = 'practitioner'
    PARTICIPATION_APPLICATION = 'participation_application'
    PRIVILEGE_REQUEST = 'privilege_request'
    ADVERSE_ACTION = 'adverse_action'
    SII_REPORT = 'sii_report'
    # A state's practice-requirements document (S-01); keyed by the state code in owner_key.
    STATE = 'state'
    INGESTION_BATCH = 'ingestion_batch'


class ScanStatus(StrEnum):
    """A document's malware-scan result (``scan_status``); an upload starts ``pending``."""

    PENDING = 'pending'
    CLEAN = 'clean'
    INFECTED = 'infected'
    ERROR = 'error'


class Document(AuditColumns, table=True):
    """A file in object storage, owned by one record (D9). ``created_by`` is the uploader.

    The owner is polymorphic (``owner_type`` with ``owner_id``, or ``owner_key``
    for a state), so there is no foreign key; the owner's permissions decide who
    may download it. A document may be uploaded before its owner exists, with all
    three owner fields empty until it is attached. The rules require keeping every
    document a state submits (Rule 4 §4.3(e)(4)).
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'documents'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    public_id: UUID = Field(default_factory=uuid4, unique=True)
    owner_type: str | None = None
    owner_id: int | None = None
    owner_key: str | None = None
    # The state staff uploaded it for; None for a PA's upload. Scopes it until it is attached.
    uploaded_in_state: str | None = Field(default=None, foreign_key='states.code')
    kind: str
    storage_key: str = Field(unique=True)
    file_name: str
    content_type: str
    size_bytes: int
    scan_status: str = ScanStatus.PENDING
    # When the scan's result was recorded, and when the Worker last looked for one.
    scanned_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    scan_checked_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    # The object version the result belongs to; downloads serve this version only.
    scanned_version_id: str | None = None

    @property
    def is_attached(self) -> bool:
        """Whether the document belongs to a record yet."""
        return self.owner_type is not None


def storage_key_for(public_id: UUID) -> str:
    """The object key: the document's public ID, never anything the uploader typed."""
    return f'documents/{public_id}'
