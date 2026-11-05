"""What may be uploaded as a document (backlog D9, F-12).

The API checks a request against these limits, the bucket's POST policy enforces the
declared size and type, and the scan step checks the file's first bytes match its type.
"""

from __future__ import annotations

import codecs
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

# The bytes each type starts with. DOCX is a ZIP archive; the malware scan looks inside it.
_SIGNATURES: dict[DocumentType, bytes] = {
    DocumentType.PDF: b'%PDF-',
    DocumentType.PNG: b'\x89PNG\r\n\x1a\n',
    DocumentType.JPEG: b'\xff\xd8\xff',
    DocumentType.DOCX: b'PK\x03\x04',
}


def matches_type(content_type: str, start: bytes) -> bool:
    """Whether a file's first bytes are what its declared type starts with.

    CSV has no signature: it must be UTF-8 text with no NUL byte. ``start`` may end inside a
    multi-byte character, which is not an error.
    """
    document_type = DocumentType(content_type)
    if document_type is DocumentType.CSV:
        if b'\x00' in start:
            return False
        try:
            codecs.getincrementaldecoder('utf-8')().decode(start, final=False)
        except UnicodeDecodeError:
            return False
        return True
    return start.startswith(_SIGNATURES[document_type])
