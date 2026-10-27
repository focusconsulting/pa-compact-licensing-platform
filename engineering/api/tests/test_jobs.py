"""Scheduled jobs: each run is recorded and logged with its outcome, which alarms watch (D8)."""

import logging
import re
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import col, select

from licensing_api import jobs
from licensing_api.jobs import Job, run_job
from licensing_api.repo.job_run import JobOutcome, JobRun


async def _runs(sessions: async_sessionmaker[AsyncSession]) -> list[JobRun]:
    async with sessions() as session:
        return list((await session.scalars(select(JobRun).order_by(col(JobRun.id)))).all())


async def _fail(session_factory: async_sessionmaker[AsyncSession]) -> None:
    raise RuntimeError('state feed unreachable')


async def test_a_job_that_succeeds_is_recorded_and_logged(committed_sessions, caplog):
    ran = []

    async def record(session_factory: async_sessionmaker[AsyncSession]) -> None:
        ran.append(session_factory)

    with caplog.at_level(logging.INFO, logger='licensing_api.jobs'):
        outcome = await run_job(committed_sessions, Job('tests_record', record))

    assert outcome is JobOutcome.SUCCEEDED
    assert ran == [committed_sessions]
    [run] = await _runs(committed_sessions)
    assert (run.job, run.outcome, run.error) == ('tests_record', 'succeeded', None)
    assert run.finished_at is not None and run.finished_at >= run.started_at
    started, finished = caplog.records
    assert started.__dict__['job_run_id'] == run.id
    assert (finished.__dict__['job'], finished.__dict__['outcome']) == ('tests_record', 'succeeded')
    assert finished.__dict__['duration_ms'] >= 0


async def test_a_job_that_raises_is_recorded_as_failed_and_logged_with_its_error(
    committed_sessions, caplog
):
    with caplog.at_level(logging.ERROR, logger='licensing_api.jobs'):
        outcome = await run_job(committed_sessions, Job('tests_fail', _fail))

    assert outcome is JobOutcome.FAILED
    [run] = await _runs(committed_sessions)
    assert (run.outcome, run.error) == ('failed', 'RuntimeError: state feed unreachable')
    [record] = caplog.records
    assert (record.__dict__['job'], record.__dict__['outcome']) == ('tests_fail', 'failed')
    assert record.exc_info is not None


async def test_the_command_runs_a_job_by_name_and_exits_zero(committed_sessions):
    assert await jobs.main(['run', 'heartbeat']) == 0

    [run] = await _runs(committed_sessions)
    assert (run.job, run.outcome) == ('heartbeat', 'succeeded')


async def test_the_command_exits_non_zero_when_the_job_fails(committed_sessions, monkeypatch):
    monkeypatch.setattr(jobs, 'JOBS', (Job('tests_fail', _fail),))

    assert await jobs.main(['run', 'tests_fail']) == 1


async def test_the_command_rejects_an_unknown_job(capsys):
    with pytest.raises(SystemExit) as exit_info:
        await jobs.main(['run', 'no_such_job'])

    assert exit_info.value.code == 2
    assert "invalid choice: 'no_such_job'" in capsys.readouterr().err


_SCHEDULER_TF = (
    Path(__file__).parents[2] / 'infrastructure/iac/components/app/terraform/scheduler.tf'
)


def test_every_job_has_a_schedule_in_terraform():
    schedules = re.search(r'job_schedules = \{(.*?)\n  \}', _SCHEDULER_TF.read_text(), re.DOTALL)
    assert schedules is not None, 'scheduler.tf no longer defines local.job_schedules'

    scheduled = set(re.findall(r'^\s*(\w+)\s*=', schedules.group(1), re.MULTILINE))

    assert scheduled == {job.name for job in jobs.JOBS}
