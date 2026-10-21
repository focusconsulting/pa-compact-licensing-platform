"""deactivate_privileges: the cascade FLOW-05 runs for every trigger."""

from datetime import datetime, timezone

from sqlmodel import col, select

from licensing_api.context import system_context
from licensing_api.repo.cascade import deactivate_privileges
from licensing_api.repo.domain_event import DomainEvent, EventType
from licensing_api.repo.history import PrivilegeHistory
from licensing_api.repo.privilege import AdministratorStatus, DeactivationReason, Privilege
from tests.factories import (
    make_eligible_application,
    make_issued_privilege,
    make_practitioner,
    make_privilege,
    make_submitted_request,
)

EFFECTIVE = datetime(2026, 9, 1, tzinfo=timezone.utc)


async def _privileges_in(session, practitioner, *states: str) -> list[Privilege]:
    application = await make_eligible_application(session, practitioner)
    return [
        await make_privilege(
            session, await make_submitted_request(session, application, remote_state_code=state)
        )
        for state in states
    ]


async def test_every_active_privilege_is_deactivated_with_history_and_an_event(db_session):
    practitioner = await make_practitioner(db_session)
    oklahoma, missouri = await _privileges_in(db_session, practitioner, 'OK', 'MO')
    other_practitioner = await make_issued_privilege(db_session)
    ctx = await system_context(db_session, 'req-cascade')

    deactivated = await deactivate_privileges(
        db_session,
        ctx,
        practitioner_id=practitioner.id,
        reason=DeactivationReason.QUALIFYING_LICENSE_ADVERSE_ACTION,
        effective_at=EFFECTIVE,
        note='Reported by Kansas.',
    )

    assert [p.id for p in deactivated] == [oklahoma.id, missouri.id]
    for privilege in deactivated:
        assert privilege.administrator_status == AdministratorStatus.INACTIVE
        assert privilege.deactivation_reason == DeactivationReason.QUALIFYING_LICENSE_ADVERSE_ACTION
        assert privilege.deactivated_at == EFFECTIVE
        assert privilege.deactivation_note == 'Reported by Kansas.'
    assert other_practitioner.administrator_status == AdministratorStatus.ACTIVE

    rows = (
        await db_session.scalars(
            select(PrivilegeHistory).where(
                col(PrivilegeHistory.entity_id).in_([oklahoma.id, missouri.id])
            )
        )
    ).all()
    assert len(rows) == 2
    assert all(row.effective_at == EFFECTIVE for row in rows)
    assert all(row.updated and row.updated['administrator_status'] == 'inactive' for row in rows)

    events = (
        await db_session.scalars(
            select(DomainEvent).where(col(DomainEvent.type) == EventType.PRIVILEGE_DEACTIVATED)
        )
    ).all()
    assert sorted(event.payload['remote_state_code'] for event in events) == ['MO', 'OK']
    assert {event.payload['reason'] for event in events} == {'qualifying_license_adverse_action'}
    assert {event.request_id for event in events} == {'req-cascade'}


async def test_only_the_named_remote_state_is_deactivated(db_session):
    practitioner = await make_practitioner(db_session)
    oklahoma, missouri = await _privileges_in(db_session, practitioner, 'OK', 'MO')

    deactivated = await deactivate_privileges(
        db_session,
        await system_context(db_session),
        practitioner_id=practitioner.id,
        reason=DeactivationReason.STATE_DEACTIVATED,
        effective_at=EFFECTIVE,
        remote_state_code='MO',
    )

    assert deactivated == [missouri]
    assert oklahoma.administrator_status == AdministratorStatus.ACTIVE


async def test_an_inactive_privilege_keeps_its_first_reason(db_session):
    privilege = await make_issued_privilege(
        db_session,
        administrator_status=AdministratorStatus.INACTIVE,
        deactivation_reason=DeactivationReason.STATE_DEACTIVATED,
        deactivated_at=EFFECTIVE,
    )

    deactivated = await deactivate_privileges(
        db_session,
        await system_context(db_session),
        practitioner_id=privilege.practitioner_id,
        reason=DeactivationReason.ELIGIBILITY_WITHDRAWN,
        effective_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )

    assert deactivated == []
    assert privilege.deactivation_reason == DeactivationReason.STATE_DEACTIVATED
