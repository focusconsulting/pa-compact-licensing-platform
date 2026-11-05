# Documents

Proofs, orders, and verification documents that PAs and states upload (backlog
D9, F-12; [plan](../thoughts/shared/plans/cross-cutting/2026-11-05-SCRUM-81-documents.md)).
The rules require PAs and states to submit them and the system to keep every
one a state submits (Rule 4 §4.3(e)(4)). A document is never deleted.

## Lifecycle

1. **Upload.** `POST /me/documents` (a PA) or `POST /states/{state_code}/documents`
   (`write` in that state) creates a `pending` document and returns a form
   valid for five minutes. The browser posts the file straight to the bucket;
   the bucket accepts only the declared size and type. Allowed: PDF, PNG, JPEG,
   CSV, DOCX, at most 20 MiB. Event: `document.uploaded`.
2. **Scan.** GuardDuty Malware Protection scans each new object version and tags
   it `GuardDutyMalwareScanStatus` (locally, ClamAV and
   [`malware-scanner`](../mocks/malware-scanner/README.md) do the same). The
   Worker reads the tag of each pending document's current version, checks a
   clean file starts like its type, and records `clean`, `infected`, or `error`
   with that version. No result within 15 minutes is `error`. Event:
   `document.scanned`. Log: `Document scanned` with `outcome` and `reason`.
3. **Attach.** The feature that owns the record calls `attach()` in its own
   transaction (L-03, P-01, A-02). A document is attached once and never moves.
4. **Download.** `GET .../documents/{id}/download` returns a link valid for one
   minute to the scanned version, saved as a file. Anything but `clean` is
   `409 DOCUMENT_NOT_CLEAN`. In AWS, the bucket also refuses any version not
   tagged `NO_THREATS_FOUND`.

`GET .../documents/{id}` returns a document's details, including `scan_status`,
so the client can show when a scan finishes.

## Who may see a document

The owner's record decides (Rule 4 §4.5; `repo/document_scope.py`). Out of scope
is `404` (constitution Principle II).

| Owner | PA (`/me`) | State staff (`/states/{s}`, `read_private`) |
|---|---|---|
| practitioner | theirs | `s` holds a license or privilege of the PA |
| participation application | theirs | `s` is its state of qualifying license |
| privilege request | theirs | `s` is its remote state |
| adverse action, SII report | never | `s` reported it, or holds a license or privilege of the PA |
| state | no | `s` is that state |
| none yet, or ingestion batch | they uploaded it | the uploader's state is `s` |

`/commission` (`compact_admin`) sees every document. Every staff download writes
`document.downloaded` to the audit log; a PA reading their own does not.
