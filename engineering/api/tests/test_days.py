"""Day arithmetic boundaries (Principle XIII, ADR-0006, ADR-0011)."""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from licensing_api import days

NEW_YORK = ZoneInfo('America/New_York')


async def test_today_and_the_zone_come_from_compact_settings(db_session):
    assert await days.reference_time_zone(db_session) == NEW_YORK
    database_now = (await db_session.scalars(select(func.now()))).one()

    assert await days.compact_today(db_session) == days.compact_date_at(database_now, NEW_YORK)


@pytest.mark.parametrize(
    ('instant', 'expected'),
    [
        # 23:30 on 31 October, Eastern daylight time, is already 1 November in UTC.
        (datetime(2026, 11, 1, 3, 30, tzinfo=timezone.utc), date(2026, 10, 31)),
        # Daylight saving ends at 02:00 on 1 November 2026: the day is 25 hours long.
        (datetime(2026, 11, 1, 4, 30, tzinfo=timezone.utc), date(2026, 11, 1)),
        (datetime(2026, 11, 2, 4, 30, tzinfo=timezone.utc), date(2026, 11, 1)),
        (datetime(2026, 11, 2, 5, 0, tzinfo=timezone.utc), date(2026, 11, 2)),
        # Daylight saving starts at 02:00 on 8 March 2026: the day is 23 hours long.
        (datetime(2026, 3, 9, 3, 59, tzinfo=timezone.utc), date(2026, 3, 8)),
        (datetime(2026, 3, 9, 4, 0, tzinfo=timezone.utc), date(2026, 3, 9)),
    ],
)
def test_an_instant_falls_on_its_day_in_the_reference_zone(instant, expected):
    assert days.compact_date_at(instant, NEW_YORK) == expected


def test_a_naive_datetime_is_refused():
    with pytest.raises(ValueError, match='naive'):
        days.compact_date_at(datetime(2026, 11, 1, 12), NEW_YORK)


def test_calendar_days_cross_months_and_years():
    assert days.add_days(date(2026, 12, 31), 1) == date(2027, 1, 1)
    assert days.add_days(date(2026, 3, 1), -1) == date(2026, 2, 28)
    assert days.add_days(date(2028, 3, 1), -1) == date(2028, 2, 29)
    assert days.days_between(date(2026, 10, 21), date(2026, 10, 21)) == 0
    assert days.days_between(date(2026, 10, 21), date(2026, 12, 20)) == 60
    assert days.days_between(date(2026, 10, 21), date(2026, 10, 20)) == -1


def test_federal_holidays_in_2026_as_observed():
    assert days.federal_holidays(2026) == {
        date(2026, 1, 1),
        date(2026, 1, 19),
        date(2026, 2, 16),
        date(2026, 5, 25),
        date(2026, 6, 19),
        # Independence Day falls on a Saturday.
        date(2026, 7, 3),
        date(2026, 9, 7),
        date(2026, 10, 12),
        date(2026, 11, 11),
        date(2026, 11, 26),
        date(2026, 12, 25),
    }


def test_a_saturday_new_years_day_closes_the_year_before():
    # 1 January 2028 is a Saturday.
    assert date(2027, 12, 31) in days.federal_holidays(2027)
    assert date(2028, 1, 1) not in days.federal_holidays(2028)
    assert date(2027, 12, 31) not in days.federal_holidays(2028)


def test_a_sunday_holiday_is_observed_on_monday():
    # 4 July 2027 is a Sunday; Christmas 2027 is a Saturday.
    holidays = days.federal_holidays(2027)
    assert date(2027, 7, 5) in holidays
    assert date(2027, 7, 4) not in holidays
    assert date(2027, 12, 24) in holidays


@pytest.mark.parametrize(
    ('day', 'expected'),
    [
        (date(2026, 10, 21), True),
        (date(2026, 10, 24), False),
        (date(2026, 10, 25), False),
        (date(2026, 7, 3), False),
        (date(2026, 11, 26), False),
    ],
)
def test_business_days(day, expected):
    assert days.is_business_day(day) is expected


@pytest.mark.parametrize(
    ('start', 'count', 'expected'),
    [
        # Rule 4 §4.4(b)(2): five business days after an order on a Monday.
        (date(2026, 10, 19), 5, date(2026, 10, 26)),
        # One business day after a Friday is Monday.
        (date(2026, 10, 16), 1, date(2026, 10, 19)),
        # An order on a Saturday: the count starts on Monday.
        (date(2026, 10, 17), 5, date(2026, 10, 23)),
        # Across the observed Independence Day and the weekend after it.
        (date(2026, 7, 2), 1, date(2026, 7, 6)),
        # Across Thanksgiving.
        (date(2026, 11, 25), 1, date(2026, 11, 27)),
        # Across Christmas and New Year's Day.
        (date(2026, 12, 24), 2, date(2026, 12, 29)),
        (date(2026, 12, 31), 1, date(2027, 1, 4)),
        (date(2026, 10, 19), -1, date(2026, 10, 16)),
        (date(2026, 10, 17), 0, date(2026, 10, 17)),
    ],
)
def test_adding_business_days(start, count, expected):
    assert days.add_business_days(start, count) == expected
