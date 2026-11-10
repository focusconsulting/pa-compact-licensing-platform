"""What may be uploaded as a document (backlog D9, F-12).

The API checks a request against these limits, the bucket's POST policy enforces the
declared size and type, and the scan step checks the file's first bytes match its type.
"""

from __future__ import annotations

from datetime import timedelta
from enum import StrEnum

# 20 MiB: the ticket's 20 MB upload fits, and 21 MB does not.
MAX_BYTES = 20 * 1024 * 1024

# Long enough for 20 MiB on a slow connection; the link only uploads to one new key.
UPLOAD_LINK_LIFETIME = timedelta(minutes=5)


class DocumentType(StrEnum):
    """The content types the bucket accepts."""

    PDF = 'application/pdf'
    PNG = 'image/png'
    JPEG = 'image/jpeg'
    CSV = 'text/csv'
    DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'


EXTENSIONS: dict[DocumentType, tuple[str, ...]] = {
    DocumentType.PDF: ('.pdf',),
    DocumentType.PNG: ('.png',),
    DocumentType.JPEG: ('.jpg', '.jpeg'),
    DocumentType.CSV: ('.csv',),
    DocumentType.DOCX: ('.docx',),
}
