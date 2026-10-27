"""Email templates: subject, text, and HTML from one name, with a test-system banner outside PROD (ADR-0014)."""

from pathlib import Path

import pytest
from jinja2 import TemplateNotFound, UndefinedError

from licensing_api.notifications.render import (
    TEMPLATES_DIR,
    long_date,
    render,
    template_environment,
    template_names,
)
from tests.conftest import TEST_SETTINGS
from tests.snapshots import assert_matches_snapshot

TEST_TEMPLATES_DIR = Path(__file__).parent / 'email_templates'

# A context for every template in licensing_api/notifications/templates, as its handler builds it.
_PA = {'first_name': 'Avery', 'state_name': 'Kansas'}
_RS = {'first_name': 'Avery', 'remote_state_name': 'Oklahoma'}
_PRIVILEGE = {'privilege_number': 'PA-OK-000042', 'expires_on': '2027-12-31'}
_ACTION = {'reporting_state_name': 'Oklahoma', 'against_license': False, 'is_emergency': False}
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

_EXAMPLE_CONTEXT = {
    'state_name': 'Kansas',
    'practitioner_name': 'Avery Active',
    'application_id': 7,
}


def _environment():
    return template_environment((TEST_TEMPLATES_DIR, TEMPLATES_DIR))


def test_every_template_has_a_sample_context():
    assert template_names() == sorted(SAMPLE_CONTEXTS)


@pytest.mark.parametrize('template', template_names())
def test_every_template_matches_its_snapshot(template):
    email = render(template_environment(), template, SAMPLE_CONTEXTS[template], TEST_SETTINGS)

    assert_matches_snapshot(f'{template}.subject.txt', email.subject + '\n')
    assert_matches_snapshot(f'{template}.txt', email.text)
    assert_matches_snapshot(f'{template}.html', email.html)


def test_layouts_are_not_templates_that_can_be_sent():
    assert template_names(TEST_TEMPLATES_DIR) == ['example']
    assert 'base' not in template_names()


def test_outside_prod_the_subject_and_body_say_it_is_a_test_system():
    email = render(_environment(), 'example', _EXAMPLE_CONTEXT, TEST_SETTINGS)

    assert email.subject == '[LOCAL_DEV] Your application to Kansas was received'
    assert_matches_snapshot('example.txt', email.text)
    assert_matches_snapshot('example.html', email.html)


def test_in_prod_there_is_no_banner():
    prod = TEST_SETTINGS.model_copy(update={'environment': 'PROD'})

    email = render(_environment(), 'example', _EXAMPLE_CONTEXT, prod)

    assert email.subject == 'Your application to Kansas was received'
    assert 'test system' not in email.text
    assert 'test system' not in email.html


def test_links_use_the_client_origin_without_a_doubled_slash():
    settings = TEST_SETTINGS.model_copy(update={'client_base_url': 'https://pa.example.gov/'})

    email = render(_environment(), 'example', _EXAMPLE_CONTEXT, settings)

    assert 'https://pa.example.gov/applications/7' in email.text
    assert 'href="https://pa.example.gov/applications/7"' in email.html


def test_values_are_escaped_in_html_but_not_in_text():
    context = {**_EXAMPLE_CONTEXT, 'practitioner_name': '<b>Avery</b> & Co'}

    email = render(_environment(), 'example', context, TEST_SETTINGS)

    assert 'Hello &lt;b&gt;Avery&lt;/b&gt; &amp; Co' in email.html
    assert 'Hello <b>Avery</b> & Co' in email.text


def test_a_missing_value_raises_rather_than_rendering_blank():
    with pytest.raises(UndefinedError, match='practitioner_name'):
        render(
            _environment(), 'example', {'state_name': 'Kansas', 'application_id': 7}, TEST_SETTINGS
        )


def test_an_unknown_template_raises():
    with pytest.raises(TemplateNotFound):
        render(_environment(), 'no_such_template', {}, TEST_SETTINGS)


def test_dates_read_as_words():
    assert long_date('2027-12-01') == 'December 1, 2027'
