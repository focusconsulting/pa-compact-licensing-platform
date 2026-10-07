# Data Model

The PA Compact Data System's relational data model: every table, what each column means, the rule that requires it, who may see it, and which epic owns it. Owners amend their tables with forward-only migrations without approval; a change to a shared root needs the tech lead (`product/backlog/mvp-jira-tickets.md`, "How an engineering ticket is owned").

- Conventions: [ADR-0005](../adrs/0005-data-model-conventions.md)
- Dates and the reference time zone: [ADR-0006](../adrs/0006-reference-time-zone-and-dates.md)
- SSN storage: [ADR-0007](../adrs/0007-ssn-storage.md)
- Expungement and append-only history: [ADR-0008](../adrs/0008-expungement-and-append-only-history.md)
- Plan: [F-02 base data model](../thoughts/shared/plans/api/2026-10-07-F-02-canonical-data-model.md)

Rule citations are to the adopted Rules 3 and 4 in `product/context/research-corpus/sources/` and to the model legislation (ML).

## Confidentiality tiers

| Tier | Who may see it |
|---|---|
| Public | Anyone, through public verification (Rule 4 §4.5(b)) |
| Private | The PA themselves, and state and Commission users with a relationship to the PA (`read_private`) |
| States and Commission | State and Commission users only; never the PA or the public (ML §8.C) |
| Restricted | The full SSN: `read_ssn`, every read audited (ADR-0007) |
| Internal | System bookkeeping, not shown to users |

Every table also has the audit columns `created_at`, `created_by`, `updated_at`, `updated_by` (ADR-0005), not repeated below.

## Diagram

Every table, column, and foreign key, as the migrations build them: [data-model-diagram.md](data-model-diagram.md).

## Shared roots

These belong to the platform (epic 2). Changing one needs the tech lead.

### `users`

A person who can sign in, or the system user that workers and jobs write as. Tier: internal, except `email` and names, which are private.

| Column | Type | Meaning |
|---|---|---|
| `id` | BIGSERIAL | Internal key |
| `email` | TEXT, unique | Sign-in address |
| `public_id` | UUID, unique, NULL | The Cognito `sub`; NULL until first sign-in (ADR-0003) |
| `given_name`, `family_name` | TEXT | From Cognito |
| `role` | TEXT, CHECK | `licensee`, `state_staff`, `state_admin`, `compact_admin`, `admin` (backlog D5) |
| `state_code` | CHAR(2), FK `states`, NULL | The staff member's state; NULL for `admin` and `compact_admin` |
| `is_active` | BOOLEAN | An inactive user cannot sign in |
| `permissions` | JSONB object | Per-state permissions, e.g. `{"KS": ["write", "read_private"]}` (D5) |

The system user is `system@pa-compact.invalid`: inactive, no `public_id`, its own creator.

### `compact_settings`

One row (`id = 1`) of compact-wide configuration. Tier: internal.

| Column | Type | Meaning |
|---|---|---|
| `time_zone` | TEXT | The reference time zone for every date (ADR-0006); default `America/New_York` |

Later epics add the Commission fee and similar settings here.

### `states`

Every US jurisdiction: the 50 states, DC, and five territories. Membership and go-live are configuration (Q-03). Tier: public. Owner: platform; epic 7 (S-01) edits the configuration columns.

| Column | Type | Meaning |
|---|---|---|
| `code` | CHAR(2), PK | USPS code |
| `name` | TEXT, unique | |
| `is_member` | BOOLEAN | A participating state |
| `member_effective_on` | DATE, NULL | When membership took effect |
| `is_live` | BOOLEAN | Accepting applications; only a member can be live |
| `practice_requirements_url` | TEXT, NULL | Shown to PAs choosing states (S-01) |
| `jurisprudence_requirement`, `supervision_agreement_requirement`, `prescriptive_authority_requirement`, `other_compliance_requirement` | TEXT, CHECK | `none`, `attestation`, or `proof_upload`: what the state requires before issuing (Rule 3 §3.4(c)(3)–(6)) |

### Lookup tables

Lists that wait on a Commission answer, so an answer is a data change. Each has `code` (PK), `label`, `sort_order`, and `is_active`; inactive values stay so old rows keep their meaning. Tier: public.

| Table | Values | Owner |
|---|---|---|
| `ref_sex` | Empty until Q-10 is answered | Epic 5 |
| `ref_adverse_action_types` | The examples in ML §2.A: license denial, censure, revocation, suspension, probation, monitoring, practice restriction, other | Epic 9 |
| `ref_npdb_categories` | Empty until Q-17 is answered | Epic 9 |
| `ref_denial_reasons` | Eligibility reasons from ML §4.A(1)–(8) and privilege reasons from Rule 3 §3.4(c)–(d); `applies_to` is `eligibility` or `privilege` (Q-08 default) | Epics 7 and 8 |

The `conviction` denial reason names a category, not a record; whether naming it is allowed under ML §8.B.4 is part of Q-08.

### `audit_log`

One action a person or the system took, including staff reads of private data. Append-only (ADR-0008). Tier: internal; readable by `compact_admin` and `admin`.

| Column | Type | Meaning |
|---|---|---|
| `occurred_at` | TIMESTAMPTZ | |
| `actor_user_id` | BIGINT, FK `users`, NULL | NULL only for actions with no user |
| `action` | TEXT | e.g. `ssn.revealed` |
| `entity_type`, `entity_id` | TEXT, BIGINT | What the action touched |
| `before`, `after` | JSONB, NULL | Changed values; never an SSN or an expunged value |
| `reason` | TEXT, NULL | Why, where the action requires one (an SSN reveal) |
| `request_id` | TEXT, NULL | Correlates with logs |

### `domain_events` and `domain_event_deliveries`

The transactional outbox (backlog D2): an event is written in the same transaction as the change it describes, and the worker delivers it to handlers. F-05 adds the code. Tier: internal.

`domain_events`: `event_id` (UUID, unique), `type` (listed in [FLOW-07](../../product/context/flows/07-domain-event-catalogue.md)), `aggregate_type` and `aggregate_id`, `payload` (JSONB, **IDs only, never PII**), `actor_user_id`, `request_id`, `occurred_at`.

`domain_event_deliveries`: one row per `(event_id, handler)`, with `attempts`, `last_error`, `handled_at`, and `dead_lettered_at`. Handlers are idempotent on this key.

### `notifications`

An email the worker sends (backlog D7); F-11 adds the code. Tier: private.

| Column | Type | Meaning |
|---|---|---|
| `public_id` | UUID | |
| `template` | TEXT | Template name |
| `recipient_user_id`, `recipient_email` | FK `users` NULL, TEXT | The address is copied at write time (Rule 3 §3.5(b): "the e-mail address currently on-file") |
| `context` | JSONB | Template values |
| `idempotency_key` | TEXT, unique | A repeated request sends once |
| `status` | TEXT, CHECK | `pending`, `sent`, `failed`; `sent_at` is set exactly when `sent` |

## Core entities

Every entity table has a `public_id` UUID for use outside the API, and a `<table>_history` table (ADR-0005). Two helpers in the migrations keep new tables consistent: `add_audit_columns_trigger(table)` and `create_history_table(table)`.

### `practitioners`

A PA's uniform data set (Rule 4 §4.3(c)), held by the Commission and written by several parties: the PA enters it and the state of qualifying license verifies it. Tier: private. Owner: platform (shared root).

| Column | Type | Meaning |
|---|---|---|
| `user_id` | FK `users`, unique | The PA's sign-in |
| `current_sql_state_code` | FK `states`, NULL | Set when an application becomes eligible |
| `legal_first_name`, `legal_middle_name`, `legal_last_name`, `name_suffix` | TEXT | §4.3(c)(1) |
| `sex_code` | FK `ref_sex`, NULL | §4.3(c)(3); values wait on Q-10 |
| `date_of_birth` | DATE | §4.3(c)(4) |
| `residence_*` (line1, line2, city, region, postal code, country code) | TEXT | Primary residence of record, §4.3(c)(6) |
| `phone`, `correspondence_email` | TEXT | §4.3(c)(7)–(8) |
| `pa_program_name`, `pa_program_graduation_year` | TEXT, SMALLINT | §4.3(c)(9) |
| `nccpa_certification_number`, `_status`, `_expires_on` | TEXT, TEXT, DATE | §4.3(c)(10) |
| `npi` | TEXT, NULL | Not in the adopted uniform data set; optional, never verified |
| `<group>_entered_by`, `<group>_verified_by_state`, `<group>_verified_at` | FK `users`, FK `states`, TIMESTAMPTZ | Provenance for each group: `identity`, `residence`, `contact`, `education`, `certification`. A state and a time are set together or not at all |

Other names (§4.3(c)(2)) and the address and email change log (§4.3(e)(1)–(2)) are reserved for epic 5.

### `practitioner_ssn`

One SSN per practitioner, encrypted by the application (ADR-0007). Tier: restricted. No history table: changes are audited without the value.

| Column | Type | Meaning |
|---|---|---|
| `practitioner_id` | FK, unique | |
| `ssn_ciphertext` | BYTEA | AES-256-GCM, nonce prepended |
| `ssn_key_version` | SMALLINT | Which key encrypted it |
| `ssn_lookup_hash` | BYTEA, unique | Keyed HMAC; a second account with the same SSN is rejected |
| `ssn_last4` | CHAR(4) | Four digits, shown to staff with `read_private` |

### `documents`

A file in object storage owned by one record (D9). `created_by` is the uploader. Tier: follows its owner. Owner: platform.

| Column | Type | Meaning |
|---|---|---|
| `owner_type`, `owner_id` | TEXT CHECK, BIGINT | `practitioner`, `participation_application`, `privilege_request`, `adverse_action`, `sii_report`; no foreign key |
| `kind` | TEXT | What it proves; free text until Q-07 |
| `storage_key` | TEXT, unique | S3 (RustFS locally) object key |
| `file_name`, `content_type`, `size_bytes` | | |
| `scan_status` | TEXT CHECK | `pending`, `clean`, `infected`, `error`; only `clean` may be downloaded |

### `qualifying_licenses`

A state PA license, authored by the issuing state (Rule 4 §4.3(c)(11)). Tier: the state holding it is public (Rule 4 §4.5(b)); the rest is private. Owner: epic 7.

| Column | Type | Meaning |
|---|---|---|
| `practitioner_id` | FK, NULL | NULL until linked; an uploaded license may arrive first (epic 13) |
| `state_code`, `license_number` | FK `states`, TEXT | Unique together |
| `state_reported_status` | TEXT CHECK | `active`, `expired`, `lapsed`, `inactive`, `terminated`; reinstatement returns to `active` (FLOW-05) |
| `status_effective_on` | DATE | When the reported status took effect |
| `issued_on`, `expires_on` | DATE | `issued_on` ≤ `expires_on` |
| `is_unrestricted` | BOOLEAN | Only a full and unrestricted license qualifies (Rule 3 §3.4(a)(2)) |
| `terminated_on` | DATE, NULL | Voluntary termination by the PA (Rule 3 §3.5(a), §3.6(a)) |
| `source` | TEXT CHECK | `manual`, `upload`, `api` |
| `verified_by`, `verified_at` | FK `users`, TIMESTAMPTZ | Set together |

Whether a license is in effect on a given day is computed (F-02 phase 3), not stored.

### `participation_applications`

A PA's application to participate in the compact, decided by their state of qualifying license (FLOW-02). Tier: private. Owner: epic 6.

| Column | Type | Meaning |
|---|---|---|
| `practitioner_id` | FK | |
| `kind` | TEXT CHECK | `initial` or `change_sql` (Rule 3 §3.6(a)) |
| `sql_state_code` | FK `states` | The designated state of qualifying license. There is no basis column: adopted Rule 3 §3.4(a)(2) dropped the draft's tests |
| `qualifying_license_id` | FK, NULL | |
| `status` | TEXT CHECK | `draft`, `submitted`, `info_requested`, `eligible`, `denied`, `withdrawn`, `eligibility_withdrawn` (FLOW-06) |
| `opened_at` | TIMESTAMPTZ | Received by the SQL; starts the 60-day clock (Rule 3 §3.7(a)). Required once out of `draft` |
| `request_note` | TEXT | The SQL's request for information (D15) |
| `license_verified_at`, `license_verified_by` | | Set together |
| `cbc_completed_on` | DATE | The background check's completion date; never a result (Rule 4 §4.2) |
| `decided_at`, `decided_by` | | Required for `eligible`, `denied`, `eligibility_withdrawn` |
| `denial_reason_code`, `denial_reason_detail` | FK `ref_denial_reasons`, TEXT | A code is required for `denied`; use an `eligibility` reason |
| `withdrawn_at` | TIMESTAMPTZ | Required for `withdrawn` |
| `eligibility_withdrawn_at`, `eligibility_withdrawal_reason` | | Required for `eligibility_withdrawn` (Rule 3 §3.9(b)) |

The database enforces: `eligible` needs `license_verified_at` and `cbc_completed_on` (FLOW-02); one open application (`draft`, `submitted`, `info_requested`) per practitioner. The queue index is `(sql_state_code, status)`.

### `privilege_requests`

A PA's request for a compact privilege in one remote state (FLOW-03). Tier: private. Owner: epic 8.

| Column | Type | Meaning |
|---|---|---|
| `participation_application_id`, `practitioner_id` | FKs | The eligible application it rests on |
| `remote_state_code` | FK `states` | |
| `qualifying_license_id` | FK | The license used to apply (Rule 3 §3.5(a)) |
| `status` | TEXT CHECK | `pending_payment`, `submitted`, `issued`, `denied`, `withdrawn`. `withdrawn` replaces FLOW-06's `abandoned`, per Rule 3 §3.7(b)(1) |
| `ql_expires_on_snapshot` | DATE | The license expiry in effect when the PA applied; becomes the privilege's expiry (Rule 3 §3.5(a)). Required once submitted |
| `submitted_at` | TIMESTAMPTZ | Received by the remote state (Rule 3 §3.7(b)); required once submitted |
| `decided_at`, `decided_by` | | Required for `issued` and `denied` |
| `denial_reason_code`, `denial_reason_detail` | FK `ref_denial_reasons`, TEXT | A code is required for `denied`; use a `privilege` reason |
| `withdrawn_at` | TIMESTAMPTZ | Required for `withdrawn` |

One open request (`pending_payment`, `submitted`) per practitioner and remote state. The queue index is `(remote_state_code, status)`. Per-proof verification rows are reserved for epic 8.

### `privileges`

A compact privilege issued by a remote state (Rule 4 §4.3(d)). Tier: the state, number, status, and dates are public (Rule 4 §4.5(b), Q-12); the deactivation reason and note are states and Commission. Owner: epic 8.

| Column | Type | Meaning |
|---|---|---|
| `privilege_request_id` | FK, unique | |
| `practitioner_id`, `remote_state_code`, `qualifying_license_id` | FKs | |
| `privilege_number` | TEXT, unique | `PA-{state}-{n}` |
| `state_privilege_identifier` | TEXT, NULL | The remote state's own identifier, if it issues one (Rule 4 §4.3(d)(1)) |
| `issued_at` | TIMESTAMPTZ | |
| `expires_on` | DATE | Pinned from the request; inclusive |
| `administrator_status` | TEXT CHECK | `active` or `inactive`, set by a state or the Commission |
| `deactivation_reason` | TEXT CHECK | `qualifying_license_adverse_action`, `eligibility_withdrawn`, `qualifying_license_inactive`, `qualifying_license_terminated`, `sql_changed` (Rule 3 §3.6(d)), `state_deactivated`. Set, with `deactivated_at`, exactly when `inactive` |
| `deactivation_note` | TEXT, NULL | |

The status a user sees (active, expired, encumbered, inactive) is computed (F-02 phase 3), never stored (D1).

### `adverse_actions` and `adverse_action_npdb_categories`

Discipline a state reports against a qualifying license or one privilege (Rule 4 §4.4(a)–(b)). Tier: states and Commission; public only when `is_public`. Owner: epic 9.

| Column | Type | Meaning |
|---|---|---|
| `practitioner_id`, `reporting_state_code` | FKs | |
| `against` | TEXT CHECK | `qualifying_license` or `privilege`; exactly the matching target id is set |
| `qualifying_license_id`, `privilege_id` | FKs, NULL | |
| `action_type_code` | FK `ref_adverse_action_types` | |
| `summary`, `order_document_id` | TEXT, FK `documents` | At least one: "a summary of the action taken or a copy of the order" (Rule 4 §4.4(b)(1)) |
| `ordered_on` | DATE | |
| `effective_from`, `effective_until` | DATE, DATE NULL | In force through `effective_until` inclusive, or indefinitely while it is NULL |
| `is_emergency` | BOOLEAN | Shortens the reporting window |
| `is_public` | BOOLEAN, default false | Non-public actions never reach public verification (Rule 4 §4.5(c)–(d)) |
| `reported_at` | TIMESTAMPTZ | Measures the five-business-day window (Rule 4 §4.4(b)(2)) |

`adverse_action_npdb_categories` holds optional NPDB categories, one row per category (Q-17). Updates to an action are kept in `adverse_actions_history` (Rule 4 §4.4(b)(3)). Reports a PA makes about a non-participating state are reserved for epic 9.

### `sii_reports`

A report that significant investigative information exists (Rule 4 §4.4(c)–(d)). Tier: **states and Commission only**, never the PA or the public (ML §8.C); kept apart from `adverse_actions` so no adverse-action query can return it. Owner: epic 9.

| Column | Type | Meaning |
|---|---|---|
| `practitioner_id`, `reporting_state_code` | FKs | The state of qualifying license or a remote state |
| `qualifying_license_id`, `privilege_id` | FKs, NULL | Optional link to what it concerns |
| `description` | TEXT | |
| `contact_name`, `contact_email`, `contact_phone` | TEXT | For follow-up; an email or a phone is required |
| `public_complaint_document_id` | FK `documents`, NULL | "a copy of any public complaint" (Rule 4 §4.4(d)(1)) |
| `determined_on` | DATE | Starts the five-business-day window (Rule 4 §4.4(d)(2)) |
| `reported_at` | TIMESTAMPTZ | |
| `closed_at`, `closed_by` | | Set together when the investigation closes |

### History tables

`practitioners_history`, `qualifying_licenses_history`, `participation_applications_history`, `privilege_requests_history`, `privileges_history`, `adverse_actions_history`, and `sii_reports_history`. Columns: `entity_id`, `changed_at`, `changed_by`, `effective_at`, and `previous`, `updated`, `removed` as JSONB. Append-only (ADR-0008). Tier: the same as the entity's, since history copies its values.

## Computed status

A status a rule derives is computed on read, never stored (D1). Three SQL functions are the only place status day arithmetic lives (ADR-0006). Each takes the date to evaluate; each has a view that evaluates it as of `compact_today()`. End dates are inclusive. Tier: follows the underlying record. Models: `licensing_api/repo/status.py`.

### `qualifying_license_status_on(as_of)` and `v_qualifying_license_status`

Returns `qualifying_license_id` and `status`, taking the first that applies:

1. `terminated`: the PA voluntarily terminated it on or before `as_of` (`terminated_on`).
2. The state's reported status, if not `active`: `expired`, `lapsed`, `inactive`, `terminated`.
3. `expired`: `as_of` is after `expires_on`.
4. `encumbered`: an adverse action against the license is in force.
5. `active`.

The reported status is the current one; `as_of` applies to the dates.

### `privilege_status_on(as_of)` and `v_privilege_status`

Returns `privilege_id`, `status`, and `status_reason`, taking the first that applies (ADR-0005, FLOW-06):

1. `inactive`, with the `deactivation_reason` as `status_reason`.
2. `expired`: `as_of` is after the pinned `expires_on`. Renewing the license does not change this (Rule 3 §3.5(a)).
3. `encumbered`: an adverse action against this privilege is in force.
4. `active`.

An adverse action against the qualifying license reaches privileges through the cascade that deactivates them (FLOW-05), not through this function.

### `compact_eligibility_on(as_of)` and `v_compact_eligibility`

Returns, for every practitioner, `is_barred` and `eligible_again_on` (ML §4.A.8):

- A PA is barred while an adverse action against a qualifying license is in force.
- Once it ends, the bar lasts two years from the first unrestricted day: `eligible_again_on = effective_until + 1 day + 2 years`. With several actions, the latest end wins.
- `eligible_again_on` is NULL while any such action has no end date, and for a PA never barred.
- Actions that start after `as_of`, and actions against a privilege, do not bar (FLOW-05).

## Reserved for later epics

Named here so the owning epic creates them with the conventions above. Not created yet.

| Table or columns | Owner |
|---|---|
| `fees`, `transactions`, `transaction_line_items`, privilege-request proof rows | Epic 8, privilege and payment |
| `licensure_denials` (Rule 4 §4.3(c)(14)), state administrator contacts, state fees | Epic 7, license records and SQL review |
| `ingestion_batches`, `qualifying_licenses.ingestion_batch_id` | Epic 13, state data ingestion |
| `renewal_checks`, `privileges.renewed_at` | Epic 9, status and renewal |
| `attestations` catalogue and accepted attestations | Epic 6, participation |
| `practitioner_other_names` (Rule 4 §4.3(c)(2)), address and email change log (Rule 4 §4.3(e)(1)–(2)) | Epic 5, accounts and profile |
| NCCPA lookup source and `fetched_at` | Epic 14, NCCPA |
| Adverse actions a PA reports from a non-participating state (ML §4.A(12)) | Epic 9 |
| `case_messages` | Deferred (backlog §5.1) |
