# Platform Contract

The functions every feature calls to record a change and declare a route, and the signatures the epic 2 tracks implement. Decided in [ADR-0009](../adrs/0009-route-authorization-and-change-context.md); planned in the [contract step plan](../thoughts/shared/plans/api/2026-10-14-SCRUM-77-platform-contract.md). Changing a signature here is a platform change: it needs the tech lead's review.

## Recording a change

A write validates, then changes its rows, writes a history row and an event, and commits once (constitution Principle VI). Nothing sends email or cascades inside the request: handlers do that later.

```python
before = history.snapshot(license)
license.state_reported_status = body.status
license.updated_by = ctx.user_id
await history.write(session, ctx, license, before=before)
await emit(session, ctx, EventType.QUALIFYING_LICENSE_STATUS_CHANGED, license,
           {'qualifying_license_id': license.id})
await session.commit()
```

History records changes; the audit log records access. A change to a record never writes an audit row. `audit_log.write` is for a staff read of private data or a security event:

```python
await audit_log.write(session, ctx, 'ssn.revealed', practitioner, reason=body.reason)
```

### Context

`licensing_api/context.py`

| Name | Use |
|---|---|
| `ChangeContext(user_id, request_id)` | Passed to every write helper; `user_id` goes into audit columns, history, events, and the audit log |
| `current_user` | FastAPI dependency: the active user the token belongs to, linked by email on first sign-in. Runs once per request |
| `change_context` | FastAPI dependency: the caller's context for this request |
| `system_context(session, request_id=None)` | The Worker's and jobs' context, as the system user |

Request IDs come from `RequestIdMiddleware`: the caller's `X-Request-ID` when it is a short token, otherwise a new one, returned on every response.

### Helpers

| Function | Module | Contract |
|---|---|---|
| `emit(session, ctx, event_type, aggregate, payload=None) -> DomainEvent` | `repo/domain_event.py` | Raises `OutsideTransactionError` with no open transaction. Payload values are IDs, codes, and dates, never PII. `EventType` lists FLOW-07's pilot events; adding one means adding a row there |
| `history.snapshot(entity) -> dict` | `repo/history.py` | Take before changing the entity |
| `history.write(session, ctx, entity, *, before, effective_at=None) -> HistoryRecord \| None` | `repo/history.py` | `before=None` for a new row. Writes nothing when nothing changed. Raises `ValueError` for a model with no history table |
| `audit_log.write(session, ctx, action, entity, *, before=None, after=None, reason=None) -> AuditLogEntry` | `repo/audit_log.py` | Reads of private data and security events only. `action` is `<entity>.<verb>`. `before`/`after` are for security events on rows with no history, such as a permission change. Never pass an SSN or an expunged value |
| `handler(name, *event_types)` | `events.py` | Decorator returning a frozen `Handler`; `name` is `<owning module>.<what it does>` and never changes while its deliveries exist |
| `HandlerRegistry(handlers)` | `events.py` | Built by the Worker from a constant tuple; rejects duplicate names |
| `deactivate_privileges(session, ctx, *, practitioner_id, reason, effective_at, note=None, remote_state_code=None) -> list[Privilege]` | `repo/cascade.py` | Deactivates every active privilege of the practitioner, or only those in one remote state, in the caller's transaction: status, reason, `deactivated_at` (`effective_at`), note, one history row and one `privilege.deactivated` event each. Already inactive privileges keep their first reason |
| `dispatch_events(session_factory, registry, *, batch_size=100) -> int` | `worker.py` | Fans new events out to a delivery per registered handler, then runs up to `batch_size` due deliveries, each in its own transaction ([ADR-0012](../adrs/0012-outbox-dispatcher.md)). Returns the number attempted. Tests drain the outbox by calling it |
| `notify(session, ctx, *, template, recipient_email, recipient_user_id=None, context, idempotency_key) -> Notification` | `repo/notification.py` | Queues one email as a `pending` row; the Worker sends it. A repeated key queues nothing and returns the first row. Called from handlers, not routes. Copies the address at call time |

A handler is `async def run(session, ctx, event) -> None`. The Worker's `dispatch_events` calls it with the system context and the event's request ID, inside a savepoint of a transaction it commits ([ADR-0012](../adrs/0012-outbox-dispatcher.md)): a handler never commits, and when it raises, its writes are rolled back and the delivery is retried, then dead-lettered after five attempts. A query that runs longer than 60 seconds is cancelled and counts as a failure. It must be safe to run twice for the same event, and it must cope with events out of order ([below](#handlers-and-event-order)). A handler that emails queues through `notifications.recipients.queue`, which keys each email `<event_id>:<template>:<address>`, so a retry sends once and one event can email several people.

#### Handlers and event order

Nothing makes events reach a handler in the order they were recorded, even for one aggregate. A failed delivery waits at least 30 seconds while later events are delivered, and two Workers deliver at the same time, so a handler can receive `adverse_action.lifted` before `adverse_action.reported`, or run while another handler changes the same row.

A handler that only reports what happened, such as emailing the PA that a privilege was deactivated, is unaffected: the event is the fact it reports. A handler that decides something from state is not, and is written so the order does not matter:

- **Read current state, not the payload.** The payload is what was true when the event was recorded; the row is what is true now.
- **Lock what the decision reads.** Load the rows with `with_for_update()`, so a handler acting on the same row waits instead of deciding from the same snapshot.
- **Act only while the reason holds.** When the state that justified the action has gone (the privilege is no longer active, the adverse action was lifted), return without writing. That is a successful delivery, not an error.
- **Test both orders.** Deliver the events in the order they were recorded and in reverse, and assert the same end state.

A handler that needs strict order for one aggregate cannot be built on this dispatcher; it needs a new ADR.

#### Renaming or removing an event type

Stored events keep their type forever, and the dispatcher does not run a handler for an event whose type is no longer in `EventType`: it logs `outcome=dead_lettered` and moves on. So a rename or removal takes two releases:

1. Add the new type, emit it instead of the old one, and subscribe handlers to both. The old type stays in `EventType`.
2. Once every event of the old type is delivered, remove it from `EventType` and FLOW-07, and add it to `_RETIRED_EVENT_TYPES` in `tests/test_events.py`. Ship a migration that stops the release while any are still in flight:

```sql
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM domain_events e
        WHERE e.type = '<old type>'
          AND (
              e.dispatched_at IS NULL
              OR EXISTS (
                  SELECT 1 FROM domain_event_deliveries d
                  WHERE d.event_id = e.event_id AND d.handled_at IS NULL
              )
          )
    ) THEN
        RAISE EXCEPTION '<old type> events are still being delivered';
    END IF;
END
$$;
```

A dead-lettered delivery counts as in flight: replay or delete it first.

## Declaring a route

`licensing_api/permissions.py`. Every `/api` route declares who may call it, and sits under a persona namespace (`/me`, `/public`, `/states/{state_code}`, `/commission`, `/admin`) whose rule its declaration meets; `tests/test_route_access.py` fails on one that does not. A resource router carries only its own prefix and is listed under its namespace in `licensing_api/routes/__init__.py`. What each role, permission, and namespace means is in [Roles and Permissions](roles-and-permissions.md).

```python
# applications.router, listed under '/states/{state_code}': GET /api/states/{state_code}/applications
@router.get('/applications', name=..., description=...)
async def list_applications(
    state_code: str,
    caller: Annotated[User, require(Permission.READ_PRIVATE, state_param='state_code')],
    query: Annotated[PageQuery, page_query('submitted_at', 'status', default_sort='-submitted_at')],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Paged[ApplicationOut]:
    rows, total = await paginate(session, applications_in_state(state_code), query,
                                 {'submitted_at': col(...), 'status': col(...)}, tiebreaker=col(...id))
    return Paged(data=[ApplicationOut.model_validate(r) for r in rows], page=query.page_of(total))
```

| Name | Contract |
|---|---|
| `require(permission=None, *, state_param=None)` | Yields the caller's `User` (from `current_user`). The caller passes when they hold `permission` through their role or as a grant in the route's state: the `state_param` path state, or their own. With no `permission`, any active user passes. Unknown user `403 USER_NOT_FOUND`, inactive `403 USER_INACTIVE`, missing permission `403 FORBIDDEN` |
| `public()` | For a route anyone may call, signed in or not; use in `dependencies=[...]` |
| `Permission` | What a route asks for. `manage_own_record`, `read_general`, `compact_admin`, `system_admin` come from a role; `read_private`, `read_ssn`, `write`, `admin` are granted per state in `users.permissions` (the Commission roles also hold `read_private` everywhere) |
| `ROLE_PERMISSIONS` | Each role's permissions. A role is never checked directly: change what a role may do here, not in routes |

`require` decides who may call a route, not which rows they see: a record outside the caller's scope is filtered by the route's query and returns `404` (constitution Principle II).

### Permission matrix

What each role reaches, by route family, decided in [ADR-0017](../adrs/0017-state-standing-and-relationship-scoping.md). A `/states/{st}` row applies only to a caller with **standing** in `st`: `st` is their `state_code`, or they hold a grant there. Without standing the route returns `403 FORBIDDEN`, whatever the role. **✓** means the role alone passes; **grant** means the user also needs that permission granted in the state (in `*` for a Commission user); **own** means only their own record. SCRUM-104's role × endpoint test is driven from this table.

| Route family | Declares | Rows the query returns | `licensee` | `state_staff` | `state_admin` | `compact_admin` | `admin` |
|---|---|---|---|---|---|---|---|
| `/me`: the caller's account | `require()` | The caller | ✓ | ✓ | ✓ | ✓ | ✓ |
| `/me/...`: profile, applications, privilege requests, payments | `manage_own_record` | The caller's practitioner | own | — | — | — | — |
| `/public/...`: verification, live states, fees | `public()` | Public tier only | Anyone, signed in or not | | | | |
| `/states/{st}/practitioners/...`: search, profile, history, documents | `read_general` | `related_to(st)` | — | ✓ | ✓ | — | — |
| The private fields in those responses | `read_private` in `st` | Same | — | grant | grant | — | — |
| `/states/{st}/practitioners/{id}/ssn`: reveal, audited | `read_ssn` | `related_to(st)` | — | grant | grant | — | — |
| `/states/{st}/applications`: SQL queue and case view | `read_general` | `sql_state_code = st`, out of `draft` | — | ✓ | ✓ | — | — |
| `/states/{st}/applications/{id}/...`: verify, request information, decide, withdraw eligibility | `write` | Same | — | grant | grant | — | — |
| `/states/{st}/qualifying-licenses`, `/license-ingestions`: enter, update, upload | `write` | `state_code = st` | — | grant | grant | — | — |
| `/states/{st}/privilege-requests`: remote-state queue and case view | `read_general` | `remote_state_code = st`, out of `pending_payment` | — | ✓ | ✓ | — | — |
| `/states/{st}/privilege-requests/{id}/...`, `/privileges/{id}/...`: issue, deny, change status | `write` | `remote_state_code = st` | — | grant | grant | — | — |
| `/states/{st}/adverse-actions`, `/sii-reports`: read | `read_general` | The practitioner is `related_to(st)` | — | ✓ | ✓ | — | — |
| The same: report, update, lift, close | `write` | Reported by `st` | — | grant | grant | — | — |
| `/states/{st}/settings`: fees, proofs, contacts, practice requirements | `admin` | The state itself | — | grant | grant | — | — |
| `/states/{st}/member-contacts`, `/reports`, `/dashboard` | `read_general` | The state's own figures; every member state's contacts | — | ✓ | ✓ | — | — |
| `/commission/...`: every state's records, reports, member contacts, audit log | `compact_admin` | Every state | — | — | — | ✓ | ✓ |
| `/commission/practitioners/{id}/ssn`: reveal, audited | `compact_admin`, then `read_ssn` | Every state | — | — | — | grant | — |
| `/commission/settings`, `/commission/states/{st}`, `/commission/privileges/{id}/deactivate` | `compact_admin` | Every state | — | — | — | ✓ | ✓ |
| `/admin/...` | `system_admin` | | — | — | — | — | ✓ |

A `state_admin` is given the `admin` grant for their state when their account is created; the role itself adds nothing a `state_staff` user lacks. Creating staff and changing grants is the SCRUM-105 CLI, not a route: `admin` and `compact_admin` may act in any state, and a holder of the `admin` grant in a state may act in that state.

A route that needs two permissions, such as the Commission SSN reveal, declares the namespace's permission on its router and the second on the route. A route that returns private fields only to some callers decides it with `held_permissions(caller, st)`, not with a second route.

### Relationships

`licensing_api/repo/scope.py` (SCRUM-104). Each predicate is a `ColumnElement[bool]` correlated on `practitioners.id`, for use as `select(Practitioner).where(related_to(st))` or inside an `EXISTS`. A relationship, once formed, persists: denials, withdrawals, and expiry do not end it.

| Predicate | True when |
|---|---|
| `is_sql_for(state_code)` | A participation application names the state as `sql_state_code` and has left `draft` |
| `is_remote_for(state_code)` | A privilege request names the state as `remote_state_code` and has left `pending_payment` |
| `holds_license_in(state_code)` | A qualifying license in the state is linked to the practitioner |
| `related_to(state_code)` | Any of the three: the PAs whose uniform data set the state may see (Rule 4 §4.6(a)) |

An action on one record checks that record's state column, not `related_to`. A Kansas user can read a PA whose SQL is Kansas and who holds a privilege in Missouri, but can decide only the application whose `sql_state_code` is `KS`.

### Profile fields

The uniform data set the PA enters (Rule 4 §4.3(c)(1)–(10)) is held in five groups on `practitioners`. Each group carries `<group>_entered_by`, `<group>_verified_by_state`, and `<group>_verified_at` ([data model](data-model.md#practitioners)).

| Group | Fields | Rule 4 §4.3(c) |
|---|---|---|
| `identity` | `legal_first_name`, `legal_middle_name`, `legal_last_name`, `name_suffix`, `practitioner_other_names` rows, `sex_code`, `date_of_birth`, `practitioner_ssn` | (1)–(5) |
| `residence` | `residence_line1`, `residence_line2`, `residence_city`, `residence_region`, `residence_postal_code`, `residence_country_code` | (6) |
| `contact` | `phone`, `correspondence_email` | (7)–(8) |
| `education` | `pa_program_name`, `pa_program_graduation_year` | (9) |
| `certification` | `nccpa_certification_number`, `nccpa_certification_status`, `nccpa_certification_expires_on` | (10) |

Stamps follow these rules:

- **Who stamps.** Only the state of qualifying license stamps, when it confirms identity on the case view (epic 7). It stamps every group at once, with `verified_by_state` set to the application's `sql_state_code`. That confirmation is the state's "verify and submit" of these fields.
- **Who enters.** `<group>_entered_by` is the last user who wrote the group: the PA, or staff entering on their behalf.
- **A PA edit keeps the stamp.** It writes a history row and emits `practitioner.profile_changed`. Whether a field changed since verification is read from history (`changed_at` after `<group>_verified_at`), not stored.
- **Unstamped fields.** `npi` is not in the adopted data set and is never stamped. The NCCPA lookup result (SCRUM-153) sits beside the `certification` group, with its own source and `fetched_at`; it never overwrites what the PA entered and is never stamped.
- **Change logs.** The address and email change logs (Rule 4 §4.3(e)(1)–(2)) are the `residence_*` and `correspondence_email` changes in `practitioners_history`, dated by `changed_at`. They have no table of their own.
- **Sign-in email.** `users.email` is not part of the data set. `correspondence_email` is, and email goes to it when it is set ([notifications](notifications.md)).

## Response shapes

`licensing_api/responses.py` and `licensing_api/repo/pagination.py`. Errors keep `{"code", "details"}` (`errors.py`).

| Name | Contract |
|---|---|
| `Data[T]` | `{"data": ...}` for one resource |
| `Paged[T]` | `{"data": [...], "page": {"number", "size", "total"}}` for a list |
| `page_query(*sortable, default_sort)` | Reads `?page=` (from 1), `?page_size=` (1–100, default 25), `?sort=field,-field`; an unlisted sort field is `422 VALIDATION_ERROR` |
| `paginate(session, statement, query, columns, tiebreaker) -> (rows, total)` | `columns` maps sort names to columns; `tiebreaker` is a unique column sorted last |

Every `/api` route outside `/api/health` returns `Data`, `Paged`, or no body; `tests/test_responses.py` fails one that does not. Every model a route returns carries an example (`json_schema_extra`), which the Prism mock (`just mock-api`) answers with ([ADR-0013](../adrs/0013-generated-api-client-and-mocks.md)).

## Counting days

`licensing_api/days.py` is the only place feature code counts days (constitution Principle XIII). Calendar days follow [ADR-0006](../adrs/0006-reference-time-zone-and-dates.md); business days skip weekends and federal holidays as observed ([ADR-0011](../adrs/0011-business-days-and-holiday-calendar.md)).

| Function | Contract |
|---|---|
| `compact_today(session) -> date` | Today in the reference time zone, from the same SQL function the status views use |
| `reference_time_zone(session) -> ZoneInfo` | `compact_settings.time_zone` |
| `compact_date_at(instant, time_zone) -> date` | The day an aware instant falls on; a naive datetime is a `ValueError` |
| `add_days(day, days)`, `days_between(start, end)` | Calendar days; `days_between` is 0 for the same day |
| `is_business_day(day)`, `add_business_days(day, days)` | Counting starts the day after `day`, which need not be a business day |

## Signatures the tracks implement

These are fixed here so the tracks build in parallel. Each becomes code, with tests, in the track named. Each track's plan links this page.

### `.3` events, history, audit, the privilege cascade

Implemented: `deactivate_privileges` and `dispatch_events` are in [Helpers](#helpers), the day module in [Counting days](#counting-days), and `GET /commission/audit` lists the audit log for the Commission (`compact_admin`).

### `.4` API rules, client generation, demo seed

Builds on `require`, `public`, `route_access`, `Data`, `Paged`, `page_query`, and `paginate`. Adds the persona routers (`/me`, `/public`, `/states/{state_code}`, `/commission`, `/admin`), a test that every route returns `Data`, `Paged`, or no body, the OpenAPI drift check, the generated client, the Prism mock, `just seed demo`, and moves `/me` to `Data`.

### `.5` worker and notifications

Builds on `handler`, `HandlerRegistry`, `system_context`, `notify`, and `.3`'s `dispatch_events`.

```python
# licensing_api/notifications/sender.py
async def send_pending(
    session_factory: async_sessionmaker[AsyncSession], settings: Settings, *, batch_size: int = 100,
) -> int:
    """Claim pending notifications with FOR UPDATE SKIP LOCKED, render each template, send it over
    SMTP (maildev locally, SES's SMTP interface deployed), and mark it sent or failed with the error.
    Returns the number sent."""
```

Implemented: the Worker process runs `dispatch_events` then `send_pending` until SIGTERM (`just worker`), and `python -m licensing_api.jobs run <name>` runs a scheduled job (`just job <name>`). Templates are Jinja files rendered with a test-system banner outside PROD, sent over SMTP with the standard library ([ADR-0014](../adrs/0014-email-templates-and-smtp.md)). [Notifications](notifications.md) lists which event emails whom; `tests/test_event_catalogue.py` fails an event type with no handler, named owner, or test.

### `.6` documents

Builds on `require` (download permission, with record scoping in the query), `ChangeContext`, `history.write` (documents are part of the retained record), and `audit_log.write` (a staff download of a private document is a read that is audited).

| Function | Module | Contract |
|---|---|---|
| `attach(session, ctx, document, *, owner_type, owner_id=None, owner_key=None) -> None` | `repo/document_owner.py` | Gives an unattached document to its owner in the caller's transaction and writes history; the caller emits its own event. Raises `ValueError` if the document is already attached. The caller checks its user may attach it, such as by having uploaded it |
| `get_storage` | `dependencies.py` | FastAPI dependency: the documents bucket (`Storage`), built once at start-up ([ADR-0017](../adrs/0017-s3-client.md)) |

Implemented in part: `POST /me/documents` and `POST /states/{state_code}/documents` (`write`) create a `pending` document, emit `document.uploaded`, and return a five-minute presigned POST for exactly the declared size and type (PDF, PNG, JPEG, CSV, DOCX; at most 20 MiB). `GET .../documents/{id}` returns its details to the uploader.

### Epic 5: roles, permissions, and accounts

The epic 5 tracks build against the [permission matrix](#permission-matrix), [relationships](#relationships), and [profile fields](#profile-fields) above.

- **SCRUM-104** adds the standing check and the `*` grant key to `require` and `held_permissions`, adds `repo/scope.py`, and adds the role × endpoint test.
- **SCRUM-105** adds the staff CLI. It refuses a grant outside the caller's states, and refuses `*` for anyone but a `compact_admin`.
- **SCRUM-107** adds `practitioner_other_names` and the profile routes.
