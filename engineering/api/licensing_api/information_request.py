"""When a state of qualifying license asked a PA for more, and the last day it must have the answer.

The request's time is read from history, never stored: the application's history row that moved
it to ``info_requested``. The deadline counts from the application, not the request (Rule 3 §3.7(a)(1)).
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.days import add_days, compact_date_at
from licensing_api.repo.history import ParticipationApplicationHistory
from licensing_api.repo.participation_application import ApplicationStatus

RESUBMIT_WITHIN_DAYS = 60


def resubmit_by(opened_at: datetime, time_zone: ZoneInfo) -> date:
    """The last day the state must have the PA's answer: 60 days after the day it received the application."""
    return add_days(compact_date_at(opened_at, time_zone), RESUBMIT_WITHIN_DAYS)


async def requested_at(session: AsyncSession, application_id: int) -> datetime | None:
    """When the state last asked for information on this application, or None if it never has."""
    statement = (
        select(col(ParticipationApplicationHistory.changed_at))
        .where(
            col(ParticipationApplicationHistory.entity_id) == application_id,
            col(ParticipationApplicationHistory.updated)['status'].astext
            == ApplicationStatus.INFO_REQUESTED,
        )
        .order_by(
            col(ParticipationApplicationHistory.changed_at).desc(),
            col(ParticipationApplicationHistory.id).desc(),
        )
        .limit(1)
    )
    return (await session.scalars(statement)).one_or_none()
