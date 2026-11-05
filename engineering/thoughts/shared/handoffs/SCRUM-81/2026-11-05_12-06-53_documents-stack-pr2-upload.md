---
date: 2026-11-05T12:06:53-05:00
git_commit: 3c2f6935d4dcf71f18554a27939300bcb6664a09
branch: feature/SCRUM-81-upload
repository: pa-compact-licensing-platform
task_id: SCRUM-81
status: handoff
---

# Handoff: SCRUM-81 document storage and scanning, paused in PR 2 (upload)

## Task(s)

SCRUM-81 (F-12) is split into six stacked draft PRs. Jamie asked for all of them as drafts to review, and was asked clarifying questions before implementation. The ticket is already In Progress.

- **Completed**: plan (`a7e2207`); PR 1 S3 client on `feature/SCRUM-81-storage` (`3c2f693`). 403 tests passed at 100% coverage; lint and pyright clean.
- **In progress**: PR 2 upload on `feature/SCRUM-81-upload`, branched from PR 1. All code is written and **uncommitted** (see Artifacts). Last run: 69 passed, 1 failed (see Next Steps 2).
- **Planned**: PR 3 scan, PR 4 download, PR 5 infra, PR 6 client. Then push all branches, open the drafts as a GitHub native stack, and comment on SCRUM-84.
- Nothing is pushed and no PR exists yet.

## Critical References

- `engineering/thoughts/shared/plans/cross-cutting/2026-11-05-SCRUM-81-documents.md`: the plan. It has the Decisions table, the Scope table, and phases 1–6, one per PR.
- `engineering/adrs/0017-s3-client.md`: why `boto3` runs in a thread, and why credentials come from boto3's own chain.
- `engineering/api/licensing_api/storage.py`: `Storage`, `create_storage`, `SCAN_TAG`.

## Decisions made with Jamie (all final)

1. **Uploads and downloads:** presigned POST straight to the bucket; presigned GET issued after the permission check. Jamie asked whether streaming through the API would be more secure; the answer was no, given the controls, and he chose direct links.
2. **GuardDuty:** SCRUM-81 provisions the Malware Protection plan, not SCRUM-84. Comment on SCRUM-84 that it moved.
3. **Scan results:** the Worker loop polls the `GuardDutyMalwareScanStatus` tag, not SQS. A document still pending after 15 minutes becomes `error`.
4. **Local scanning:** ClamAV (`clamav/clamav-debian:1.5.1`, which has arm64; `clamav/clamav` is amd64-only) plus a tagger in `engineering/mocks/malware-scanner/`. Both go in compose profile `scanner`, which is not started in CI. Tests write the tag directly.
5. **File types:** PDF, PNG, JPEG, CSV, DOCX. 20 MiB maximum.
6. **Download scope:** the plan's Scope table as proposed, reusing `notifications/recipients.py:33` `states_holding`.
7. **Events:** add `document.uploaded` and `document.scanned` to FLOW-07, owned by "history only; D-01 lists documents".
8. **FilePickerField:** polls the document's metadata until the scan finishes and shows the result.
9. **Credentials:** boto3's default chain. The S3 key settings are gone. Locally boto3 reads the standard AWS access-key variables from `engineering/api/.env`.
10. **Commits and PRs:** Jamie approved committing and opening draft PRs for this stack without asking each time.

## Recent Changes

PR 1, committed `3c2f693`:

- `engineering/api/licensing_api/storage.py` (new):
  - `presign_upload` and `presign_download`
  - async `scan_tag` and `read_start`
  - `_call`, which logs `Storage call` with `operation`, `outcome` (`ok`/`missing`/`failed`) and `duration_ms`
- `engineering/api/licensing_api/config.py`: `s3_endpoint_url`, `s3_region`, `s3_documents_bucket`.
- `engineering/api/tests/test_storage.py` (new), against RustFS; `tests/conftest.py`: a session-scoped `storage` fixture.
- `engineering/api/docker-compose.yaml`: `rustfs-init` turns on versioning and CORS (POST from `http://localhost:3000`).
- `pyproject.toml`/`uv.lock`: `boto3>=1.43.124`, dev `boto3-stubs[s3]`. README dependency rows. ADR-0017.

PR 2, uncommitted:

- `db-migrations/20261105_090000_documents_scan.sql`: `scanned_at`, `scan_checked_at`, a partial index on pending scans, and `create_history_table('documents')`.
- `licensing_api/repo/document.py`:
  - the two columns
  - `is_attached`
  - `storage_key_for(public_id)`, which returns `documents/<uuid>`
- `licensing_api/repo/document_owner.py` (new): `attach()`. It writes history only; the caller emits the event.
- `licensing_api/repo/history.py`: `DocumentHistory`, registered; `repo/__init__.py` exports it.
- `licensing_api/repo/domain_event.py`: `DOCUMENT_UPLOADED`.
  - FLOW-07 row added in `product/context/flows/07-domain-event-catalogue.md`.
  - `tests/test_event_catalogue.py` `_CONSUMED_ELSEWHERE` entry added.
- `licensing_api/errors.py`: `NotFound = 'NOT_FOUND'`.
- `licensing_api/documents.py` (new): `MAX_BYTES`, `UPLOAD_LINK_LIFETIME` (5 minutes), `DocumentType`, `EXTENSIONS`.
- `licensing_api/routes/document.py` (new): routers `me` and `states`, each with prefix `/documents`.
  - `POST` returns 201 with `Data[DocumentUpload]`.
  - `GET /{document_id}` is uploader-only for now; it returns 404 `NOT_FOUND` to anyone else.
- `licensing_api/routes/__init__.py`: mounts `document.me` under `/me` and `document.states` under `/states/{state_code}`.
- `licensing_api/dependencies.py`: `get_storage`. `__main__.py` lifespan sets `app.state.storage`.
- `tests/test_documents_upload.py` (new).

## Learnings

- **Secrets hook.** A PreToolUse secrets hook blocks any Write or Edit that assigns a value to the AWS secret-key variable or parameter, even RustFS's public local default. It blocked `storage.py` (now fixed by not passing keys at all), `.env.example`, and a first draft of this handoff. Don't try to get around it.
- **Local test command** (Jamie's machine needs `ENVIRONMENT` unset and `DB_PORT=5433`): from `engineering/api`, run `env -u ENVIRONMENT DB_PORT=5433 uv run --env-file .env.example pytest`, with the two standard AWS access-key variables exported, both set to RustFS's local key `rustfsadmin`.
- **RustFS differences from S3:**
  - A Content-Type mismatch in a POST policy gets 400 from RustFS, where S3 gives 403.
  - A missing bucket on tag reads comes back as a missing key.
  - Versioning, CORS (a wrong origin gets 403), `content-length-range`, tags and ranged GET all work. These were checked by hand.
- **Error-path tests:** use `botocore.stub.Stubber` on a fresh `create_storage(TEST_SETTINGS)`, not the shared fixture.
- **`record_guard`:** fails a route test that writes history without an event. `attach()` relies on its caller's event.
- **`test_events.py`:** keeps `_SHIPPED_EVENT_TYPES` in sync with `EventType`, so every new event must be added there.
- **No nosniff on downloads:** S3 can't add `X-Content-Type-Options` to a presigned GET. This is documented in the plan's What We're NOT Doing.
- **Overlapping PR:** #168, open, moves `rustfs-init` to a compose profile. If it merges first, merge `main` into the stack. Memory says merge, never rebase and force-push.
- **Stacks:** use GitHub native stacks. `gh pr edit --base` fails on a stacked PR. Create the stack with `POST repos/focusconsulting/pa-compact-licensing-platform/stacks` and `{"pull_requests":[bottom..top]}`.
- **gh:** prefix every `gh` command with `GH_TOKEN=$(gh auth token -u jalbinson)`.

## Artifacts

- `engineering/thoughts/shared/plans/cross-cutting/2026-11-05-SCRUM-81-documents.md`
- `engineering/adrs/0017-s3-client.md`
- `engineering/api/licensing_api/storage.py`, `config.py`, `tests/test_storage.py`, `tests/conftest.py`, `docker-compose.yaml`, `README.md`, `pyproject.toml`, `uv.lock` (PR 1)
- PR 2 (uncommitted): the files listed under Recent Changes

## Action Items & Next Steps

1. [ ] **Jamie:** in `engineering/api/.env.example` lines 57-68, rename the two S3 key variables to the standard AWS access-key ID and secret-key variable names, keeping the `rustfsadmin` values. Also update the comment: the endpoint is unset in AWS; locally the S3 client reads RustFS's keys from the standard AWS variables (ADR-0017). The hook blocks the agent from making this edit. CI (`api.yml` runs tests with `.env.example`) fails `test_storage.py` until it's done. Commit it on `feature/SCRUM-81-storage`, then merge into the branches above it.
2. [ ] **PR 2:** add `'document.uploaded'` to `_SHIPPED_EVENT_TYPES` in `engineering/api/tests/test_events.py`. That is the one failing test.
3. [ ] **PR 2:** run the full `just test-coverage` (100% required) and `just lint`.
4. [ ] **PR 2:** run `just generate` from the repo root to regenerate `engineering/api/openapi.json` and `engineering/client/src/api/schema.d.ts`; CI checks both for drift.
5. [ ] **PR 2:** docs.
   - `engineering/docs/data-model.md`: the documents columns and `documents_history`.
   - `engineering/docs/platform-contract.md` `.6`: `attach`, `get_storage`.
   - `engineering/docs/roles-and-permissions.md` if routes are listed there.
6. [ ] Commit PR 2 (plain commit, no attribution).
7. [ ] PR 3 to PR 6, per plan phases 3–6, each on `feature/SCRUM-81-<scan|download|infra|client>` branched from the previous one. Each API PR regenerates the client schema. PR 3 adds `DOCUMENT_SCANNED` (FLOW-07, `_SHIPPED_EVENT_TYPES`, `_CONSUMED_ELSEWHERE`).
8. [ ] For each branch: `/describe_pr` writes `engineering/thoughts/shared/prs/SCRUM-81-<slug>_description.md`. Push, then `gh pr create --draft --base <previous branch>`. Then create the native stack.
   - The descriptions name `boto3`, `botocore`, `s3transfer`, `jmespath`, `python-dateutil` and `urllib3` for Commission consent (SOW §7.5).
   - No Claude attribution (AGENTS.md).
9. [ ] Comment on SCRUM-84 that GuardDuty Malware Protection moved to SCRUM-81. Move SCRUM-81 to In Review when the PRs open.
10. [ ] Don't apply OpenTofu. Ask Jamie before any AWS create or apply; CI's staging plan is fine.

## Other Notes

- PR 2 has no `get_storage` override in tests: the app's lifespan builds storage from `settings`, which reads `.env.example` plus the exported AWS variables.
- In this PR the metadata GET under `/states/{state_code}` requires `WRITE`, since it is uploader-only. PR 4 changes it to `READ_PRIVATE` with the full scope.
- Routes declare `state_code` with `Path(pattern=r'^[A-Za-z]{2}$')`. This is the first `/states` route in the codebase.
