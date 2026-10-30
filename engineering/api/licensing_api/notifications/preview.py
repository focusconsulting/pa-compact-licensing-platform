"""Send every email template, filled with sample data, so it can be checked in an inbox (maildev locally).

``just email-preview`` sends them all; name templates to send only those.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from licensing_api.config import Settings, settings
from licensing_api.notifications.render import render, template_environment, template_names
from licensing_api.notifications.sender import deliver

PREVIEW_RECIPIENT = 'preview@licensing.localhost'

# A context for every template, as its handler builds it.
_PA: dict[str, object] = {'first_name': 'Avery', 'state_name': 'Kansas'}
_RS: dict[str, object] = {'first_name': 'Avery', 'remote_state_name': 'Oklahoma'}
_PRIVILEGE: dict[str, object] = {'privilege_number': 'PA-OK-000042', 'expires_on': '2027-12-31'}
_ACTION: dict[str, object] = {
    'reporting_state_name': 'Oklahoma',
    'against_license': False,
    'is_emergency': False,
}
SAMPLE_CONTEXTS: dict[str, dict[str, object]] = {
    'welcome': {'first_name': 'Avery'},
    'application_submitted': _PA,
    'application_submitted_state': {'state_name': 'Kansas'},
    'application_info_requested': _PA,
    'application_resubmitted_state': {'state_name': 'Kansas'},
    'application_eligible': _PA,
    'application_denied': _PA | {'denial_reason': 'Does not hold current NCCPA certification'},
    'application_decided_commission': {'state_name': 'Kansas', 'eligible': False},
    'application_withdrawn': _PA,
    'application_withdrawn_state': {'state_name': 'Kansas'},
    'application_eligibility_withdrawn': _PA,
    'application_eligibility_withdrawn_state': {
        'state_name': 'Kansas',
        'remote_state_name': 'Oklahoma',
    },
    'privilege_requested': _RS,
    'privilege_requested_state': {'remote_state_name': 'Oklahoma'},
    'payment_declined': _RS,
    'privilege_issued': _RS | _PRIVILEGE,
    'privilege_issued_staff': {'remote_state_name': 'Oklahoma'},
    'privilege_denied': _RS | {'denial_reason': 'Does not hold current NCCPA certification'},
    'privilege_denied_staff': {'remote_state_name': 'Oklahoma'},
    'privilege_deactivated': _RS
    | {'privilege_number': 'PA-OK-000042', 'note': 'Supervision agreement lapsed.'},
    'privilege_deactivated_state': {
        'remote_state_name': 'Oklahoma',
        'privilege_number': 'PA-OK-000042',
    },
    'privilege_expiring': _RS | _PRIVILEGE,
    'privilege_expired': _RS | _PRIVILEGE,
    'license_status_changed': _PA | {'status': 'inactive'},
    'license_status_changed_state': {'state_name': 'Kansas', 'status': 'inactive'},
    'adverse_action_reported': _ACTION | {'first_name': 'Avery'},
    'adverse_action_reported_staff': _ACTION | {'is_emergency': True},
    'adverse_action_lifted': _ACTION | {'first_name': 'Avery'},
    'adverse_action_lifted_staff': _ACTION,
    'sii_flagged_state': {'reporting_state_name': 'Kansas'},
    'sii_closed_state': {'reporting_state_name': 'Kansas'},
}


def send_previews(settings: Settings, templates: Sequence[str], recipient: str) -> None:
    """Render each of ``templates`` with its sample context and send it to ``recipient``."""
    environment = template_environment()
    for template in templates:
        email = render(environment, template, SAMPLE_CONTEXTS[template], settings)
        deliver(settings, recipient, email)


def main(argv: Sequence[str]) -> int:
    """Send the templates named in ``argv``, or every one. Refuses in PROD, where it would send real email."""
    parser = argparse.ArgumentParser(prog='python -m licensing_api.notifications.preview')
    parser.add_argument('templates', nargs='*', choices=template_names(), metavar='template')
    parser.add_argument('--to', default=PREVIEW_RECIPIENT, help=f'default: {PREVIEW_RECIPIENT}')
    args = parser.parse_args(argv)
    if settings.environment == 'PROD':
        parser.error('previews are not sent in PROD')
    templates = args.templates or template_names()
    send_previews(settings, templates, args.to)
    print(f'Sent {len(templates)} preview emails to {args.to}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
