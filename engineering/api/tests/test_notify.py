"""notify() queues an email once per idempotency key (D7)."""

from sqlalchemy import func, select

from licensing_api.context import system_context
from licensing_api.repo.notification import Notification, NotificationStatus, notify
from tests.factories import make_user, system_user_id


async def test_notify_queues_a_pending_email_as_the_actor(db_session):
    recipient = await make_user(db_session, role='licensee')

    queued = await notify(
        db_session,
        await system_context(db_session, 'req-5'),
        template='privilege_issued',
        recipient_email=recipient.email,
        recipient_user_id=recipient.id,
        context={'privilege_number': 'PA-KS-000001'},
        idempotency_key='privilege.issued:1:notifications.send_privilege_issued',
    )

    assert queued.status == NotificationStatus.PENDING
    assert queued.template == 'privilege_issued'
    assert queued.recipient_email == recipient.email
    assert queued.recipient_user_id == recipient.id
    assert queued.context == {'privilege_number': 'PA-KS-000001'}
    assert queued.created_by == await system_user_id(db_session)
    assert queued.sent_at is None


async def test_a_repeated_key_queues_nothing_and_returns_the_first_row(db_session):
    first = await notify(
        db_session,
        await system_context(db_session),
        template='welcome',
        recipient_email='pa@example.com',
        context={},
        idempotency_key='practitioner.registered:7:notifications.send_welcome',
    )

    again = await notify(
        db_session,
        await system_context(db_session),
        template='welcome',
        recipient_email='changed@example.com',
        context={'ignored': True},
        idempotency_key='practitioner.registered:7:notifications.send_welcome',
    )

    assert again.id == first.id
    assert again.recipient_email == 'pa@example.com'
    count = await db_session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.idempotency_key == 'practitioner.registered:7:notifications.send_welcome'
        )
    )
    assert count == 1
