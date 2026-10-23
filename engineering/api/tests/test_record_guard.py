"""The guard every route test runs under: a change must emit an event."""

from licensing_api.context import system_context
from licensing_api.repo import history
from licensing_api.repo.domain_event import EventType, emit
from tests.factories import make_issued_privilege
from tests.record_guard import RecordGuard


async def test_a_change_committed_without_an_event_is_a_violation(db_session):
    guard = RecordGuard(db_session)
    privilege = await make_issued_privilege(db_session)

    await history.write(db_session, await system_context(db_session), privilege, before=None)
    await db_session.commit()

    assert guard.violations == ['Committed privileges_history with no domain_events row']


async def test_a_change_committed_with_its_event_passes(db_session):
    guard = RecordGuard(db_session)
    privilege = await make_issued_privilege(db_session)
    ctx = await system_context(db_session)

    await history.write(db_session, ctx, privilege, before=None)
    await emit(db_session, ctx, EventType.PRIVILEGE_ISSUED, privilege)
    await db_session.commit()

    assert guard.violations == []


async def test_a_rolled_back_change_is_forgotten(db_session):
    guard = RecordGuard(db_session)
    privilege = await make_issued_privilege(db_session)

    await history.write(db_session, await system_context(db_session), privilege, before=None)
    await db_session.rollback()
    await db_session.commit()

    assert guard.violations == []
