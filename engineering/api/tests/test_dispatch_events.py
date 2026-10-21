"""The dispatcher: each event reaches each handler once, failures retry, then dead-letter (ADR-0012)."""

import asyncio
import logging
import time
from collections import Counter
from uuid import UUID

from sqlalchemy import insert, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import col, select

from licensing_api.context import ChangeContext, system_context
from licensing_api.events import HandlerRegistry, handler
from licensing_api.repo.domain_event import DomainEvent, DomainEventDelivery, EventType, emit
from licensing_api.repo.notification import Notification, notify
from licensing_api.repo.state import State
from licensing_api.worker import MAX_ATTEMPTS, dispatch_events


async def _emit(
    sessions: async_sessionmaker[AsyncSession], event_type: EventType, request_id: str = 'req-1'
) -> UUID:
    async with sessions() as session, session.begin():
        ctx = await system_context(session, request_id)
        state = await session.get(State, 'KS')
        assert state is not None
        return (await emit(session, ctx, event_type, state)).event_id


async def _deliveries(sessions: async_sessionmaker[AsyncSession]) -> list[DomainEventDelivery]:
    async with sessions() as session:
        statement = select(DomainEventDelivery).order_by(col(DomainEventDelivery.handler))
        return list((await session.scalars(statement)).all())


async def _make_due(sessions: async_sessionmaker[AsyncSession]) -> None:
    async with sessions() as session, session.begin():
        await session.execute(update(DomainEventDelivery).values(next_attempt_at=text('now()')))


class Recorder:
    """A handler body that records each call, and fails while ``failures`` remain."""

    def __init__(self, failures: int = 0) -> None:
        self.calls: list[tuple[UUID, ChangeContext]] = []
        self.failures = failures

    async def __call__(self, session: AsyncSession, ctx: ChangeContext, event: DomainEvent) -> None:
        self.calls.append((event.event_id, ctx))
        if self.failures:
            self.failures -= 1
            raise RuntimeError('mail server unreachable')


async def test_each_handler_runs_once_per_event_and_a_replay_does_nothing(committed_sessions):
    issued, either, unrelated = Recorder(), Recorder(), Recorder()
    registry = HandlerRegistry(
        [
            handler('tests.issued', EventType.PRIVILEGE_ISSUED)(issued),
            handler('tests.either', EventType.PRIVILEGE_ISSUED, EventType.PRIVILEGE_DENIED)(either),
            handler('tests.unrelated', EventType.SII_CLOSED)(unrelated),
        ]
    )
    event_id = await _emit(committed_sessions, EventType.PRIVILEGE_ISSUED, request_id='req-42')

    assert await dispatch_events(committed_sessions, registry) == 2
    assert await dispatch_events(committed_sessions, registry) == 0

    assert [call[0] for call in issued.calls] == [event_id]
    assert [call[0] for call in either.calls] == [event_id]
    assert unrelated.calls == []
    async with committed_sessions() as session:
        system = await system_context(session, 'req-42')
    assert issued.calls[0][1] == system
    deliveries = await _deliveries(committed_sessions)
    assert [(d.handler, d.attempts) for d in deliveries] == [
        ('tests.either', 1),
        ('tests.issued', 1),
    ]
    assert all(d.handled_at is not None for d in deliveries)


async def test_an_event_no_handler_wants_is_marked_dispatched(committed_sessions):
    await _emit(committed_sessions, EventType.SII_CLOSED)

    assert await dispatch_events(committed_sessions, HandlerRegistry([])) == 0

    assert await _deliveries(committed_sessions) == []
    async with committed_sessions() as session:
        event = (await session.scalars(select(DomainEvent))).one()
    assert event.dispatched_at is not None


async def test_a_failing_handler_is_retried_after_a_delay(committed_sessions, caplog):
    flaky = Recorder(failures=1)
    registry = HandlerRegistry([handler('tests.flaky', EventType.PRIVILEGE_ISSUED)(flaky)])
    await _emit(committed_sessions, EventType.PRIVILEGE_ISSUED)

    with caplog.at_level(logging.WARNING, logger='licensing_api.worker'):
        assert await dispatch_events(committed_sessions, registry) == 1
    [delivery] = await _deliveries(committed_sessions)
    assert delivery.attempts == 1
    assert delivery.last_error == 'RuntimeError: mail server unreachable'
    assert delivery.handled_at is None
    assert delivery.next_attempt_at > delivery.created_at
    assert [r.__dict__['outcome'] for r in caplog.records] == ['failed']

    assert await dispatch_events(committed_sessions, registry) == 0
    await _make_due(committed_sessions)
    assert await dispatch_events(committed_sessions, registry) == 1

    [delivery] = await _deliveries(committed_sessions)
    assert (delivery.attempts, delivery.handled_at is not None) == (2, True)
    assert len(flaky.calls) == 2


async def test_a_handler_that_keeps_failing_is_dead_lettered(committed_sessions, caplog):
    broken = Recorder(failures=MAX_ATTEMPTS)
    registry = HandlerRegistry([handler('tests.broken', EventType.PRIVILEGE_ISSUED)(broken)])
    await _emit(committed_sessions, EventType.PRIVILEGE_ISSUED)

    with caplog.at_level(logging.WARNING, logger='licensing_api.worker'):
        for _ in range(MAX_ATTEMPTS):
            assert await dispatch_events(committed_sessions, registry) == 1
            await _make_due(committed_sessions)
        assert await dispatch_events(committed_sessions, registry) == 0

    [delivery] = await _deliveries(committed_sessions)
    assert delivery.attempts == MAX_ATTEMPTS
    assert delivery.dead_lettered_at is not None
    assert delivery.handled_at is None
    outcomes = [r.__dict__['outcome'] for r in caplog.records]
    assert outcomes == ['failed'] * (MAX_ATTEMPTS - 1) + ['dead_lettered']


async def test_a_failing_handler_writes_nothing(committed_sessions):
    async def queue_then_fail(session: AsyncSession, ctx: ChangeContext, event: DomainEvent):
        await notify(
            session,
            ctx,
            template='welcome',
            recipient_email='pa@example.com',
            context={},
            idempotency_key=f'{event.event_id}:tests.queue_then_fail',
        )
        raise RuntimeError('template missing')

    registry = HandlerRegistry(
        [handler('tests.queue_then_fail', EventType.PRIVILEGE_ISSUED)(queue_then_fail)]
    )
    await _emit(committed_sessions, EventType.PRIVILEGE_ISSUED)

    await dispatch_events(committed_sessions, registry)

    async with committed_sessions() as session:
        assert (await session.scalars(select(Notification))).all() == []
    [delivery] = await _deliveries(committed_sessions)
    assert delivery.attempts == 1


async def test_a_delivery_for_a_removed_handler_is_dead_lettered_at_once(committed_sessions):
    event_id = await _emit(committed_sessions, EventType.PRIVILEGE_ISSUED)
    await dispatch_events(committed_sessions, HandlerRegistry([]))
    async with committed_sessions() as session, session.begin():
        await session.execute(
            insert(DomainEventDelivery).values(event_id=event_id, handler='tests.removed')
        )

    assert await dispatch_events(committed_sessions, HandlerRegistry([])) == 1

    [delivery] = await _deliveries(committed_sessions)
    assert delivery.last_error == "No handler is registered as 'tests.removed'"
    assert delivery.dead_lettered_at is not None


async def test_two_workers_never_run_the_same_delivery(committed_sessions):
    seen: Counter[UUID] = Counter()

    async def slow(session: AsyncSession, ctx: ChangeContext, event: DomainEvent) -> None:
        seen[event.event_id] += 1
        await asyncio.sleep(0.01)

    registry = HandlerRegistry([handler('tests.slow', EventType.PRIVILEGE_ISSUED)(slow)])
    event_ids = [await _emit(committed_sessions, EventType.PRIVILEGE_ISSUED) for _ in range(20)]

    attempted = await asyncio.gather(
        dispatch_events(committed_sessions, registry),
        dispatch_events(committed_sessions, registry),
    )

    assert sum(attempted) == 20
    assert seen == Counter(event_ids)


async def test_a_thousand_events_drain_in_under_a_minute(committed_sessions):
    async def handled(session: AsyncSession, ctx: ChangeContext, event: DomainEvent) -> None:
        return None

    registry = HandlerRegistry([handler('tests.handled', EventType.PRIVILEGE_ISSUED)(handled)])
    async with committed_sessions() as session, session.begin():
        system = await system_context(session)
        await session.execute(
            insert(DomainEvent),
            [
                {
                    'type': EventType.PRIVILEGE_ISSUED,
                    'aggregate_type': 'states',
                    'aggregate_key': 'KS',
                    'actor_user_id': system.user_id,
                }
                for _ in range(1000)
            ],
        )

    started = time.monotonic()
    while await dispatch_events(committed_sessions, registry):
        pass
    elapsed = time.monotonic() - started

    deliveries = await _deliveries(committed_sessions)
    assert len(deliveries) == 1000
    assert all(d.handled_at is not None for d in deliveries)
    assert elapsed < 60
