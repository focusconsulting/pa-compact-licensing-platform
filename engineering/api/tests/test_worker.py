"""The Worker process: runs the dispatcher until it is told to stop (D8)."""

import asyncio
import logging
import signal
import time
from collections import Counter
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from licensing_api import worker
from licensing_api.context import ChangeContext, system_context
from licensing_api.events import HandlerRegistry, handler
from licensing_api.repo.domain_event import DomainEvent, EventType, emit
from licensing_api.repo.state import State
from licensing_api.worker import run_worker
from tests.conftest import TEST_SETTINGS

_EVENTS = 1000


async def test_two_workers_drain_a_thousand_events_in_under_a_minute_handling_each_once(
    committed_sessions,
):
    async with committed_sessions() as session, session.begin():
        ctx = await system_context(session)
        state = await session.get(State, 'KS')
        assert state is not None
        for _ in range(_EVENTS):
            await emit(session, ctx, EventType.PRIVILEGE_ISSUED, state)

    handled: Counter[UUID] = Counter()
    stop = asyncio.Event()

    async def count(session: AsyncSession, ctx: ChangeContext, event: DomainEvent) -> None:
        handled[event.event_id] += 1
        if sum(handled.values()) == _EVENTS:
            stop.set()

    registry = HandlerRegistry([handler('tests.count', EventType.PRIVILEGE_ISSUED)(count)])
    started = time.monotonic()
    await asyncio.wait_for(
        asyncio.gather(
            run_worker(committed_sessions, registry, TEST_SETTINGS, stop),
            run_worker(committed_sessions, registry, TEST_SETTINGS, stop),
        ),
        timeout=60,
    )

    assert time.monotonic() - started < 60
    assert len(handled) == _EVENTS
    assert set(handled.values()) == {1}


async def test_an_idle_worker_waits_then_stops_when_asked(committed_sessions, caplog):
    stop = asyncio.Event()
    polls = 0

    async def dispatch(*args: object, **kwargs: object) -> int:
        nonlocal polls
        polls += 1
        if polls == 2:
            stop.set()
        return 0

    with (
        caplog.at_level(logging.INFO, logger='licensing_api.worker'),
        pytest.MonkeyPatch.context() as patch,
    ):
        patch.setattr(worker, 'dispatch_events', dispatch)
        started = time.monotonic()
        await run_worker(
            committed_sessions,
            HandlerRegistry([]),
            TEST_SETTINGS,
            stop,
            idle_poll_interval=timedelta(milliseconds=50),
        )

    assert polls == 2
    assert time.monotonic() - started >= 0.05
    assert [record.getMessage() for record in caplog.records] == [
        'Worker started',
        'Worker stopped',
    ]


@pytest.mark.parametrize('stop_signal', [signal.SIGTERM, signal.SIGINT])
async def test_the_worker_process_stops_on_sigterm_or_sigint(
    committed_sessions, caplog, stop_signal
):
    with caplog.at_level(logging.INFO, logger='licensing_api.worker'):
        running = asyncio.create_task(worker.main())
        while not any(record.getMessage() == 'Worker started' for record in caplog.records):
            await asyncio.sleep(0.01)
        signal.raise_signal(stop_signal)
        await asyncio.wait_for(running, timeout=5)

    assert caplog.records[-1].getMessage() == 'Worker stopped'
    # Removed on exit, so the next signal reaches the default handler again.
    assert not asyncio.get_running_loop().remove_signal_handler(stop_signal)


async def test_the_worker_sends_queued_email(committed_sessions, monkeypatch):
    sent = asyncio.Event()

    async def send(*args: object, **kwargs: object) -> int:
        if sent.is_set():
            return 0
        sent.set()
        return 1

    monkeypatch.setattr(worker, 'send_pending', send)
    stop = asyncio.Event()
    running = asyncio.create_task(
        run_worker(committed_sessions, HandlerRegistry([]), TEST_SETTINGS, stop)
    )
    await asyncio.wait_for(sent.wait(), timeout=5)
    stop.set()
    await asyncio.wait_for(running, timeout=5)
