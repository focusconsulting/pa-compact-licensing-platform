"""Run an email handler as the Worker would and read back what it queued."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, col, select

from licensing_api.context import system_context
from licensing_api.events import Handler
from licensing_api.repo.domain_event import EventType, emit
from licensing_api.repo.notification import Notification
from licensing_api.repo.state_contact import ContactPurpose
from tests.factories import make_state_contact

OPS = 'commission-ops@demo.example'


async def add_contacts(session: AsyncSession, *states: str) -> None:
    """A contact per purpose for each state, addressed ``<state>-<purpose>@demo.example``."""
    for state in states:
        for purpose in ContactPurpose:
            await make_state_contact(
                session, state, purpose, f'{state.lower()}-{purpose}@demo.example'
            )


async def run_handler(
    session: AsyncSession, declared: Handler, event_type: EventType, aggregate: SQLModel
) -> list[tuple[str, str, dict]]:
    """Emit the event, run the handler, and return each queued (template, address, context)."""
    ctx = await system_context(session)
    event = await emit(session, ctx, event_type, aggregate)
    await declared.run(session, ctx, event)
    statement = select(Notification).order_by(col(Notification.id))
    return [
        (n.template, n.recipient_email, n.context) for n in (await session.scalars(statement)).all()
    ]
