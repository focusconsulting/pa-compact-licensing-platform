---
category: architecture
status: proposed
date: 2026-10-21
---

# ADR-0012: Outbox Dispatcher

## Status

Proposed

## Date

2026-10-21

## Context

Every write records a `domain_events` row in its own transaction (backlog D2, constitution Principle VI). Something must deliver each event to its handlers (emails, metrics) exactly once per handler, retry a handler that fails, dead-letter one that keeps failing, and let two Worker tasks run without handling the same event twice (F-05 acceptance criteria). SCRUM-78 asks this ADR to choose between building the dispatcher on the tables F-02 created and adopting a Postgres queue library such as [pgqueuer](https://github.com/janbjorge/pgqueuer).

The tables already exist: `domain_events` (the outbox) and `domain_event_deliveries`, one row per event and handler, keyed `(event_id, handler)`.

## Decision

Build the dispatcher on the existing tables, as `dispatch_events` in `licensing_api/worker.py`:

1. **Fan-out.** Claim events with no `dispatched_at` (`FOR UPDATE SKIP LOCKED`), insert a delivery row for each handler registered for the event's type, and stamp `dispatched_at`, in one transaction. A handler registered later does not receive earlier events.
2. **Delivery.** Each delivery runs in its own transaction: claim one due row (`SKIP LOCKED`), run the handler inside a savepoint as the system user with the event's request ID, and set `handled_at`. The handler's writes and `handled_at` commit together, so a crash between them cannot send twice.
3. **Failure.** The savepoint rolls back the handler's writes; the delivery records the attempt and error and waits 30 seconds, doubling each time. The fifth failure dead-letters it and logs `outcome=dead_lettered`, which an alarm watches (F-13). A delivery whose handler has been removed dead-letters at once.
4. **No inline mode.** Tests call `dispatch_events` to drain the outbox; no setting runs handlers inside a request (Principle IV).

## Pros and cons

### Build on the existing tables (chosen)

- Pro: no dependency, no ADR for one, and no third-party material for the Commission to consent to (SOW §7.5).
- Pro: the handler's writes, its delivery row, and the event share one database and one transaction; idempotency on `(event_id, handler)` is a primary key, not a convention.
- Pro: the tables, the history, and the data dictionary F-02 shipped stay the single description of the outbox.
- Pro: about 150 lines a reader can follow with SQLAlchemy alone (Principle I).
- Con: retry, backoff, and dead-letter are ours to test and maintain.
- Con: polling. An idle Worker queries every few seconds instead of waking on `LISTEN/NOTIFY`; at pilot volume this is negligible.

### pgqueuer

- Pro: maintained queueing on Postgres with `LISTEN/NOTIFY` wake-ups, retries, scheduling, and a dashboard.
- Pro: its scheduler could replace EventBridge Scheduler for cron jobs.
- Con: a dependency and a second schema: its own queue tables beside `domain_events`, so an event and its queue entry are two rows to keep consistent, or the outbox is rebuilt on its tables.
- Con: its job model is "one job, one consumer"; fanning one event out to several idempotent handlers is still ours to build.
- Con: it runs its own async driver and connection handling beside SQLAlchemy's, a second way to reach the database (Principle I).
- Con: moving cron into the Worker removes the run-task isolation and alarms D8 chose.

### A managed queue (SQS, EventBridge)

- Pro: no polling; AWS handles retries and dead-letter queues.
- Con: the outbox still needs a relay from Postgres to the queue, so the problem moves rather than disappears.
- Con: locally it needs another mock in Docker Compose, and tests could no longer drain events by calling one function.

## Consequences

- `domain_events.dispatched_at` and `domain_event_deliveries.next_attempt_at` are added (migration `20261021_090000_event_dispatch.sql`).
- A handler must not commit; the dispatcher commits for it.
- A delivery is retried for about eight minutes before it dead-letters. A dead-lettered delivery is replayed by clearing its `dead_lettered_at` and `attempts`.
