"""The outbox write and handler declarations (D2, FLOW-07, ADR-0009)."""

import re
import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from licensing_api.context import ChangeContext, system_context
from licensing_api.events import HandlerRegistry, handler
from licensing_api.repo.base import entity_ref
from licensing_api.repo.domain_event import (
    DomainEvent,
    DomainEventDelivery,
    EventType,
    OutsideTransactionError,
    emit,
)
from licensing_api.repo.state import State
from tests.factories import make_issued_privilege, make_user, system_user_id

_FLOW_07 = Path(__file__).parents[3] / 'product/context/flows/07-domain-event-catalogue.md'


def _pilot_event_names() -> set[str]:
    """Event names in FLOW-07's pilot table; ``a.b`` / ``.c`` is shorthand for ``a.b`` and ``a.c``."""
    section = _FLOW_07.read_text().split('## Events the pilot builds')[1].split('\n## ')[0]
    names: set[str] = set()
    for row in section.splitlines():
        if not row.startswith('| `'):
            continue
        entity = ''
        for token in re.findall(r'`([a-z_.]+)`', row.split('|')[1]):
            if token.startswith('.'):
                names.add(entity + token)
            else:
                entity = token.split('.')[0]
                names.add(token)
    return names


def test_event_types_match_the_flow_07_catalogue():
    assert {event.value for event in EventType} == _pilot_event_names()


# Append-only: every event type a release has emitted. Stored events keep their type forever.
_SHIPPED_EVENT_TYPES = frozenset(
    {
        'practitioner.registered',
        'practitioner.profile_changed',
        'practitioner.email_change_requested',
        'application.submitted',
        'application.info_requested',
        'application.resubmitted',
        'application.eligible',
        'application.denied',
        'application.withdrawn',
        'application.eligibility_withdrawn',
        'privilege.requested',
        'payment.declined',
        'privilege.issued',
        'privilege.denied',
        'privilege.deactivated',
        'privilege.expiring',
        'privilege.expired',
        'qualifying_license.status_changed',
        'adverse_action.reported',
        'adverse_action.lifted',
        'sii.flagged',
        'sii.closed',
    }
)
# Types removed from EventType through the two-release process in the platform contract.
_RETIRED_EVENT_TYPES: frozenset[str] = frozenset()


def test_an_event_type_leaves_only_through_the_two_release_process():
    current = {event.value for event in EventType}
    assert not current - _SHIPPED_EVENT_TYPES, 'Add new event types to _SHIPPED_EVENT_TYPES'
    assert _SHIPPED_EVENT_TYPES - current == _RETIRED_EVENT_TYPES, (
        'An event type left EventType. Follow "Renaming or removing an event type" in '
        'engineering/docs/platform-contract.md, then add it to _RETIRED_EVENT_TYPES'
    )


async def test_emit_refuses_without_an_open_transaction(db_session):
    with pytest.raises(OutsideTransactionError):
        await emit(
            db_session,
            ChangeContext(user_id=1, request_id=None),
            EventType.SII_FLAGGED,
            State(code='KS'),
        )


async def test_emit_refuses_after_the_change_is_committed(db_session):
    ctx = await system_context(db_session)
    privilege = await make_issued_privilege(db_session)
    await db_session.commit()

    with pytest.raises(OutsideTransactionError):
        await emit(db_session, ctx, EventType.PRIVILEGE_ISSUED, privilege)


async def test_emit_writes_the_event_with_the_actor_and_request_id(db_session: AsyncSession):
    user = await make_user(db_session)
    privilege = await make_issued_privilege(db_session)
    ctx = ChangeContext(user_id=user.id, request_id='req-1')

    event = await emit(
        db_session,
        ctx,
        EventType.PRIVILEGE_ISSUED,
        privilege,
        {
            'privilege_id': privilege.id,
            'public_id': privilege.public_id,
            'expires_on': date(2027, 12, 31),
        },
    )

    assert event.type == 'privilege.issued'
    assert (event.aggregate_type, event.aggregate_id, event.aggregate_key) == (
        'privileges',
        privilege.id,
        None,
    )
    assert event.actor_user_id == user.id
    assert event.request_id == 'req-1'
    assert event.payload == {
        'privilege_id': privilege.id,
        'public_id': str(privilege.public_id),
        'expires_on': '2027-12-31',
    }
    assert isinstance(event.event_id, uuid.UUID)


async def test_emit_references_a_state_by_code_as_the_system_user(db_session):
    state = await db_session.get(State, 'KS')
    assert state is not None

    event = await emit(db_session, await system_context(db_session), EventType.SII_FLAGGED, state)

    assert (event.aggregate_type, event.aggregate_id, event.aggregate_key) == ('states', None, 'KS')
    assert event.actor_user_id == await system_user_id(db_session)
    assert event.payload == {}


async def test_entity_ref_rejects_an_unflushed_row():
    with pytest.raises(ValueError, match='no key yet'):
        entity_ref(State(code='KS'))


async def test_entity_ref_rejects_a_composite_key(db_session):
    event = await emit(
        db_session,
        await system_context(db_session),
        EventType.SII_FLAGGED,
        await _kansas(db_session),
    )
    delivery = DomainEventDelivery(event_id=event.event_id, handler='tests.example')
    db_session.add(delivery)
    await db_session.flush()

    with pytest.raises(ValueError, match='composite key'):
        entity_ref(delivery)


async def _kansas(session: AsyncSession) -> State:
    state = await session.get(State, 'KS')
    assert state is not None
    return state


async def _noop(session: AsyncSession, ctx: ChangeContext, event: DomainEvent) -> None:
    return None


def test_handler_declares_its_name_and_event_types():
    declared = handler('notifications.send_privilege_issued', EventType.PRIVILEGE_ISSUED)(_noop)

    assert declared.name == 'notifications.send_privilege_issued'
    assert declared.event_types == frozenset({EventType.PRIVILEGE_ISSUED})
    assert declared.run is _noop


@pytest.mark.parametrize(
    'name', ['send_privilege_issued', 'Notifications.send', 'licensing_api.handlers.send.x', '']
)
def test_handler_rejects_a_name_that_is_not_module_dot_action(name):
    with pytest.raises(ValueError, match='owning module'):
        handler(name, EventType.PRIVILEGE_ISSUED)


def test_handler_needs_an_event_type():
    with pytest.raises(ValueError, match='at least one event type'):
        handler('notifications.send_nothing')


def test_registry_rejects_two_handlers_with_one_name():
    first = handler('notifications.send', EventType.PRIVILEGE_ISSUED)(_noop)
    second = handler('notifications.send', EventType.PRIVILEGE_DENIED)(_noop)

    with pytest.raises(ValueError, match='Two handlers'):
        HandlerRegistry([first, second])


def test_registry_returns_the_handlers_for_an_event():
    issued = handler('notifications.send_issued', EventType.PRIVILEGE_ISSUED)(_noop)
    either = handler(
        'metrics.time_to_issue', EventType.PRIVILEGE_ISSUED, EventType.PRIVILEGE_DENIED
    )(_noop)
    registry = HandlerRegistry([issued, either])

    assert registry.for_event(EventType.PRIVILEGE_ISSUED) == (issued, either)
    assert registry.for_event(EventType.PRIVILEGE_DENIED) == (either,)
    assert registry.for_event(EventType.SII_CLOSED) == ()
