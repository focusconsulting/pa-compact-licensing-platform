"""Sends queued ``notifications`` rows over SMTP: maildev locally, SES's SMTP interface in AWS (D7, ADR-0014)."""

from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
import time
from datetime import timedelta
from email.message import EmailMessage

from jinja2 import Environment, TemplateError
from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlmodel import col, select

from licensing_api.config import Settings
from licensing_api.context import system_context
from licensing_api.notifications.render import RenderedEmail, render, template_environment
from licensing_api.repo.notification import Notification, NotificationStatus

logger = logging.getLogger(__name__)

# A notification that fails this many times is marked failed and alarmed on.
MAX_ATTEMPTS = 5
# Doubles after each failure: 30 s, 1 min, 2 min, 4 min.
FIRST_RETRY_DELAY = timedelta(seconds=30)
SMTP_TIMEOUT = timedelta(seconds=30)
_MAX_ERROR_LENGTH = 2000


async def send_pending(
    session_factory: async_sessionmaker[AsyncSession], settings: Settings, *, batch_size: int = 100
) -> int:
    """Send up to ``batch_size`` due notifications, each in its own transaction. Returns the number sent.

    Each row is claimed with ``SKIP LOCKED``, so two Workers never send the same one. A
    failure is retried with backoff, then marked ``failed``. Sending is at least once: if
    the commit after a successful send fails, the email goes again on the next attempt.
    """
    environment = template_environment()
    sent = 0
    for _ in range(batch_size):
        outcome = await _send_one(session_factory, settings, environment)
        if outcome is None:
            break
        sent += outcome
    return sent


async def _send_one(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    environment: Environment,
) -> bool | None:
    """Send the next due notification: True when sent, False when it failed, None when none is due."""
    async with session_factory() as session, session.begin():
        due = (
            select(Notification)
            .where(
                col(Notification.status) == NotificationStatus.PENDING,
                col(Notification.next_attempt_at) <= func.now(),
            )
            .order_by(col(Notification.next_attempt_at))
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        notification = (await session.scalars(due)).one_or_none()
        if notification is None:
            return None
        ctx = await system_context(session)
        # The template and ID only: the address is PII.
        log = {'notification_id': str(notification.public_id), 'template': notification.template}
        attempts = notification.attempts + 1
        started = time.monotonic()
        try:
            email = render(environment, notification.template, notification.context, settings)
            await asyncio.to_thread(_deliver, settings, notification.recipient_email, email)
        # smtplib.SMTPException is an OSError, as are connection failures and timeouts.
        except (TemplateError, OSError) as error:
            failure = {
                'attempts': attempts,
                'last_error': f'{type(error).__name__}: {error}'[:_MAX_ERROR_LENGTH],
                'updated_by': ctx.user_id,
            }
            if attempts >= MAX_ATTEMPTS:
                await _record(session, notification, **failure, status=NotificationStatus.FAILED)
                logger.exception(
                    'Notification failed', extra={**log, 'attempts': attempts, 'outcome': 'failed'}
                )
            else:
                delay = FIRST_RETRY_DELAY * 2 ** (attempts - 1)
                await _record(session, notification, **failure, next_attempt_at=func.now() + delay)
                logger.warning(
                    'Notification send failed; will retry',
                    exc_info=True,
                    extra={**log, 'attempts': attempts, 'outcome': 'retrying'},
                )
            return False

        await _record(
            session,
            notification,
            attempts=attempts,
            status=NotificationStatus.SENT,
            sent_at=func.now(),
            last_error=None,
            updated_by=ctx.user_id,
        )
        duration_ms = round((time.monotonic() - started) * 1000)
        logger.info(
            'Notification sent', extra={**log, 'outcome': 'sent', 'duration_ms': duration_ms}
        )
        return True


def _deliver(settings: Settings, recipient: str, email: RenderedEmail) -> None:
    """Send one email, blocking; run in a thread so the Worker's event loop keeps running."""
    message = EmailMessage()
    message['Subject'] = email.subject
    message['From'] = settings.email_from_address
    message['To'] = recipient
    message.set_content(email.text)
    message.add_alternative(email.html, subtype='html')
    with smtplib.SMTP(
        settings.smtp_host, settings.smtp_port, timeout=SMTP_TIMEOUT.total_seconds()
    ) as smtp:
        if settings.smtp_starttls:
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


async def _record(session: AsyncSession, notification: Notification, **values: object) -> None:
    await session.execute(
        update(Notification).where(col(Notification.id) == notification.id).values(**values)
    )
