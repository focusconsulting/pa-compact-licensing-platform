from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Column, insert, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel

from licensing_api.repo.base import TimestampTZ, entity_ref, utc_now

if TYPE_CHECKING:
    # Annotations only: licensing_api.context imports the repo package, so a runtime import would be circular.
    from licensing_api.context import ChangeContext


class EventType(StrEnum):
    """Every event the pilot emits. FLOW-07's "Events the pilot builds" table is the source; a test keeps them equal."""

    PRACTITIONER_REGISTERED = 'practitioner.registered'
    PRACTITIONER_PROFILE_CHANGED = 'practitioner.profile_changed'
    PRACTITIONER_EMAIL_CHANGE_REQUESTED = 'practitioner.email_change_requested'
    APPLICATION_SUBMITTED = 'application.submitted'
    APPLICATION_INFO_REQUESTED = 'application.info_requested'
    APPLICATION_RESUBMITTED = 'application.resubmitted'
    APPLICATION_ELIGIBLE = 'application.eligible'
    APPLICATION_DENIED = 'application.denied'
    APPLICATION_WITHDRAWN = 'application.withdrawn'
    APPLICATION_ELIGIBILITY_WITHDRAWN = 'application.eligibility_withdrawn'
    PRIVILEGE_REQUESTED = 'privilege.requested'
    PAYMENT_DECLINED = 'payment.declined'
    PRIVILEGE_ISSUED = 'privilege.issued'
    PRIVILEGE_DENIED = 'privilege.denied'
    PRIVILEGE_DEACTIVATED = 'privilege.deactivated'
    PRIVILEGE_EXPIRING = 'privilege.expiring'
    PRIVILEGE_EXPIRED = 'privilege.expired'
    QUALIFYING_LICENSE_STATUS_CHANGED = 'qualifying_license.status_changed'
    ADVERSE_ACTION_REPORTED = 'adverse_action.reported'
    ADVERSE_ACTION_LIFTED = 'adverse_action.lifted'
    SII_FLAGGED = 'sii.flagged'
    SII_CLOSED = 'sii.closed'


# IDs, codes, and dates only: an event is read by every handler and kept forever, so it never carries PII.
EventPayload = Mapping[str, int | str | UUID | date | None]


class OutsideTransactionError(RuntimeError):
    """``emit`` was called with no open transaction, so the event could be committed apart from its change."""


class DomainEvent(SQLModel, table=True):
    """A state change, written in the same transaction as the change itself (the transactional outbox, D2).

    ``payload`` carries IDs, never PII. Every event type is listed in FLOW-07's catalogue.
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'domain_events'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    event_id: UUID = Field(default_factory=uuid4, unique=True)
    type: str
    aggregate_type: str
    # Exactly one: aggregate_id for records with a numeric id, aggregate_key for records keyed by text, such as a state.
    aggregate_id: int | None = None
    aggregate_key: str | None = None
    payload: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    actor_user_id: int | None = Field(default=None, foreign_key='users.id')
    request_id: str | None = None
    occurred_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ)
    # When the dispatcher created this event's delivery rows (ADR-0012).
    dispatched_at: datetime | None = Field(default=None, sa_type=TimestampTZ)


class DomainEventDelivery(SQLModel, table=True):
    """One handler's progress on one event. Handlers are idempotent on ``(event_id, handler)``."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'domain_event_deliveries'  # type: ignore[assignment]

    event_id: UUID = Field(primary_key=True, foreign_key='domain_events.event_id')
    # A registered name such as 'notifications.send_privilege_issued', never the import path, which changes on a rename.
    handler: str = Field(primary_key=True)
    attempts: int = 0
    last_error: str | None = None
    handled_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    dead_lettered_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    created_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ)
    # A failed delivery is not retried before this time.
    next_attempt_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ)


async def emit(
    session: AsyncSession,
    ctx: ChangeContext,
    event_type: EventType,
    aggregate: SQLModel,
    payload: EventPayload | None = None,
) -> DomainEvent:
    """Write an event in the caller's transaction, beside the change it describes (the outbox, D2).

    Flushes first, so ``aggregate`` has its key. The caller commits.
    """
    if not session.in_transaction():
        raise OutsideTransactionError(
            f'{event_type} must be emitted inside the transaction that makes the change'
        )
    await session.flush()
    ref = entity_ref(aggregate)
    statement = (
        insert(DomainEvent)
        .values(
            type=event_type,
            aggregate_type=ref.type,
            aggregate_id=ref.id,
            aggregate_key=ref.key,
            payload={key: _json_value(value) for key, value in (payload or {}).items()},
            actor_user_id=ctx.user_id,
            request_id=ctx.request_id,
        )
        .returning(DomainEvent)
    )
    return (await session.scalars(statement)).one()


def _json_value(value: int | str | UUID | date | None) -> int | str | None:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value
