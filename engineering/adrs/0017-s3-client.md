---
category: architecture
status: proposed
date: 2026-11-05
---

# ADR-0017: The S3 Client for Documents

## Status

Proposed

## Date

2026-11-05

## Context

SCRUM-81 stores uploaded documents in a private bucket (backlog D9): S3 deployed, RustFS locally, reached by the same client (Principle IV). Browsers upload and download through presigned links, so file bytes never pass through the API. What the API itself does with the bucket is small:

- sign a POST policy that fixes one key, an exact size, and a content type;
- sign a short GET that forces a download;
- read one object tag, `GuardDutyMalwareScanStatus`, which GuardDuty Malware Protection writes;
- read the first few kilobytes of a file to check its type.

Signing is local computation. Only the last two touch the network, and only from the Worker, a few times per upload. The API and the Worker are async, and `asyncpg` is the only async client in the stack; the email sender runs `smtplib` in a thread ([ADR-0014](0014-email-templates-and-smtp.md)).

## Decision

1. **`boto3`**, with each network call run in `asyncio.to_thread`. One client per process, built at start-up (`licensing_api/storage.py`); `boto3` clients are thread-safe.
2. **Credentials come from boto3's own chain**, never from settings: the ECS task role in AWS, and the standard `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` variables in `engineering/api/.env` locally, where they hold RustFS's local keys. Settings carry only `S3_ENDPOINT_URL` (unset in AWS), `S3_REGION`, and `S3_DOCUMENTS_BUCKET`.
3. **Path-style addressing** when an endpoint is set (RustFS on `localhost`), virtual-hosted in AWS.

## Pros and cons

### `boto3` with `asyncio.to_thread` (chosen)

- Pro: AWS's own SDK. `generate_presigned_post` and `generate_presigned_url` implement POST policies and SigV4 exactly as S3 checks them; nothing to get wrong by hand.
- Pro: the credential chain reads the ECS task role with no code, and refreshes it.
- Pro: the same pattern as `smtplib` in ADR-0014, so there is one way the codebase calls a blocking client.
- Pro: `boto3-stubs[s3]` (dev only) types every call for pyright.
- Con: four runtime packages: `boto3`, `botocore`, `s3transfer` (Apache-2.0), and `jmespath` (MIT), plus `python-dateutil` (Apache-2.0/BSD) and `urllib3` (MIT). Each is third-party material for the Commission to consent to (SOW §7.5).
- Con: each network call holds a thread from the default pool. The Worker makes a few per upload; the pool is never the limit.
- Con: `botocore` is a large install (about 15 MB in the image).

### `aioboto3` / `aiobotocore`

- Pro: native async calls, no threads.
- Con: wraps `botocore` with patches pinned to exact `botocore` versions, so every `boto3` security release waits on the wrapper's release.
- Con: the same packages as `boto3`, plus the wrapper and `aiohttp`: more material to consent to for no behaviour the API needs.
- Con: presigning is synchronous anyway; async buys nothing for the calls the API makes in a request.

### Hand-rolled SigV4 over `httpx` (no new dependency)

- Pro: `httpx` is already a dependency; nothing new to consent to.
- Con: POST policy encoding and SigV4 signing written and maintained by us: a security-sensitive surface where a mistake lets a browser upload outside the limits.
- Con: credential loading and refresh from the ECS task role would also be ours to write.

## Consequences

- New API dependency `boto3` and dev dependency `boto3-stubs[s3]`, listed in the API README.
- `.env.example` replaces `S3_ACCESS_KEY_ID`/`S3_SECRET_ACCESS_KEY` with `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`. A developer whose `.env` predates this copies that section again.
- Only the API's own processes (`uv run --env-file .env`) see those variables, so they never replace a developer's real AWS credentials for `just push` or `just deploy`.
- Every S3 call logs `Storage call` with `operation`, `outcome` (`ok`, `missing`, `failed`), and `duration_ms` (Principle VIII). Links are never logged.
