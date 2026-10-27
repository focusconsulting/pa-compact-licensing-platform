from __future__ import annotations

from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, col, select

from licensing_api.repo.base import AuditColumns


class ContactPurpose(StrEnum):
    """Which of a state's notifications a contact receives (``purpose``)."""

    # As state of qualifying license: submitted, resubmitted, and withdrawn applications.
    APPLICATIONS = 'applications'
    # As remote state: privilege requests, issues, and deactivations.
    PRIVILEGES = 'privileges'
    # Adverse actions and SII.
    DISCIPLINE = 'discipline'


class StateContact(AuditColumns, table=True):
    """A mailbox a state wants one purpose's notifications sent to (FLOW-07). Tier: internal."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'state_contacts'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    state_code: str = Field(foreign_key='states.code', max_length=2)
    purpose: str
    email: str


async def contact_emails(
    session: AsyncSession, state_codes: list[str], purpose: ContactPurpose
) -> list[str]:
    """The distinct addresses for ``purpose`` across ``state_codes``, sorted. Empty when a state has none."""
    statement = (
        select(col(StateContact.email))
        .where(col(StateContact.state_code).in_(state_codes), col(StateContact.purpose) == purpose)
        .distinct()
        .order_by(col(StateContact.email))
    )
    return list((await session.scalars(statement)).all())
