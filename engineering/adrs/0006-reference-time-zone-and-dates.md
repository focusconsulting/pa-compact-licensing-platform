---
category: architecture
status: proposed
date: 2026-10-07
---

# ADR-0006: Reference Time Zone and Dates

## Status

Proposed

## Date

2026-10-07

## Context

The compact rules count calendar days. A privilege expires on its qualifying license's expiration date (Rule 3 §3.5(a)); an incomplete application is withdrawn 60 days after it is opened (Rule 3 §3.7(a)); adverse actions are reported within five business days (Rule 4 §4.4(b)). "Which day is it?" depends on a time zone, and nothing in the rules, the SOW, or the backlog names one. Engineering constitution Principle XIII requires one reference time zone, recorded in an ADR and read from one setting.

## Decision

1. **One reference time zone**, stored in `compact_settings.time_zone`, default `America/New_York`, where the Commission and its administrator operate. It is raised with the Commission as a new question; changing it is an update to that row.
2. **`compact_date_at(instant)`** returns the calendar day an instant falls on in the reference time zone. **`compact_today()`** is `compact_date_at(now())`. No code uses the server's or the database session's time zone to decide a date.
3. **Status day arithmetic lives in the SQL status functions** that F-02 phase 3 adds (license status, privilege status, compact eligibility), each taking an `as_of DATE`. When Python needs day counts (the 60-day withdrawal job, the reporting windows), it goes through one module, added by the first ticket that needs it.
4. **End dates are inclusive.** A privilege is active on its expiration date; an adverse action is in force on its `effective_until` date (FLOW-06).
5. **Business days** need a holiday calendar. It is decided by the first ticket that counts business days (A-02's reporting windows), in this ADR's successor.

## Consequences

- A PA in Hawaii sees a privilege expire at midnight Eastern, five or six hours before their own midnight. The Commission may choose otherwise when it answers.
- Tests can check any boundary by passing an instant to `compact_date_at` or a date to the status functions, without freezing the database clock.
- `compact_today()` reads `compact_settings` on every call; the row is tiny and cached by Postgres.
