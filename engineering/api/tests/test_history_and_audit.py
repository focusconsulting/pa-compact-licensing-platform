"""history.write and audit_log.write (ADR-0005, ADR-0008, ADR-0009)."""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from licensing_api.context import Actor, ChangeContext, UnknownActorError, system_context
from licensing_api.repo import audit_log, history
from licensing_api.repo.history import PrivilegeHistory, StateHistory
from licensing_api.repo.state import State
from tests.factories import make_issued_privilege, make_user, system_user_id


async def test_history_records_a_new_row(db_session):
    privilege = await make_issued_privilege(db_session)

    row = await history.write(db_session, system_context(), privilege, before=None)

    assert isinstance(row, PrivilegeHistory)
    assert row.entity_id == privilege.id
    assert row.previous is None
    assert row.updated is not None
    assert row.updated['privilege_number'] == privilege.privilege_number
    assert 'created_by' not in row.updated
    assert row.removed is None
    assert row.changed_by == await system_user_id(db_session)


async def test_history_records_the_fields_that_changed(db_session):
    sub = uuid.uuid4()
    user = await make_user(db_session, public_id=sub)
    privilege = await make_issued_privilege(db_session)
    before = history.snapshot(privilege)
    effective = datetime(2026, 8, 1, tzinfo=timezone.utc)

    privilege.deactivation_note = 'Reported by the state.'
    row = await history.write(
        db_session,
        ChangeContext(Actor(sub), 'req-2'),
        privilege,
        before=before,
        effective_at=effective,
    )

    assert row is not None
    assert row.previous == before
    assert row.updated == {'deactivation_note': 'Reported by the state.'}
    assert row.removed is None
    assert row.changed_by == user.id
    assert row.effective_at == effective


async def test_history_records_a_field_cleared_to_null(db_session):
    privilege = await make_issued_privilege(db_session, deactivation_note='Temporary.')
    before = history.snapshot(privilege)

    privilege.deactivation_note = None
    row = await history.write(db_session, system_context(), privilege, before=before)

    assert row is not None
    assert row.updated is None
    assert row.removed == {'deactivation_note': 'Temporary.'}


async def test_history_writes_nothing_when_nothing_changed(db_session):
    privilege = await make_issued_privilege(db_session)

    row = await history.write(
        db_session, system_context(), privilege, before=history.snapshot(privilege)
    )

    assert row is None
    count = await db_session.scalar(
        select(func.count())
        .select_from(PrivilegeHistory)
        .where(PrivilegeHistory.entity_id == privilege.id)
    )
    assert count == 0


async def test_history_keys_a_state_by_code(db_session):
    state = await db_session.get(State, 'KS')
    assert state is not None
    before = history.snapshot(state)

    state.practice_requirements_url = 'https://example.gov/ks'
    row = await history.write(db_session, system_context(), state, before=before)

    assert isinstance(row, StateHistory)
    assert row.state_code == 'KS'
    assert row.updated == {'practice_requirements_url': 'https://example.gov/ks'}


async def test_history_rejects_an_entity_without_a_history_table(db_session):
    user = await make_user(db_session)

    with pytest.raises(ValueError, match='no history table'):
        await history.write(db_session, system_context(), user, before=None)


async def test_audit_records_an_action_on_a_numbered_row(db_session):
    sub = uuid.uuid4()
    user = await make_user(db_session, public_id=sub)
    privilege = await make_issued_privilege(db_session)

    entry = await audit_log.write(
        db_session,
        ChangeContext(Actor(sub), 'req-3'),
        'privilege.deactivated',
        privilege,
        before={'administrator_status': 'active'},
        after={'administrator_status': 'inactive'},
        reason='Court order.',
    )

    assert (entry.entity_type, entry.entity_id, entry.entity_key) == (
        'privileges',
        privilege.id,
        None,
    )
    assert entry.actor_user_id == user.id
    assert entry.action == 'privilege.deactivated'
    assert entry.before == {'administrator_status': 'active'}
    assert entry.after == {'administrator_status': 'inactive'}
    assert entry.reason == 'Court order.'
    assert entry.request_id == 'req-3'


async def test_audit_records_an_action_on_a_state_by_code(db_session):
    state = await db_session.get(State, 'KS')
    assert state is not None

    entry = await audit_log.write(db_session, system_context(), 'state.configured', state)

    assert (entry.entity_type, entry.entity_id, entry.entity_key) == ('states', None, 'KS')
    assert entry.before is None
    assert entry.after is None


async def test_audit_rejects_an_action_that_is_not_entity_dot_verb(db_session):
    state = await db_session.get(State, 'KS')
    assert state is not None

    with pytest.raises(ValueError, match='<entity>.<verb>'):
        await audit_log.write(db_session, system_context(), 'Revealed SSN', state)


async def test_audit_refuses_an_actor_that_matches_no_user(db_session):
    state = await db_session.get(State, 'KS')
    assert state is not None

    with pytest.raises(UnknownActorError):
        await audit_log.write(
            db_session, ChangeContext(Actor(uuid.uuid4()), None), 'state.configured', state
        )


async def test_history_refuses_an_actor_that_matches_no_user(db_session):
    privilege = await make_issued_privilege(db_session)

    with pytest.raises(IntegrityError):
        await history.write(
            db_session, ChangeContext(Actor(uuid.uuid4()), None), privilege, before=None
        )
