---
category: architecture
status: proposed
date: 2026-10-21
---

# ADR-0011: Business Days and the Holiday Calendar

## Status

Proposed. Succeeds point 5 of [ADR-0006](0006-reference-time-zone-and-dates.md). The Commission confirms the calendar through a new open question.

## Date

2026-10-21

## Context

The compact rules count business days: an adverse action is reported within five business days of the order, one for a summary or emergency action (Rule 4 §4.4(b)(2)); significant investigative information within five (Rule 4 §4.4(d)(2)); an expungement within ten (Rule 4 §4.2(f)). None of them says which days are not business days. Principle XIII requires one holiday calendar, recorded in an ADR, and one module for day arithmetic.

The Commission is a multi-state body whose administrator follows the federal calendar; participating states each close on different state holidays.

## Decision

1. **A business day is a weekday that is not a US federal holiday as observed**: the eleven holidays of 5 U.S.C. 6103, moved to the Friday before when they fall on a Saturday and the Monday after when they fall on a Sunday, as OPM observes them. 1 January on a Saturday closes 31 December of the year before.
2. **Computed, not listed.** `licensing_api/days.py` derives each year's holidays from the statute's rules, so no table needs a yearly update. A change in the statute is a code change.
3. **Business days are counted in the reference time zone's calendar** (ADR-0006): the day an order is taken is decided there, and counting starts on the next day.
4. **State holidays are not observed.** A deadline that a state's own holiday would extend is not extended.

## Alternatives

- **The `holidays` package** (PyPI): covers every country and US state. Rejected: a dependency, with its ADR and the Commission's consent, for eleven rules that fit in one function, and its state calendars are the part this decision does not use.
- **A holiday table in the database**: lets the Commission add a closure without a release. Rejected for now: someone must load each year, and a missing year silently shortens every deadline. It remains the path if the Commission wants ad-hoc closures.
- **Each state's own calendar**: what a state's staff would expect. Rejected: a report crosses states, the rules set one deadline, and the dashboard (C-01) compares states on the same clock.

## Consequences

- Deadlines may land on a state holiday; the state reports a day early or is shown late.
- An emergency action ordered on a Friday before a Monday federal holiday is due the Tuesday after.
- If the Commission chooses another calendar, only `days.py` and this ADR change.
