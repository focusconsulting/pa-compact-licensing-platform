"""The Worker: delivers outbox events to their handlers (D2, D8, ADR-0012)."""

from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import func, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import col, select

from licensing_api.context import system_context
from licensing_api.events import HandlerRegistry
from licensing_api.repo.domain_event import DomainEvent, DomainEventDelivery, EventType

logger = logging.getLogger(__name__)

# A delivery that fails this many times is dead-lettered and alarmed on.
MAX_ATTEMPTS = 5
# Doubles after each failure: 30 s, 1 min, 2 min, 4 min.
FIRST_RETRY_DELAY = timedelta(seconds=30)
# Postgres cancels a handler's query that runs longer, which fails the delivery like any error.
# Not asyncio.timeout: cancelling mid-query breaks the connection, so the failure could not be recorded.
HANDLER_STATEMENT_TIMEOUT = timedelta(seconds=60)
_MAX_ERROR_LENGTH = 2000
_EVENT_TYPES = frozenset(EventType)


async def dispatch_events(
    session_factory: async_sessionmaker[AsyncSession],
    registry: HandlerRegistry,
    *,
    batch_size: int = 100,
) -> int:
    """Fan new events out to their handlers, then run up to ``batch_size`` due deliveries.

    Each delivery runs in its own transaction holding a ``SKIP LOCKED`` row lock,
    so two Workers never run the same one; the handler's writes and ``handled_at``
    commit together, and a handler that raises has its writes rolled back. Returns
    the number of deliveries attempted, successful or not. Tests drain the outbox
    by calling this.
    """
    await _fan_out(session_factory, registry, batch_size)
    attempted = 0
    while attempted < batch_size and await _deliver_one(session_factory, registry):
        attempted += 1
    return attempted


async def _fan_out(
    session_factory: async_sessionmaker[AsyncSession], registry: HandlerRegistry, batch_size: int
) -> None:
    async with session_factory() as session, session.begin():
        undispatched = (
            select(DomainEvent)
            .where(col(DomainEvent.dispatched_at).is_(None))
            .order_by(col(DomainEvent.id))
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        events = (await session.scalars(undispatched)).all()
        if not events:
            return
        deliveries = [
            {'event_id': event.event_id, 'handler': declared.name}
            for event in events
            for declared in registry.for_event(event.type)
        ]
        for event in events:
            if event.type not in _EVENT_TYPES:
                # Marked dispatched like the rest, so one bad row cannot stop fan-out.
                logger.error(
                    'Event type is not an EventType; no handler will run',
                    extra={
                        'event_id': str(event.event_id),
                        'event_type': event.type,
                        'outcome': 'dead_lettered',
                    },
                )
        if deliveries:
            await session.execute(
                insert(DomainEventDelivery).values(deliveries).on_conflict_do_nothing()
            )
        await session.execute(
            update(DomainEvent)
            .where(col(DomainEvent.id).in_([event.id for event in events]))
            .values(dispatched_at=func.now())
        )


async def _deliver_one(
    session_factory: async_sessionmaker[AsyncSession], registry: HandlerRegistry
) -> bool:
    """Run the next due delivery. False when none is due."""
    async with session_factory() as session, session.begin():
        due = (
            select(DomainEventDelivery)
            .where(
                col(DomainEventDelivery.handled_at).is_(None),
                col(DomainEventDelivery.dead_lettered_at).is_(None),
                col(DomainEventDelivery.next_attempt_at) <= func.now(),
            )
            .order_by(col(DomainEventDelivery.next_attempt_at))
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        delivery = (await session.scalars(due)).one_or_none()
        if delivery is None:
            return False
        event_query = select(DomainEvent).where(col(DomainEvent.event_id) == delivery.event_id)
        event = (await session.scalars(event_query)).one()
        log = {
            'event_id': str(event.event_id),
            'event_type': event.type,
            'handler': delivery.handler,
        }

        declared = registry.named(delivery.handler)
        attempts = delivery.attempts + 1
        if declared is None:
            await _record(
                session,
                delivery,
                attempts=attempts,
                last_error=f'No handler is registered as {delivery.handler!r}',
                dead_lettered_at=func.now(),
            )
            logger.error('Event dead-lettered', extra={**log, 'outcome': 'dead_lettered'})
            return True

        ctx = await system_context(session, event.request_id)
        timeout_ms = str(int(HANDLER_STATEMENT_TIMEOUT.total_seconds() * 1000))
        await session.execute(select(func.set_config('statement_timeout', timeout_ms, True)))
        try:
            async with session.begin_nested():
                await declared.run(session, ctx, event)
        # A handler may raise anything; the failure is recorded on the delivery and retried.
        except Exception as error:
            failure = {
                'attempts': attempts,
                'last_error': f'{type(error).__name__}: {error}'[:_MAX_ERROR_LENGTH],
            }
            if attempts >= MAX_ATTEMPTS:
                await _record(session, delivery, **failure, dead_lettered_at=func.now())
                logger.exception(
                    'Event dead-lettered',
                    extra={**log, 'attempts': attempts, 'outcome': 'dead_lettered'},
                )
            else:
                delay = FIRST_RETRY_DELAY * 2 ** (attempts - 1)
                await _record(session, delivery, **failure, next_attempt_at=func.now() + delay)
                logger.warning(
                    'Event handler failed',
                    exc_info=True,
                    extra={**log, 'attempts': attempts, 'outcome': 'failed'},
                )
            return True

        await _record(session, delivery, attempts=attempts, handled_at=func.now())
        logger.info('Event handled', extra={**log, 'outcome': 'handled'})
        return True


async def _record(session: AsyncSession, delivery: DomainEventDelivery, **values: object) -> None:
    await session.execute(
        update(DomainEventDelivery)
        .where(
            col(DomainEventDelivery.event_id) == delivery.event_id,
            col(DomainEventDelivery.handler) == delivery.handler,
        )
        .values(**values)
    )
