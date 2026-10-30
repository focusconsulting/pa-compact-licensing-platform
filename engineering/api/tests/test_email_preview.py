"""just email-preview: every template, with sample data, lands in maildev for QA (SCRUM-179)."""

import pytest

from licensing_api.notifications import preview
from licensing_api.notifications.preview import PREVIEW_RECIPIENT, main
from licensing_api.notifications.render import template_names
from tests.conftest import TEST_SETTINGS, received_emails


@pytest.fixture(autouse=True)
def _test_settings(monkeypatch):
    monkeypatch.setattr(preview, 'settings', TEST_SETTINGS)


def test_with_no_names_every_template_is_sent_to_the_preview_mailbox(maildev, capsys):
    assert main([]) == 0

    emails = received_emails(maildev)
    assert len(emails) == len(template_names())
    assert {to['address'] for email in emails for to in email['to']} == {PREVIEW_RECIPIENT}
    assert '[LOCAL_DEV] Your PA Compact account is ready' in {email['subject'] for email in emails}
    assert capsys.readouterr().out == (
        f'Sent {len(template_names())} preview emails to {PREVIEW_RECIPIENT}\n'
    )


def test_named_templates_go_to_the_given_address(maildev):
    main(['welcome', 'privilege_issued', '--to', 'qa@demo.example'])

    emails = received_emails(maildev)
    assert sorted(email['subject'] for email in emails) == [
        '[LOCAL_DEV] Your PA Compact account is ready',
        '[LOCAL_DEV] Your privilege to practice in Oklahoma is active',
    ]
    assert {to['address'] for email in emails for to in email['to']} == {'qa@demo.example'}


def test_an_unknown_template_is_refused(maildev):
    with pytest.raises(SystemExit):
        main(['no_such_template'])

    assert received_emails(maildev) == []


def test_nothing_is_sent_in_prod(monkeypatch, maildev):
    monkeypatch.setattr(
        preview, 'settings', TEST_SETTINGS.model_copy(update={'environment': 'PROD'})
    )

    with pytest.raises(SystemExit):
        main([])

    assert received_emails(maildev) == []
