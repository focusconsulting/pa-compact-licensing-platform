# Platform Contract

The functions every feature calls to record a change, and the signatures the epic 2 tracks implement. Decided in [ADR-0009](../adrs/0009-route-authorization-and-change-context.md); planned in the [contract step plan](../thoughts/shared/plans/api/2026-10-14-bd-4gi.2-platform-contract.md). Changing a signature here is a platform change: it needs the tech lead's review.

## Recording a change

A write validates, then changes its rows, writes history, audit, and an event, and commits once (constitution Principle VI). Nothing sends email or cascades inside the request: handlers do that later.

```python
before = history.snapshot(license)
license.state_reported_status = body.status
stamp_update(license, ctx)
await history.write(session, ctx, license, before=before)
await audit_log.write(session, ctx, 'qualifying_license.status_changed', license,
                      before={'state_reported_status': before['state_reported_status']},
                      after={'state_reported_status': body.status})
await emit(session, ctx, EventType.QUALIFYING_LICENSE_STATUS_CHANGED, license,
           {'qualifying_license_id': license.id})
await session.commit()
```

### Context

`licensing_api/context.py`

| Name | Use |
|---|---|
| `ChangeContext(actor, request_id)` | Passed to every write helper |
| `change_context` | FastAPI dependency: the caller's context for this request |
| `system_context(request_id=None)` | The Worker's and jobs' context, as the system user |
| `actor_id(actor)` | `users.id` as a subquery, for an audit column set in a statement |
| `stamp_update(entity, ctx)` | Sets `updated_by` on a changed row; refresh before reading it back |

Request IDs come from `RequestIdMiddleware`: the caller's `X-Request-ID` when it is a short token, otherwise a new one, returned on every response.

### Helpers

| Function | Module | Contract |
|---|---|---|
| `emit(session, ctx, event_type, aggregate, payload=None) -> DomainEvent` | `repo/domain_event.py` | Raises `OutsideTransactionError` with no open transaction. Payload values are IDs, codes, and dates, never PII. `EventType` lists FLOW-07's pilot events; adding one means adding a row there |
| `history.snapshot(entity) -> dict` | `repo/history.py` | Take before changing the entity |
| `history.write(session, ctx, entity, *, before, effective_at=None) -> HistoryRecord \| None` | `repo/history.py` | `before=None` for a new row. Writes nothing when nothing changed. Raises `ValueError` for a model with no history table |
| `audit_log.write(session, ctx, action, entity, *, before=None, after=None, reason=None) -> AuditLogEntry` | `repo/audit_log.py` | `action` is `<entity>.<verb>`. Never pass an SSN or an expunged value |
| `handler(name, *event_types)` | `events.py` | Decorator returning a frozen `Handler`; `name` is `<owning module>.<what it does>` and never changes while its deliveries exist |
| `HandlerRegistry(handlers)` | `events.py` | Built by the Worker from a constant tuple; rejects duplicate names |

A handler is `async def run(session, ctx, event) -> None`. It is called with the system context and the event's request ID, and must be safe to run twice for the same event.

## Signatures the tracks implement

These are fixed here so the tracks build in parallel. Each becomes code, with tests, in the track named.

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
