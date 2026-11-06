# Document Storage and Scanning (SCRUM-81) Implementation Plan

## Overview

PAs and state staff upload documents straight to a private bucket through short-lived presigned links. GuardDuty scans each file. A Worker step reads the scan result from the object's tag, and a document can be downloaded only once it is clean, only by someone whose scope covers its owner, and only through a 60-second link. This replaces phases 12–13 of [`2026-10-21-SCRUM-78-81-platform-tracks.md`](../api/2026-10-21-SCRUM-78-81-platform-tracks.md); the decisions below differ from it where noted.

## Related

- **Spec**: F-12 in [`mvp-ticket-breakdown.md`](../../../../../product/backlog/mvp-ticket-breakdown.md) (epic 2 in [`mvp-jira-tickets.md`](../../../../../product/backlog/mvp-jira-tickets.md)); consumers L-03, P-01, A-02, D-01
- **Flows**: [FLOW-01](../../../../../product/context/flows/01-end-to-end-privilege-issuance.md) (documents step), [FLOW-02](../../../../../product/context/flows/02-sql-eligibility-verification.md) (documents added on resubmission), [FLOW-03](../../../../../product/context/flows/03-payment-and-remote-state-issuance.md) (per-state proofs), [FLOW-05](../../../../../product/context/flows/05-adverse-action-cascade.md) (optional order attachment), [FLOW-07](../../../../../product/context/flows/07-domain-event-catalogue.md) (two new events)
- **Compact rules**: Rule 4 §4.3(e)(4) (state documents are kept), Rule 4 §4.4 (reports and SII), Rule 4 §4.5 (confidentiality), R2r §2.1(c) and R3r §3.4(c)(3)–(6) (proofs)
- **Decisions**: D9 (documents), D13 (local stack); Q-07 (which documents are required) stays open and does not block this
- **Jira**: SCRUM-81 (epic SCRUM-68). GuardDuty Malware Protection moves here from SCRUM-84
- **ADRs**: [ADR-0009](../../../../adrs/0009-route-authorization-and-change-context.md), [ADR-0012](../../../../adrs/0012-outbox-dispatcher.md), [ADR-0014](../../../../adrs/0014-email-templates-and-smtp.md) (the blocking-client-in-a-thread precedent), [ADR-0015](../../../../adrs/0015-opentofu-for-infrastructure.md); new ADR-0017 (S3 client)
- **Area**: cross-cutting (api, client, iac, local tooling)

## Decisions (2026-11-05, with Jamie)

| # | Decision | Differs from the earlier plan |
|---|---|---|
| 1 | Upload by presigned POST straight to the bucket; download by presigned GET issued after the permission check | No |
| 2 | SCRUM-81 provisions the GuardDuty Malware Protection for S3 plan | Yes: it was left to epic 3 |
| 3 | The Worker loop polls the `GuardDutyMalwareScanStatus` tag on pending documents; still pending after 15 minutes → `error` | Yes: it was a once-a-minute job |
| 4 | Locally, a ClamAV container plus a small tagger in `engineering/mocks/malware-scanner/` writes the same tag; not started in CI | ClamAV as before; CI exclusion is new |
| 5 | Allowed types: PDF, JPEG, PNG, CSV, DOCX; at most 20 MiB | Yes: CSV and DOCX added |
| 6 | Download scope per owner type as in [Scope](#scope) | Detailed here for the first time |
| 7 | `document.uploaded` and `document.scanned` join FLOW-07, with no consumer at pilot | New |
| 8 | `FilePickerField` polls the document until its scan finishes and shows the result | New |

## Constitution Check

- **I.** `boto3` is a new dependency: ADR-0017 compares `boto3` in a thread, `aioboto3`/`aiobotocore`, and hand-rolled SigV4, each with pros and cons, and the API README table lists it. Blocking calls run under `asyncio.to_thread`, as `smtplib` does (ADR-0014). File-type checks are a few byte signatures, with no `python-magic`/libmagic.
- **II.** Every route declares `require(...)`. Scope is in the query; out of scope is `404`. The client's size and type checks are convenience; the API and the bucket's POST policy enforce them.
- **III.** Tests run against real Postgres and real RustFS. GuardDuty is mocked at its boundary: tests write the scan tag directly. The Worker step is tested by calling it.
- **IV.** The local scanner is Docker Compose tooling outside the app; the app reads the tag through the same `boto3` call in every environment. Only `S3_ENDPOINT_URL` and keys differ locally.
- **VI.** Document rows get `documents_history`. Upload and scan each write history and an event in one transaction. `attach()` writes history inside its caller's transaction, whose event covers it. Documents are never deleted.
- **VII.** Upload links last 5 minutes; download links 60 seconds and force `attachment`. The bucket is private, SSE-KMS with a customer key, versioned, TLS-only, and refuses `GetObject` on any object not tagged `NO_THREATS_FOUND` (GuardDuty's role excepted). Task role: object-level actions on this bucket only.
- **VIII.** Every S3 call logs `duration_ms` and `outcome`; the scan step logs `Document scanned` with the result. A CloudWatch metric filter and alarm on `outcome=infected` routes to the Slack topic.
- **IX.** Scope cites Rule 4 §4.5 once in `repo/document.py`; retention cites Rule 4 §4.3(e)(4) where it already does.
- **XI.** New `engineering/docs/documents.md` (behavior, events, permissions); `platform-contract.md` `.6`; `architecture.md` (GuardDuty, scanner); `data-model.md`. The PR adding `boto3` names it for Commission consent (SOW §7.5).
- **XII.** New settings already in `.env.example`; README lists ClamAV and the scanner; Compose and both justfiles start them.
- **XIII.** The 15-minute scan timeout and link lifetimes are instants, not calendar days; no day arithmetic.
- **XIV.** One additive migration (two nullable columns, a history table, a partial index on an empty table).
- **XV.** Six PRs, each under 600 production lines.

## Current State Analysis

- `documents` exists with `scan_status` and a polymorphic owner (`repo/document.py`, `20261007_100000_data_model_core_entities_a.sql:181-216`); no history table, no `scanned_at`, no code reads or writes it.
- `S3_*` settings are in `.env.example:57-68` but `Settings` (`config.py`) has none; no S3 client dependency.
- RustFS runs locally with a `documents` bucket (`docker-compose.yaml:31-62`); no versioning, no CORS. PR #168 (open) moves `rustfs-init` to a profile; whichever lands second merges.
- `run_worker` (`worker.py:63-84`) loops `dispatch_events` then `send_pending`, idling one second.
- `record_guard.py` fails a route test that writes history with no event; `test_event_catalogue.py` needs every `EventType` to have a handler or a named owner.
- `states_holding(session, practitioner_id)` (`notifications/recipients.py:33`) returns the states where the PA holds a license or a privilege.
- `ErrorCode` has no 404 or 409 member (`errors.py`).
- Infra: one shared ECS task role (`ecs.tf:74-124`) for API, Worker, and jobs; no KMS key; no documents bucket; API env at `ecs.tf:157-187`, Worker env in `worker.tf:9-28`; client origin is `https://${var.dns_name}`; AWS provider 6.70 supports `aws_guardduty_malware_protection_plan`.
- Client: `FilePickerField` stores the file name and is used nowhere; no error UI pattern beyond `AlertBanner`; `answerFetch` answers every call the same way.

## Desired End State

- A PA uploads a 20 MiB PDF from `FilePickerField`; a request declaring 21 MB gets `422`, and a POST to the bucket larger than the declared size is refused by the bucket.
- Locally, an EICAR file is tagged `THREATS_FOUND`, becomes `infected` within seconds, the field shows it was rejected, and the download route answers `409`. In staging, GuardDuty does the same, and a direct `GetObject` on it is denied by the bucket policy.
- State A staff get `404` for a document attached to state B's application; the Commission can download it, and its download writes an audit row.

## What We're NOT Doing

- Feature pages that use the field (L-03, P-01, A-02) or a document list (D-01). The field is wired to the API and shown in Storybook.
- A practitioner history timeline. Documents get `documents_history`; showing it on the PA's timeline is D-01/L-04.
- Applying OpenTofu. The PR is validated and planned in CI; Jamie applies it to staging.
- Prod tfvars (none exist yet).
- `ingestion_batch` scoping beyond "unattached rules" — the table does not exist until SCRUM-149.
- A CSP. When SCRUM-84 adds one, `form-action`/`connect-src` needs the bucket's regional endpoint; the infra PR says so.
- `X-Content-Type-Options: nosniff` on downloads: S3 cannot add arbitrary response headers to a presigned GET. Mitigated by `attachment`, the stored content type, the clean-only rule, and the type check.

## Scope

Rule 4 §4.5. A state route requires `READ_PRIVATE` in that state; the Commission route `COMPACT_ADMIN`; `/me` any signed-in licensee.

| Owner | PA (`/me`) | State staff (`/states/{s}`) |
|---|---|---|
| `practitioner` | theirs | `s` in `states_holding(PA)` |
| `participation_application` | theirs | `s` = `sql_state_code` |
| `privilege_request` | theirs | `s` = `remote_state_code` |
| `adverse_action`, `sii_report` | never | `s` = `reporting_state_code` or in `states_holding(PA)` |
| `state` | no | `s` = `owner_key` |
| unattached | they uploaded it | `documents.uploaded_in_state` = `s`, set from the upload route's path (security review, 2026-11-05: not the uploader's home state, which can differ or change) |
| `ingestion_batch` | no | same as unattached until SCRUM-149 |

The Commission sees every document. Every staff download writes `document.downloaded` to `audit_log`; a PA's own download does not.

## Implementation Approach

Branches stack, each PR targeting the one below, as GitHub native stacked drafts.

| # | Branch | PR |
|---|---|---|
| 1 | `feature/SCRUM-81-storage` | ADR-0017, `boto3`, settings, `storage.py`, RustFS versioning and CORS, this plan |
| 2 | `feature/SCRUM-81-upload` | Migration, history, events, type limits, upload and metadata routes, `attach()` |
| 3 | `feature/SCRUM-81-scan` | Worker scan step, timeout, ClamAV and the tagger |
| 4 | `feature/SCRUM-81-download` | Scoped download routes, audit, `NOT_FOUND` |
| 5 | `feature/SCRUM-81-infra` | Bucket, KMS key, GuardDuty plan, task role, settings in the task definitions, alarm |
| 6 | `feature/SCRUM-81-client` | `FilePickerField` uploads and polls; story |

Every API PR regenerates `openapi.json` and the client's `schema.d.ts` with `just generate` (both drift checks run in CI).

---

## Phase 1: The S3 client (`feature/SCRUM-81-storage`)

### Changes Required

- **ADR-0017** `engineering/adrs/0017-s3-client.md`: `boto3` with `asyncio.to_thread` (chosen), `aioboto3`/`aiobotocore`, hand-rolled SigV4 over `httpx`; pros and cons each. Presigning is local; only tag reads, heads, and ranged reads do I/O.
- **`pyproject.toml`**: `boto3`; dev `boto3-stubs[s3]` for pyright. README dependency table rows.
- **`licensing_api/config.py`**: `s3_endpoint_url: str | None = None`, `s3_region = 'us-east-1'`, `s3_documents_bucket = 'documents'`. Credentials come from boto3's own chain, not settings (decided 2026-11-05, after the repo's secrets hook refused key fields): the task role in AWS, `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` in `.env` locally, replacing `S3_ACCESS_KEY_ID`/`S3_SECRET_ACCESS_KEY`.
- **`licensing_api/storage.py`** (new): `Storage(client, bucket)` built once by `create_storage(settings)`; the API keeps it on `app.state` (set in `lifespan`) behind a `get_storage` dependency, the Worker builds its own.
  - `presign_upload(key, *, content_type, size_bytes, expires) -> PresignedUpload(url, fields)`: POST policy with `content-length-range` `[size_bytes, size_bytes]` and exact `Content-Type`.
  - `presign_download(key, *, file_name, content_type, expires) -> str`: `ResponseContentDisposition` `attachment; filename*=UTF-8''…`, `ResponseContentType`.
  - `async scan_tag(key) -> str | None`, `async read_start(key, size) -> bytes`; each logs `duration_ms` and `outcome`; a missing object is `None`/`b''`, other `ClientError`s raise.
- **Compose**: `rustfs-init` also runs `put-bucket-versioning` and `put-bucket-cors` (POST from `http://localhost:3000`).
- **Tests** `tests/test_storage.py` against RustFS: a presigned POST of exactly the declared size succeeds; one byte more and a different `Content-Type` are refused; the download link returns the bytes with `attachment`; tags and ranged reads.
- This plan file.

## Phase 2: Upload (`feature/SCRUM-81-upload`)

### Changes Required

- **Migration** `20261105_090000_documents_scan.sql`: `documents.scanned_at`, `documents.scan_checked_at` (nullable `TIMESTAMPTZ`); `SELECT create_history_table('documents')`; partial index on `scan_checked_at` `WHERE scan_status = 'pending'`.
- **`repo/history.py`**: `DocumentHistory`, registered.
- **`repo/document.py`**: the two columns; `storage_key_for(public_id)` = `documents/<public_id>`; `attach(session, ctx, document, *, owner_type, owner_id=None, owner_key=None)` — raises `ValueError` on an attached document, writes history; the caller emits.
- **`repo/domain_event.py`**: `DOCUMENT_UPLOADED`, `DOCUMENT_SCANNED`; FLOW-07 rows; `_CONSUMED_ELSEWHERE` owner "history only; D-01 lists documents".
- **`licensing_api/documents.py`** (new): `MAX_BYTES = 20 MiB`; `ALLOWED` maps each content type to its extensions and a signature check (`%PDF-`; PNG magic; `FF D8 FF`; `PK\x03\x04`; CSV: UTF-8 with no NUL).
- **`errors.py`**: `NotFound = 'NOT_FOUND'`, `DocumentNotClean = 'DOCUMENT_NOT_CLEAN'` (used in phase 4).
- **`routes/document.py`** (new), mounted under `/me` and `/states/{state_code}`:
  - `POST …/documents` (`/me`: `MANAGE_OWN_RECORD`; states: `WRITE`): body `{file_name, content_type, size_bytes, kind}` (extension must match the type, size 1..`MAX_BYTES`, `kind` a short slug until Q-07) → `201` `Data[DocumentUpload]` = the `pending` document plus `{url, fields, expires_at}`. Writes the row, history, `document.uploaded`.
  - `GET …/documents/{document_id}` → `Data[DocumentOut]` (`id`, `file_name`, `content_type`, `size_bytes`, `kind`, `scan_status`, `created_at`); scoped as phase 4 describes — in this PR, the uploader only.
- **Tests** `tests/test_documents_upload.py`: 20 MiB accepted and the returned form uploads to RustFS; 21 MB `422`; wrong type, mismatched extension, unknown field `422`; states route without `WRITE` `403`; history and event written; `attach` on an attached document raises.

## Phase 3: Scanning (`feature/SCRUM-81-scan`)

### Changes Required

- **`licensing_api/scans.py`** (new): `check_document_scans(session_factory, storage, *, batch_size=20) -> int` — one transaction per document, claimed `FOR UPDATE SKIP LOCKED` where `scan_status = 'pending'` and `scan_checked_at` is null or 5 s old:
  - `NO_THREATS_FOUND` → `read_start(8 KiB)`; signature matches → `clean`, else `error`.
  - `THREATS_FOUND` → `infected`. `UNSUPPORTED`, `ACCESS_DENIED`, `FAILED` → `error`.
  - No tag and created 15 minutes ago → `error`; otherwise stamp `scan_checked_at` and move on.
  - Tags and bytes are read from the object's current version, and a result also stores that `VersionId` in `documents.scanned_version_id` (new migration). An upload link lasts five minutes and can be reused, so a later POST makes a new, unscanned version; only the stored version is ever served (security review, 2026-11-05).
  - A result sets `scanned_at`, writes history, emits `document.scanned`, logs `Document scanned` with `outcome`. An S3 error logs and stamps `scan_checked_at`. Returns the number of results recorded.
- **`worker.py`**: builds `Storage`; `run_worker(..., storage, ...)` runs the step after `send_pending` and counts it toward the idle check.
- **`engineering/mocks/malware-scanner/`**: `Dockerfile` (`python:3.13-slim`, pinned `boto3`), `scanner.py` (lists the bucket, streams each untagged object to `clamd` with `INSTREAM`, tags it `NO_THREATS_FOUND`/`THREATS_FOUND`/`FAILED`), `README.md`.
- **Compose**: `clamav` (`clamav/clamav-debian:1.5.1`, which ships arm64 where `clamav/clamav` does not, healthcheck `clamdcheck.sh`, signatures bind-mounted from `engineering/api/.clamav/` so `infra-down -v` keeps them) and `malware-scanner`, both in profile `scanner`. Root `just services` and API `just infra` pass `--profile scanner`; `api.yml` and `e2e.yml` don't.
- **Docs**: README services table; `architecture.md` local-substitution row.
- **Tests** `tests/test_document_scans.py` (tags written by the test): each tag maps to its status; a mismatched signature → `error`; timeout → `error`; a fresh untagged document is untouched; two concurrent calls record once; history and event; `test_worker.py` covers the new step.

## Phase 4: Download (`feature/SCRUM-81-download`)

### Changes Required

- **`repo/document.py`**: `visible_to_practitioner(practitioner_id, user_id)` and `visible_to_state(state_code)` return SQL conditions per [Scope](#scope), using `EXISTS` on the owner tables and the `states_holding` union.
- **`routes/document.py`**: the metadata route takes the scope; `GET …/documents/{document_id}/download` under `/me`, `/states/{state_code}` (`READ_PRIVATE`), `/commission` (`COMPACT_ADMIN`) → `Data[DocumentDownload]` `{url, expires_at}`, the link naming `scanned_version_id`; `404 NOT_FOUND` out of scope; `409 DOCUMENT_NOT_CLEAN` unless `clean`; staff calls write `audit_log.write(…, 'document.downloaded', document)`.
- **Docs**: `docs/documents.md`; `roles-and-permissions.md`; `platform-contract.md` `.6` implemented.
- **Tests** `tests/test_documents_download.py`: the Scope table row by row, each with an in-scope and out-of-scope caller; state A `404` on state B's application document; pending and infected `409`; audit row for staff only; the link returns the bytes.

## Phase 5: Infrastructure (`feature/SCRUM-81-infra`)

### Changes Required

- **`documents.tf`**: `aws_kms_key` (rotation on) and alias; bucket `${env}-licensing-documents`, public access block, `BucketOwnerEnforced`, versioning, SSE-KMS with bucket key, CORS (`POST` from `https://${var.dns_name}`); policy denying non-TLS and denying `s3:GetObject` when `s3:ExistingObjectTag/GuardDutyMalwareScanStatus` ≠ `NO_THREATS_FOUND` unless the principal is the GuardDuty role.
- **`guardduty.tf`**: the Malware Protection role (trust `malware-protection-plan.guardduty.amazonaws.com`, `aws:SourceAccount`) with AWS's documented policy scoped to the bucket and key; `aws_guardduty_malware_protection_plan` with tagging enabled.
- **`ecs.tf`**: `aws_iam_role_policy.ecs_task_documents` — `s3:PutObject`, `s3:GetObject`, `s3:GetObjectTagging` on `documents/*`, `s3:ListBucket` on the bucket, `kms:GenerateDataKey`, `kms:Decrypt` on the key; `S3_DOCUMENTS_BUCKET`, `S3_REGION` in the API env and `local.worker_environment`.
- **`alerting.tf`**: metric filter and alarm on `Document scanned` with `outcome=infected`.
- **`outputs.tf`**: `documents_bucket`. Comment on SCRUM-84 that GuardDuty moved here.
- Verified with `just check` and CI's staging plan; Jamie applies and uploads EICAR in staging.

## Phase 6: The file picker (`feature/SCRUM-81-client`)

### Changes Required

- **`src/lib/documents.ts`** (new): `uploadDocument(target, file, kind)` (create, then `FormData` POST of the fields then the file to the returned URL) and `waitForScan(target, id)` (polls every 2 s until not `pending`). `target` is `{ kind: "me" }` or `{ kind: "state", stateCode }`.
- **`FilePickerField.tsx`**: props `target` and `kind`; checks size and type before uploading; status text ("Uploading…", "Checking file…", "Uploaded", rejected/failed) in a live region tied to the input; the form value becomes `{ id, fileName }`, and a default value restores the name. Strings in `common.json` `filePicker`.
- **Story** `FilePickerField.stories.tsx` with its own `FormProvider`.
- **Tests**: every status path, the client-side checks, restore from defaults, axe.

---

## Testing Strategy

### API Tests (against Postgres and RustFS)

- Upload limits at the API and at the bucket; scope per owner type, both namespaces and the Commission; scan results from each tag; timeout; concurrency; history, events, and audit.

### E2E Tests

- None in this ticket: no flow page uses the field yet. L-03 adds the documents step's E2E (golden path and an EICAR rejection) with the scanner profile.

### Manual Testing Steps

1. `just up`; in Storybook or a scratch page, upload a PDF: "Checking file…" then "Uploaded".
2. Upload the EICAR test file: "rejected"; `GET …/download` answers `409`.
3. `curl` the upload form with a 21 MB file: refused by RustFS.
4. In staging after apply: EICAR → `infected`; `aws s3api get-object` on it is denied.

## Security Impact Assessment

- **Data**: uploaded proofs, orders, and complaints: PII, and for adverse actions and SII, States-and-Commission tier. File names are user input and are only ever returned to the same scope.
- **Flow**: browser → bucket (presigned POST, 5 minutes, exact size and type, server key) → GuardDuty → tag → Worker → `scan_status` → API scope check → presigned GET (60 s, attachment) → browser.
- **Protection**: private, KMS-encrypted, versioned bucket; TLS only; deny-unless-clean bucket policy as a second wall behind the API's `clean` check; least-privilege task role; audit row on every staff download; links never logged.
- **What could go wrong**: a leaked download link (60 s window, clean files only, scope checked at issue); a mislabeled file (signature check after a clean scan; `attachment`); a file never scanned (timeout → `error`, never downloadable); cross-state access (scope tests per row; `404`); an unattached upload abandoned (kept, `pending` → `error`, never served).

## Dates and Deadlines

Not applicable: link lifetimes and the scan timeout are instants in UTC, not calendar dates.

## Migration Notes

`20261105_090000_documents_scan.sql` adds two nullable columns, an empty history table, and a partial index on `documents`, which holds no rows in any environment. The running release ignores the new columns.

## Documentation Updates

`docs/documents.md` (new); `platform-contract.md` `.6`; `data-model.md` (`documents` columns, `documents_history`); `architecture.md` (GuardDuty, Worker → bucket, local scanner); `roles-and-permissions.md`; FLOW-07 (two events); API README dependencies; root README services; `engineering/mocks/malware-scanner/README.md`.

## Performance Considerations

The scan step reads one tag per pending document at most every 5 s; pilot volume is a handful a day. Presigning is local CPU. Downloads and uploads never pass through ECS.

## References

- Ticket: SCRUM-81; spec F-12
- Earlier plan: [`2026-10-21-SCRUM-78-81-platform-tracks.md`](../api/2026-10-21-SCRUM-78-81-platform-tracks.md) phases 12–13
- Step pattern: `engineering/api/licensing_api/notifications/sender.py:33-117`
- Scope helper: `engineering/api/licensing_api/notifications/recipients.py:33`
