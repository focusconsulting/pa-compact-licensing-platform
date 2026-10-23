"""Calendar-day and business-day arithmetic: the one place day counts are computed (Principle XIII).

Calendar days follow ADR-0006: an instant's day is decided in the reference time
zone, and end dates are inclusive. Business days skip weekends and US federal
holidays as observed (ADR-0011).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import cache
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from licensing_api.repo.compact_settings import COMPACT_SETTINGS_ID, CompactSettings

_MONDAY, _THURSDAY, _SATURDAY, _SUNDAY = 0, 3, 5, 6


async def compact_today(session: AsyncSession) -> date:
    """Today in the reference time zone, from the same SQL function the status views use."""
    return (await session.scalars(select(func.compact_today()))).one()


async def reference_time_zone(session: AsyncSession) -> ZoneInfo:
    """The reference time zone from compact settings, in which every day is decided (ADR-0006)."""
    statement = select(col(CompactSettings.time_zone)).where(
        col(CompactSettings.id) == COMPACT_SETTINGS_ID
    )
    return ZoneInfo((await session.scalars(statement)).one())


def compact_date_at(instant: datetime, time_zone: ZoneInfo) -> date:
    """The calendar day ``instant`` falls on in ``time_zone``. Raises ``ValueError`` for a naive instant."""
    if instant.tzinfo is None:
        raise ValueError('A naive datetime has no instant; pass one with a time zone')
    return instant.astimezone(time_zone).date()


def add_days(day: date, days: int) -> date:
    """The calendar day ``days`` days after ``day`` (before it when negative)."""
    return day + timedelta(days=days)


def days_between(start: date, end: date) -> int:
    """Calendar days from ``start`` to ``end``: 0 for the same day, negative when ``end`` is earlier."""
    return (end - start).days


def is_business_day(day: date) -> bool:
    """Whether ``day`` is a weekday that is not an observed federal holiday (ADR-0011)."""
    return day.weekday() < _SATURDAY and day not in federal_holidays(day.year)


def add_business_days(day: date, days: int) -> date:
    """The business day ``days`` business days after ``day`` (before it when negative).

    ``day`` itself need not be a business day: five business days after a
    Saturday order is the following Friday.
    """
    step = 1 if days >= 0 else -1
    remaining = abs(days)
    while remaining:
        day += timedelta(days=step)
        if is_business_day(day):
            remaining -= 1
    return day


@cache
def federal_holidays(year: int) -> frozenset[date]:
    """The days federal offices close in ``year`` (5 U.S.C. 6103, observed as OPM observes them).

    A holiday on a Saturday is observed the Friday before, and on a Sunday the
    Monday after, so 1 January on a Saturday closes 31 December of the year before.
    """
    actual = _holidays_on_their_dates(year) | _holidays_on_their_dates(year + 1)
    return frozenset(observed for observed in map(_observed, actual) if observed.year == year)


def _holidays_on_their_dates(year: int) -> frozenset[date]:
    return frozenset(
        {
            date(year, 1, 1),  # New Year's Day
            _nth_weekday(year, 1, _MONDAY, 3),  # Birthday of Martin Luther King, Jr.
            _nth_weekday(year, 2, _MONDAY, 3),  # Washington's Birthday
            _last_weekday(year, 5, _MONDAY),  # Memorial Day
            date(year, 6, 19),  # Juneteenth National Independence Day
            date(year, 7, 4),  # Independence Day
            _nth_weekday(year, 9, _MONDAY, 1),  # Labor Day
            _nth_weekday(year, 10, _MONDAY, 2),  # Columbus Day
            date(year, 11, 11),  # Veterans Day
            _nth_weekday(year, 11, _THURSDAY, 4),  # Thanksgiving Day
            date(year, 12, 25),  # Christmas Day
        }
    )


def _observed(holiday: date) -> date:
    if holiday.weekday() == _SATURDAY:
        return holiday - timedelta(days=1)
    if holiday.weekday() == _SUNDAY:
        return holiday + timedelta(days=1)
    return holiday


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    next_month = date(year + month // 12, month % 12 + 1, 1)
    last = next_month - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)
