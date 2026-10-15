# Platform Contract

The functions every feature calls to record a change and declare a route, and the signatures the epic 2 tracks implement. Decided in [ADR-0009](../adrs/0009-route-authorization-and-change-context.md); planned in the [contract step plan](../thoughts/shared/plans/api/2026-10-14-bd-4gi.2-platform-contract.md). Changing a signature here is a platform change: it needs the tech lead's review.

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
| `notify(session, ctx, *, template, recipient_email, recipient_user_id=None, context, idempotency_key) -> Notification` | `repo/notification.py` | Queues one email as a `pending` row; the Worker sends it. A repeated key queues nothing and returns the first row. Called from handlers, not routes. Copies the address at call time |

A handler is `async def run(session, ctx, event) -> None`. It is called with the system context and the event's request ID, and must be safe to run twice for the same event. A handler that emails uses `<event_id>:<handler name>` as the idempotency key, so a retry sends once.

## Declaring a route

`licensing_api/permissions.py`. Every `/api` route declares who may call it; `tests/test_route_access.py` fails on one that does not.

```python
@router.get('/states/{state_code}/applications', name=..., description=...)
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
| `Permission` | What a route asks for. `manage_own_record`, `read_general`, `compact_admin` come from a role; `read_private`, `read_ssn`, `write`, `admin` are granted per state in `users.permissions` (the Commission roles also hold `read_private` everywhere) |
| `ROLE_PERMISSIONS` | Each role's permissions. A role is never checked directly: change what a role may do here, not in routes |

`require` decides who may call a route, not which rows they see: a record outside the caller's scope is filtered by the route's query and returns `404` (constitution Principle II).

## Response shapes

`licensing_api/responses.py` and `licensing_api/repo/pagination.py`. Errors keep `{"code", "details"}` (`errors.py`).

| Name | Contract |
|---|---|
| `Data[T]` | `{"data": ...}` for one resource |
| `Paged[T]` | `{"data": [...], "page": {"number", "size", "total"}}` for a list |
| `page_query(*sortable, default_sort)` | Reads `?page=` (from 1), `?page_size=` (1–100, default 25), `?sort=field,-field`; an unlisted sort field is `422 VALIDATION_ERROR` |
| `paginate(session, statement, query, columns, tiebreaker) -> (rows, total)` | `columns` maps sort names to columns; `tiebreaker` is a unique column sorted last |

`/me` still returns its body unwrapped: the deployed client reads that shape, and `.4` moves it to `Data` with the regenerated client.

## Signatures the tracks implement

These are fixed here so the tracks build in parallel. Each becomes code, with tests, in the track named. Each track's plan links this page.

### `.3` events, history, audit, the privilege cascade

```python
# licensing_api/repo/privilege.py
async def deactivate_privileges(
    session: AsyncSession, ctx: ChangeContext, *, practitioner_id: int, reason: DeactivationReason,
    effective_at: datetime, note: str | None = None, remote_state_code: str | None = None,
) -> list[Privilege]:
    """Deactivate every active privilege of the practitioner, or only those in one remote state, in the
    caller's transaction: sets administrator_status, deactivation_reason, deactivated_at, and the note,
    with one history row and one ``privilege.deactivated`` event per privilege. The notification to
    the PA comes from that event's handler."""

# licensing_api/worker.py
async def dispatch_events(
    session_factory: async_sessionmaker[AsyncSession], registry: HandlerRegistry, *, batch_size: int = 100,
) -> int:
    """Claim undelivered (event, handler) pairs with FOR UPDATE SKIP LOCKED, run each in its own
    transaction, and record the outcome in domain_event_deliveries; retry, then dead-letter.
    Returns the number handled. Tests drain the outbox by calling it."""
```

Also `.3`: the event-catalogue test (every `EventType` has a test), `GET /commission/audit`, and the day-arithmetic module (ADR-0006).

### `.4` API rules, client generation, demo seed

Builds on `require`, `public`, `route_access`, `Data`, `Paged`, `page_query`, and `paginate`. Adds the persona routers (`/me`, `/public`, `/states/{state_code}`, `/commission`, `/admin`), a test that every route returns `Data`, `Paged`, or no body, the OpenAPI drift check, the generated client and mocks, `just seed demo`, and moves `/me` to `Data`.

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

### `.6` documents

Builds on `require` (download permission, with record scoping in the query), `ChangeContext`, `history.write` (documents are part of the retained record), and `audit_log.write` (a staff download of a private document is a read that is audited).
