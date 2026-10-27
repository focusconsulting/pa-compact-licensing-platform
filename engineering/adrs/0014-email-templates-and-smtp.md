---
category: architecture
status: proposed
date: 2026-10-27
---

# ADR-0014: Email Templates and SMTP

## Status

Proposed

## Date

2026-10-27

## Context

Handlers queue email as `notifications` rows with `notify` (backlog D7); nothing sends them yet. SCRUM-80 asks for the sender: HTML and text templates kept in the repo, a banner outside prod so test-system email is never mistaken for real, snapshot tests of every template, and delivery through SES deployed and maildev locally. The [platform contract](../docs/platform-contract.md) fixes the transport as SMTP, so the same code reaches maildev and SES's SMTP interface and only settings differ (Principle IV).

Two choices remain: how templates are rendered, and how the Worker, which is async, talks SMTP.

Template values include practitioner names and other text a person typed, so the HTML part must escape them. A template that refers to a value the handler forgot must fail, not send an email with a blank where the value should be.

## Decision

1. **Templates are [Jinja](https://jinja.palletsprojects.com/en/stable/) files** in `licensing_api/notifications/templates/`: `<name>.txt` defines the `subject` and `body` blocks, `<name>.html` defines `body`. Both extend a base layout that carries the footer and, outside PROD, the test-system banner; the subject gains an `[<ENVIRONMENT>]` prefix. HTML is autoescaped and `StrictUndefined` makes a missing value raise.
2. **SMTP through the standard library.** `smtplib` sends each message inside `asyncio.to_thread`, so the Worker's event loop keeps running. STARTTLS and login run when their settings are set, as they are for SES.
3. **Snapshots.** Each template is rendered with a sample context into `tests/snapshots/`; `UPDATE_SNAPSHOTS=1 just test` rewrites them, and the diff is what product reviews.

## Pros and cons

### Jinja, with `smtplib` in a thread (chosen)

- Pro: one new dependency, `jinja2` (BSD-3-Clause), with `markupsafe` (BSD-3-Clause) under it; both are maintained by Pallets and are what FastAPI's own templating uses.
- Pro: autoescaping and `StrictUndefined` close the two failure modes the context names, by configuration rather than by care.
- Pro: template inheritance puts the banner and footer in one layout, so no template can leave the banner out.
- Pro: `smtplib` is the standard library: nothing to add, and its behaviour against SES is well documented.
- Con: each send holds a thread from the default pool while the SMTP conversation runs; at the pilot's volume the pool is never the limit.
- Con: one connection per message. SES allows that; batching on one connection would add code for no measured need.

### Jinja with `aiosmtplib`

- Pro: SMTP without threads, on the Worker's event loop.
- Con: a second dependency, and a second piece of third-party material for the Commission to consent to (SOW §7.5), for no behaviour `smtplib` lacks.
- Con: fewer people know it than `smtplib`, against Principle I.

### `string.Template` and `smtplib` (no dependency)

- Pro: no dependency at all.
- Con: no escaping, so every value in every HTML template must be escaped by hand; one miss puts typed text into markup.
- Con: no inheritance and no conditionals, so the banner and footer are copied into every template or assembled in Python.
- Con: a missing value raises only with `substitute`, and nothing checks the HTML and text parts use the same values.

### SES's HTTPS API through `boto3`, with SES templates

- Pro: templates stored in SES, sent by name.
- Con: templates leave the repo, so snapshot tests and review in the PR are lost.
- Con: maildev speaks SMTP, not the SES API, so the local stack would need another mock.

## Consequences

- New API dependency: `jinja2`. Listed in the API README.
- Settings: `SMTP_HOST`, `SMTP_PORT`, `SMTP_STARTTLS`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `EMAIL_FROM_ADDRESS`, `CLIENT_BASE_URL`. In AWS, the SMTP credentials come from Secrets Manager.
- `notifications.next_attempt_at` is added (migration `20261027_100000_notification_retry.sql`). A failed send is retried after 30 seconds, doubling, and the fifth failure marks it `failed` and logs `outcome=failed`, which an alarm watches.
- Sending is at least once: if the commit after a successful send fails, the email is sent again. The idempotency key still prevents a repeated `notify` from queueing it twice.
- A handler adds a template and its sample context together; a test fails a template without one.
