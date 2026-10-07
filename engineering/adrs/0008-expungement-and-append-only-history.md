---
category: architecture
status: proposed
date: 2026-10-07
---

# ADR-0008: Expungement and Append-Only History

## Status

Proposed

## Date

2026-10-07

## Context

Engineering constitution Principle VI makes the record the audit trail: every change is kept in history tables and the audit log. Rule 4 §4.2(f) requires the opposite in one case: "Any information submitted to the Data System that is subsequently expunged pursuant to federal law or the laws of the Participating State contributing the information shall be removed from the Data System as soon as reasonably possible, but no later than ten business days". If history is truly immutable, expunged information survives in it.

## Decision

1. History tables and `audit_log` are **append-only**. The `prevent_mutation()` trigger rejects `UPDATE` and `DELETE` on them.
2. The one exception is a transaction that has run `SET LOCAL app.expunge = 'on'`. Only the expungement command does this.
3. The **expungement command** (a later ticket) takes the contributing state, the records and fields to expunge, and the legal basis. In one transaction it replaces the expunged values with `{"redacted": true}` in the base rows and every history row that holds them, and writes one `audit_log` row naming the fields, the requesting state, and the basis. It never records the expunged values.
4. Expungement redacts; it does not delete rows. Keys and timestamps remain, so the record shows that something was removed and when.

## Consequences

- Day-to-day code cannot rewrite history, even by mistake; the database refuses.
- How expungement requests arrive from states (a form, an email to Commission staff, an API) is a new question for the Commission. Until it is answered, the command is run by an administrator.
- `SET LOCAL` limits the exception to one transaction. A connection pool cannot leak it to another request.
