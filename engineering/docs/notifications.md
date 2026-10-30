# Notifications

Which event emails whom, and with which template. FLOW-07 ([domain event catalogue](../../product/context/flows/07-domain-event-catalogue.md)) is the source; this page is how the code carries it out.

## How email is sent

1. A request changes a record and writes a `domain_events` row in the same transaction (D2).
2. The Worker's dispatcher runs each handler registered for the event ([ADR-0012](../adrs/0012-outbox-dispatcher.md)). An email handler queues one `notifications` row per recipient with `notify`, keyed `<event_id>:<template>:<address>`, so a handler that runs twice queues nothing new.
3. The Worker's sender renders each row and sends it over SMTP: maildev locally, SES in AWS ([ADR-0014](../adrs/0014-email-templates-and-smtp.md)). A failed send is retried four times over about eight minutes, then marked `failed`, which raises an alarm.

Outside PROD, every email's subject starts with the environment, such as `[DEV]`, and the email says it comes from a test system.

## Recipients

- **The PA**: their correspondence email (Rule 4 §4.3(c)(8)), or their sign-in email when they gave none. The address is copied when the email is queued.
- **A state**: the addresses in `state_contacts` for that state and a purpose: `applications` (as state of qualifying license), `privileges` (as remote state), or `discipline`. A state with no contact for a purpose gets no email for it.
- **The Commission**: `COMMISSION_OPS_EMAIL`. The mailbox is still to be chosen ([SCRUM-178](https://focusdigital.atlassian.net/browse/SCRUM-178)); while it is empty, the Commission gets no email.

Email to states and the Commission never names the practitioner: it says what happened and links to sign-in, where the reader sees only the records their permissions allow. Email to the PA never carries a state's information-request note or anything about SII (ML §8.C).

## Catalogue

Handlers live in `licensing_api/notifications/` and are registered in `licensing_api/handlers.py`. Templates are in `licensing_api/notifications/templates/`; rendered examples of each are in `engineering/api/tests/snapshots/`.

| Event | Handler | PA | State | Commission |
|---|---|---|---|---|
| `practitioner.registered` | `send_welcome` | `welcome` | | |
| `application.submitted` | `send_application_submitted` | `application_submitted` | SQL `applications`: `application_submitted_state` | |
| `application.info_requested` | `send_application_info_requested` | `application_info_requested` (a link, never the note) | | |
| `application.resubmitted` | `send_application_resubmitted` | | SQL `applications`: `application_resubmitted_state` | |
| `application.eligible` / `.denied` | `send_application_decided` | `application_eligible` / `application_denied` (reason and appeal route) | | `application_decided_commission` |
| `application.withdrawn` | `send_application_withdrawn` | `application_withdrawn` | SQL `applications`: `application_withdrawn_state` | |
| `application.eligibility_withdrawn` | `send_eligibility_withdrawn` | `application_eligibility_withdrawn` | `privileges` of each remote state where the PA's privilege is active or was deactivated for this: `application_eligibility_withdrawn_state` | |
| `privilege.requested` | `send_privilege_requested` | `privilege_requested` (receipt) | RS `privileges`: `privilege_requested_state` | |
| `payment.declined` | `send_payment_declined` | `payment_declined` | | |
| `privilege.issued` | `send_privilege_issued` | `privilege_issued` (number and expiry) | SQL `applications`: `privilege_issued_staff` | `privilege_issued_staff` |
| `privilege.denied` | `send_privilege_denied` | `privilege_denied` (reason) | SQL `applications`: `privilege_denied_staff` | `privilege_denied_staff` |
| `privilege.deactivated` | `send_privilege_deactivated` | `privilege_deactivated` (with the state's note) | RS `privileges`: `privilege_deactivated_state` | |
| `privilege.expiring` / `.expired` | `send_privilege_expiry` | `privilege_expiring` / `privilege_expired` | | |
| `qualifying_license.status_changed` | `send_license_status_changed` | `license_status_changed` | `privileges` of each remote state whose privilege on this license is active or was deactivated by the license cascade: `license_status_changed_state` | |
| `adverse_action.reported` / `.lifted` | `send_adverse_action` | `adverse_action_reported` / `_lifted` | `discipline` of every other state where the PA holds a license or privilege: `adverse_action_reported_staff` / `_lifted_staff` | same template (Rule 5 §5.6(b)) |
| `sii.flagged` / `.closed` | `send_sii` | never (ML §8.C) | `discipline` of every other state where the PA holds a license or privilege: `sii_flagged_state` / `sii_closed_state` | |

`practitioner.profile_changed` and `practitioner.email_change_requested` send no notification: their FLOW-07 consumers are U-03's propagation and verification code. `tests/test_event_catalogue.py` fails when an event type has neither a handler nor a named owner, or no test.

Each handler's handler name is `notifications.<handler>`, which keys its delivery rows and must not change while they exist ([data model](data-model.md#domain_events-and-domain_event_deliveries)).

## Adding a notification

1. Add `<name>.txt` (blocks `subject` and `message`) and `<name>.html` (block `message`), extending `pa` or `staff`.
2. Add a sample context to `SAMPLE_CONTEXTS` in `tests/test_email_render.py` and run `UPDATE_SNAPSHOTS=1 just test tests/test_email_render.py`; review the new snapshot files.
3. Queue it from a handler with `recipients.queue`, register the handler in `licensing_api/handlers.py`, and add a row to the table above.
