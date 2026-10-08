---
category: architecture
status: proposed
date: 2026-10-07
---

# ADR-0007: SSN Storage

## Status

Proposed

## Date

2026-10-07

## Context

Rule 3 §3.3(a)(5) requires a "unique identifier that is a social security number", and the uniform data set includes it (Rule 4 §4.3(c)(5)). The SSN is the most sensitive field the system holds: the constitution's Security Requirements put it in the restricted tier, shown as the last four digits, with a full reveal needing the `read_ssn` permission and an audit record. The backlog's decision D10 defaulted to pgcrypto with a KMS-wrapped key. Two needs shape the design: no one should be able to read SSNs from the database, its backups, or its logs without the key; and the system must detect a second account with the same SSN.

## Decision

1. SSNs live only in **`practitioner_ssn`**, one row per practitioner, created in F-02 phase 2.
2. The **application encrypts** the SSN with AES-256-GCM before it reaches the database, storing `ssn_ciphertext` (nonce prepended) and `ssn_key_version`. The key never travels to Postgres, so it cannot appear in query logs or `pg_stat_statements`. This supersedes D10's pgcrypto default for that reason.
3. A **keyed hash** (`ssn_lookup_hash`, HMAC-SHA-256 with a second key) is unique, so a duplicate SSN is detected without decrypting anything. An unkeyed hash would be brute-forceable over the small SSN space.
4. **`ssn_last4`** is stored in clear for display.
5. **Keys** come from AWS Secrets Manager in deployed environments and from `.env` locally, read through the same settings and code path (Principle IV). `ssn_key_version` allows rotation: new writes use the newest key, and old rows are re-encrypted by a job.
6. A **full read** requires `read_ssn` and writes an `audit_log` row that names the practitioner and the reason, never the value. SSN changes are audited the same way; `practitioner_ssn` has no history table, so ciphertext is not copied.
7. `ssn` is masked in structured logs.

## Consequences

- Losing a key makes the SSNs encrypted with it unrecoverable. Keys are versioned in Secrets Manager and their rotation is a runbook entry.
- Searching by full SSN means computing the keyed hash in the app and looking it up; there is no SQL search on the plaintext.
- The encryption helper is built by U-03 (PA profile), which first writes SSNs. It adds the two key settings to `.env.example` with local values.
