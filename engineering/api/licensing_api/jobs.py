"""Scheduled jobs: ``python -m licensing_api.jobs run <name>`` runs one, once, as its own ECS task (D8).

EventBridge Scheduler starts the task in AWS; locally, ``just job <name>`` does.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import col

from licensing_api.config import settings
from licensing_api.logging_config import configure_logging
from licensing_api.repo.base import utc_now
from licensing_api.repo.job_run import JobOutcome, JobRun

logger = logging.getLogger(__name__)

_MAX_ERROR_LENGTH = 2000

JobFn = Callable[[async_sessionmaker[AsyncSession]], Awaitable[None]]


@dataclass(frozen=True)
class Job:
    """A job the scheduler starts by ``name``. A job opens and commits its own transactions."""

    name: str
    run: JobFn


async def _heartbeat(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Does nothing: its run proves the scheduler still starts jobs, and an alarm fires when it stops."""


JOBS = (Job('heartbeat', _heartbeat),)


async def run_job(session_factory: async_sessionmaker[AsyncSession], job: Job) -> JobOutcome:
    """Run ``job`` once, recording the run in ``job_runs`` and logging its outcome, which alarms watch.

    A failure is recorded and logged, not raised; the caller turns it into the exit code.
    """
    async with session_factory() as session, session.begin():
        run = JobRun(job=job.name)
        session.add(run)
    log = {'job': job.name, 'job_run_id': run.id}
    logger.info('Job started', extra=log)
    started = time.monotonic()
    try:
        await job.run(session_factory)
    # A job may raise anything; the run is recorded as failed and the task exits non-zero.
    except Exception as error:
        await _finish(
            session_factory,
            run,
            JobOutcome.FAILED,
            error=f'{type(error).__name__}: {error}'[:_MAX_ERROR_LENGTH],
        )
        logger.exception('Job failed', extra={**log, 'outcome': JobOutcome.FAILED})
        return JobOutcome.FAILED
    await _finish(session_factory, run, JobOutcome.SUCCEEDED)
    duration_ms = round((time.monotonic() - started) * 1000)
    logger.info(
        'Job finished',
        extra={**log, 'outcome': JobOutcome.SUCCEEDED, 'duration_ms': duration_ms},
    )
    return JobOutcome.SUCCEEDED


async def _finish(
    session_factory: async_sessionmaker[AsyncSession],
    run: JobRun,
    outcome: JobOutcome,
    error: str | None = None,
) -> None:
    async with session_factory() as session, session.begin():
        await session.execute(
            update(JobRun)
            .where(col(JobRun.id) == run.id)
            .values(outcome=outcome, error=error, finished_at=utc_now())
        )


async def main(argv: Sequence[str]) -> int:
    """Run the job named in ``argv`` (``run <name>``). Returns the process exit code: 0 when it succeeded."""
    jobs = {job.name: job for job in JOBS}
    parser = argparse.ArgumentParser(prog='python -m licensing_api.jobs')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('run', help='Run one job once').add_argument('name', choices=sorted(jobs))
    args = parser.parse_args(argv)

    engine = create_async_engine(settings.db_url, pool_pre_ping=True)
    try:
        outcome = await run_job(async_sessionmaker(engine, expire_on_commit=False), jobs[args.name])
    finally:
        await engine.dispose()
    return 0 if outcome is JobOutcome.SUCCEEDED else 1


if __name__ == '__main__':
    # Run from the imported module, so log records name it rather than '__main__'.
    import licensing_api.jobs as entry_point

    configure_logging()
    sys.exit(asyncio.run(entry_point.main(sys.argv[1:])))
