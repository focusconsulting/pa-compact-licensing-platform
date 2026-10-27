from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel

from licensing_api.repo.base import TimestampTZ, utc_now


class JobOutcome(StrEnum):
    """How a job run ended (``outcome``); NULL while it runs, or if its task died first."""

    SUCCEEDED = 'succeeded'
    FAILED = 'failed'


class JobRun(SQLModel, table=True):
    """One run of a scheduled job (D8). ``finished_at`` is set exactly when ``outcome`` is."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'job_runs'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    job: str
    started_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ)
    finished_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    outcome: str | None = None
    error: str | None = None
