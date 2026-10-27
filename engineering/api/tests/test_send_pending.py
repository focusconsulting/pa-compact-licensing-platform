"""send_pending: each queued email goes out once through SMTP (maildev here), failures retry, then fail (D7)."""

import asyncio
import logging
import os
from collections.abc import Generator
from datetime import UTC, datetime
from email.message import EmailMessage

import httpx
import pytest
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import col, select

from licensing_api.config import Settings
from licensing_api.context import system_context
from licensing_api.notifications import sender
from licensing_api.notifications.render import TEMPLATES_DIR, RenderedEmail, template_environment
from licensing_api.notifications.sender import MAX_ATTEMPTS, send_pending
from licensing_api.repo.notification import Notification, NotificationStatus, notify
from tests.conftest import TEST_SETTINGS
from tests.test_email_render import TEST_TEMPLATES_DIR

_MAILDEV = f'http://localhost:{os.environ.get("MAILDEV_UI_PORT", "1080")}'
_CONTEXT = {'state_name': 'Kansas', 'practitioner_name': 'Avery Active', 'application_id': 7}


@pytest.fixture
def maildev() -> Generator[httpx.Client]:
    """maildev's REST API, emptied before the test."""
    with httpx.Client(base_url=_MAILDEV) as client:
        client.delete('/email/all').raise_for_status()
        yield client


@pytest.fixture(autouse=True)
def _example_template(monkeypatch):
    """Lets the sender find the test template beside the production ones."""
    templates = template_environment((TEST_TEMPLATES_DIR, TEMPLATES_DIR))
    monkeypatch.setattr(sender, 'template_environment', lambda: templates)


def _received(maildev: httpx.Client) -> list[dict]:
    return maildev.get('/email').raise_for_status().json()


async def _queue(
    sessions: async_sessionmaker[AsyncSession],
    key: str,
    *,
    template: str = 'example',
    recipient: str = 'avery@demo.example',
) -> None:
    async with sessions() as session, session.begin():
        await notify(
            session,
            await system_context(session),
            template=template,
            recipient_email=recipient,
            context=_CONTEXT,
            idempotency_key=key,
        )


async def _notifications(sessions: async_sessionmaker[AsyncSession]) -> list[Notification]:
    async with sessions() as session:
        statement = select(Notification).order_by(col(Notification.id))
        return list((await session.scalars(statement)).all())


async def _make_due(sessions: async_sessionmaker[AsyncSession]) -> None:
    async with sessions() as session, session.begin():
        await session.execute(update(Notification).values(next_attempt_at=text('now()')))


async def test_a_queued_email_is_sent_once_with_text_and_html(committed_sessions, maildev):
    await _queue(committed_sessions, 'event-1:tests.example')

    assert await send_pending(committed_sessions, TEST_SETTINGS) == 1
    assert await send_pending(committed_sessions, TEST_SETTINGS) == 0

    [email] = _received(maildev)
    assert email['subject'] == '[LOCAL_DEV] Your application to Kansas was received'
    assert [to['address'] for to in email['to']] == ['avery@demo.example']
    assert [sent_from['address'] for sent_from in email['from']] == ['no-reply@licensing.localhost']
    assert 'Track it at http://localhost:3000/applications/7.' in email['text']
    assert 'href="http://localhost:3000/applications/7"' in email['html']
    [notification] = await _notifications(committed_sessions)
    assert (notification.status, notification.attempts) == (NotificationStatus.SENT, 1)
    assert notification.sent_at is not None


async def test_a_repeated_notification_is_sent_once(committed_sessions, maildev):
    await _queue(committed_sessions, 'event-1:tests.example')
    await _queue(committed_sessions, 'event-1:tests.example')

    assert await send_pending(committed_sessions, TEST_SETTINGS) == 1
    assert len(_received(maildev)) == 1


async def test_two_senders_never_send_the_same_email(committed_sessions, maildev):
    for n in range(20):
        await _queue(
            committed_sessions, f'event-{n}:tests.example', recipient=f'pa{n}@demo.example'
        )

    sent = await asyncio.gather(
        send_pending(committed_sessions, TEST_SETTINGS),
        send_pending(committed_sessions, TEST_SETTINGS),
    )

    assert sum(sent) == 20
    recipients = [email['to'][0]['address'] for email in _received(maildev)]
    assert sorted(recipients) == sorted(f'pa{n}@demo.example' for n in range(20))


async def test_a_batch_stops_at_its_size(committed_sessions, maildev):
    await _queue(committed_sessions, 'event-1:tests.example')
    await _queue(committed_sessions, 'event-2:tests.example')

    assert await send_pending(committed_sessions, TEST_SETTINGS, batch_size=1) == 1
    assert await send_pending(committed_sessions, TEST_SETTINGS, batch_size=1) == 1


async def test_a_failed_send_is_retried_later_then_marked_failed_and_logged(
    committed_sessions, caplog
):
    # Nothing listens on port 1, so every connection is refused.
    unreachable = TEST_SETTINGS.model_copy(update={'smtp_port': 1})
    await _queue(committed_sessions, 'event-1:tests.example')

    with caplog.at_level(logging.WARNING, logger='licensing_api.notifications.sender'):
        assert await send_pending(committed_sessions, unreachable) == 0
        [notification] = await _notifications(committed_sessions)
        assert (notification.status, notification.attempts) == (NotificationStatus.PENDING, 1)
        assert notification.last_error is not None
        assert notification.last_error.startswith('ConnectionRefusedError')
        assert notification.next_attempt_at > datetime.now(UTC)
        assert await send_pending(committed_sessions, unreachable) == 0, 'not due until its delay'
        assert caplog.records[-1].__dict__['outcome'] == 'retrying'

        for _ in range(MAX_ATTEMPTS - 1):
            await _make_due(committed_sessions)
            await send_pending(committed_sessions, unreachable)

    [notification] = await _notifications(committed_sessions)
    assert (notification.status, notification.attempts) == (NotificationStatus.FAILED, MAX_ATTEMPTS)
    final = caplog.records[-1]
    assert (final.levelname, final.getMessage(), final.__dict__['outcome']) == (
        'ERROR',
        'Notification failed',
        'failed',
    )
    assert 'avery@demo.example' not in str(final.__dict__), 'the address is PII and never logged'
    await _make_due(committed_sessions)
    assert await send_pending(committed_sessions, TEST_SETTINGS) == 0, 'a failed email stays failed'


async def test_a_template_that_cannot_render_fails_the_send(committed_sessions, maildev):
    await _queue(committed_sessions, 'event-1:tests.missing', template='no_such_template')

    assert await send_pending(committed_sessions, TEST_SETTINGS) == 0

    [notification] = await _notifications(committed_sessions)
    assert notification.last_error is not None
    assert notification.last_error.startswith("TemplateNotFound: 'no_such_template.txt' not found")
    assert _received(maildev) == []


class _RecordingSmtp:
    """Stands in for SES's SMTP endpoint, which offers what maildev does not: STARTTLS and login."""

    calls: list[tuple[str, object]] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.calls.append(('connect', (host, port, timeout)))

    def __enter__(self) -> '_RecordingSmtp':
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.calls.append(('quit', None))

    def starttls(self, context: object) -> None:
        self.calls.append(('starttls', None))

    def login(self, user: str, *credentials: str) -> None:
        self.calls.append(('login', user))

    def send_message(self, message: EmailMessage) -> None:
        self.calls.append(('send', message['To']))


def test_ses_settings_upgrade_to_tls_and_log_in_before_sending(monkeypatch):
    monkeypatch.setattr(sender.smtplib, 'SMTP', _RecordingSmtp)
    _RecordingSmtp.calls = []
    ses = Settings(
        smtp_host='email-smtp.us-east-1.amazonaws.com',
        smtp_port=587,
        smtp_starttls=True,
        smtp_username='ses-smtp-user',
    )

    sender._deliver(ses, 'avery@demo.example', RenderedEmail('Subject', 'Text', '<p>HTML</p>'))

    assert _RecordingSmtp.calls == [
        ('connect', ('email-smtp.us-east-1.amazonaws.com', 587, 30.0)),
        ('starttls', None),
        ('login', 'ses-smtp-user'),
        ('send', 'avery@demo.example'),
        ('quit', None),
    ]
