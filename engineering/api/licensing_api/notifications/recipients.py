"""Who an event's email goes to, and queueing it once per recipient (FLOW-07).

Email to states and the Commission names no practitioner: it says what happened and links
to sign-in, where the reader sees only the records in their scope.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, col, select

from licensing_api.config import settings
from licensing_api.context import ChangeContext
from licensing_api.repo.domain_event import DomainEvent
from licensing_api.repo.notification import notify
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.privilege import Privilege
from licensing_api.repo.qualifying_license import QualifyingLicense
from licensing_api.repo.state import State
from licensing_api.repo.state_contact import ContactPurpose, contact_emails
from licensing_api.repo.user import User


async def aggregate[T: SQLModel](session: AsyncSession, model: type[T], event: DomainEvent) -> T:
    """The row the event is about, by its numeric ``aggregate_id``."""
    return (await session.scalars(select(model).where(model.id == event.aggregate_id))).one()  # type: ignore[attr-defined]  # every aggregate with a numeric key has ``id``


async def states_holding(session: AsyncSession, practitioner_id: int) -> set[str]:
    """Every state where the PA holds a qualifying license or a privilege, whatever its status."""
    licenses = select(col(QualifyingLicense.state_code)).where(
        col(QualifyingLicense.practitioner_id) == practitioner_id
    )
    privileges = select(col(Privilege.remote_state_code)).where(
        col(Privilege.practitioner_id) == practitioner_id
    )
    return set((await session.scalars(licenses.union(privileges))).all())


@dataclass(frozen=True)
class Recipient:
    """An address, and the user it belongs to when there is one."""

    email: str
    user_id: int | None = None


@dataclass(frozen=True)
class PractitionerRecipient:
    """A PA as their email addresses them."""

    recipient: Recipient
    first_name: str | None


async def practitioner(session: AsyncSession, practitioner_id: int) -> PractitionerRecipient:
    """The PA's correspondence email (Rule 4 §4.3(c)(8)), or their sign-in email when they gave none."""
    statement = (
        select(Practitioner, col(User.email))
        .join(User, col(User.id) == col(Practitioner.user_id))
        .where(col(Practitioner.id) == practitioner_id)
    )
    pa, sign_in_email = (await session.execute(statement)).one()
    return PractitionerRecipient(
        Recipient(pa.correspondence_email or sign_in_email, pa.user_id), pa.legal_first_name
    )


async def state_contacts(
    session: AsyncSession, state_codes: str | set[str], purpose: ContactPurpose
) -> list[Recipient]:
    """The contacts for ``purpose`` of one state or several, each address once; none until a state names one."""
    codes = [state_codes] if isinstance(state_codes, str) else sorted(state_codes)
    return [Recipient(email) for email in await contact_emails(session, codes, purpose)]


def commission_ops() -> list[Recipient]:
    """The Commission's operations mailbox, or none while ``commission_ops_email`` is unset."""
    return [Recipient(settings.commission_ops_email)] if settings.commission_ops_email else []


async def state_name(session: AsyncSession, state_code: str) -> str:
    """The state's name, as emails write it."""
    return (
        await session.scalars(select(col(State.name)).where(col(State.code) == state_code))
    ).one()


async def queue(
    session: AsyncSession,
    ctx: ChangeContext,
    event: DomainEvent,
    template: str,
    recipients: list[Recipient],
    context: Mapping[str, Any],
) -> None:
    """Queue ``template`` to each recipient, keyed ``<event_id>:<template>:<address>`` so a rerun queues nothing."""
    for recipient in recipients:
        await notify(
            session,
            ctx,
            template=template,
            recipient_email=recipient.email,
            recipient_user_id=recipient.user_id,
            context=context,
            idempotency_key=f'{event.event_id}:{template}:{recipient.email}',
        )
