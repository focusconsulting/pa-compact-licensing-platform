"""Shared roots and conventions from the F-02 phase 1 migration (ADR-0005 to ADR-0008)."""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text

from licensing_api.__main__ import _mask_sensitive
from licensing_api.repo.audit_log import AuditLogEntry
from licensing_api.repo.reference import DenialScope, RefAdverseActionType, RefDenialReason
from licensing_api.repo.state import State
from licensing_api.repo.user import User
from tests.factories import assert_rejected, make_user, system_user_id

_LONG_AGO = datetime(2020, 1, 1, tzinfo=timezone.utc)


async def test_insert_copies_created_columns_into_updated_columns(db_session):
    user = await make_user(db_session)

    assert user.updated_at == user.created_at
    assert user.updated_by == user.created_by


async def test_update_stamps_updated_at(db_session):
    user = await make_user(db_session, created_at=_LONG_AGO)

    user.given_name = 'Renamed'
    user.updated_by = user.created_by
    await db_session.flush()
    await db_session.refresh(user)

    assert user.updated_at is not None
    assert user.updated_at > _LONG_AGO


async def test_system_user_exists_and_cannot_sign_in(db_session):
    system_id = await system_user_id(db_session)
    system_user = await db_session.get(User, system_id)

    assert system_user is not None
    assert system_user.is_active is False
    assert system_user.created_by == system_id


async def test_role_accepts_state_admin(db_session):
    user = await make_user(db_session, role='state_admin', state_code='KS')

    assert user.role == 'state_admin'


async def test_role_rejects_unknown_role(db_session):
    user = await make_user(db_session)

    await assert_rejected(
        db_session, "UPDATE users SET role = 'superuser' WHERE id = :id", {'id': user.id}
    )


async def test_permissions_default_to_empty_object(db_session):
    user = await make_user(db_session)

    assert user.permissions == {}


async def test_permissions_must_be_an_object(db_session):
    user = await make_user(db_session)

    await assert_rejected(
        db_session, "UPDATE users SET permissions = '[]'::jsonb WHERE id = :id", {'id': user.id}
    )


async def test_user_state_code_must_be_a_state(db_session):
    await assert_rejected(
        db_session,
        'INSERT INTO users (email, role, state_code, is_active, created_by) '
        "VALUES ('zz@example.com', 'state_staff', 'ZZ', TRUE, 1)",
    )


async def test_audit_log_rejects_update_and_delete(db_session):
    entry = AuditLogEntry(action='test.created', entity_type='test')
    db_session.add(entry)
    await db_session.flush()

    await assert_rejected(
        db_session, "UPDATE audit_log SET action = 'changed' WHERE id = :id", {'id': entry.id}
    )
    await assert_rejected(db_session, 'DELETE FROM audit_log WHERE id = :id', {'id': entry.id})


async def test_audit_log_can_change_inside_an_expungement_transaction(db_session):
    entry = AuditLogEntry(action='test.created', entity_type='test', reason='to be expunged')
    db_session.add(entry)
    await db_session.flush()

    await db_session.execute(text("SET LOCAL app.expunge = 'on'"))
    await db_session.execute(
        text("UPDATE audit_log SET reason = 'redacted' WHERE id = :id"), {'id': entry.id}
    )
    await db_session.refresh(entry)

    assert entry.reason == 'redacted'


def _utc(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


async def _compact_date_at(db_session, instant: datetime) -> date:
    result = await db_session.execute(
        text('SELECT compact_date_at(:instant)'), {'instant': instant}
    )
    return result.scalar_one()


async def test_compact_date_at_is_still_the_previous_day_late_evening_in_new_york(db_session):
    # 03:30 UTC on 8 October is 23:30 on 7 October in New York (EDT, UTC-4).
    assert await _compact_date_at(db_session, _utc(2026, 10, 8, 3, 30)) == date(2026, 10, 7)
    assert await _compact_date_at(db_session, _utc(2026, 10, 8, 4, 30)) == date(2026, 10, 8)


async def test_compact_date_at_follows_daylight_saving(db_session):
    # 04:30 UTC on 8 January is 23:30 on 7 January in New York (EST, UTC-5).
    assert await _compact_date_at(db_session, _utc(2026, 1, 8, 4, 30)) == date(2026, 1, 7)


async def test_compact_date_at_follows_the_time_zone_setting(db_session):
    await db_session.execute(text("UPDATE compact_settings SET time_zone = 'UTC', updated_by = 1"))

    assert await _compact_date_at(db_session, _utc(2026, 10, 8, 3, 30)) == date(2026, 10, 8)


async def test_compact_today_is_today_in_new_york(db_session):
    result = await db_session.execute(text('SELECT compact_today()'))

    assert result.scalar_one() == datetime.now(ZoneInfo('America/New_York')).date()


async def test_compact_settings_has_a_single_row(db_session):
    await assert_rejected(db_session, 'INSERT INTO compact_settings (id, created_by) VALUES (2, 1)')


async def test_every_jurisdiction_is_present_and_none_is_a_member_yet(db_session):
    total = await db_session.execute(select(func.count()).select_from(State))
    members = await db_session.execute(
        select(func.count()).select_from(State).where(State.is_member)
    )

    assert total.scalar_one() == 56
    assert members.scalar_one() == 0


async def test_a_state_must_be_a_member_to_go_live(db_session):
    await assert_rejected(db_session, "UPDATE states SET is_live = TRUE WHERE code = 'KS'")


async def test_proof_requirements_reject_unknown_values(db_session):
    await assert_rejected(
        db_session, "UPDATE states SET jurisprudence_requirement = 'exam' WHERE code = 'KS'"
    )


async def test_adverse_action_types_are_seeded_from_the_model_legislation(db_session):
    result = await db_session.execute(select(RefAdverseActionType.code))

    assert set(result.scalars()) == {
        'license_denial',
        'censure',
        'revocation',
        'suspension',
        'probation',
        'monitoring',
        'practice_restriction',
        'other',
    }


async def test_denial_reasons_cover_both_decisions(db_session):
    result = await db_session.execute(select(RefDenialReason.applies_to).distinct())

    assert set(result.scalars()) == {DenialScope.ELIGIBILITY, DenialScope.PRIVILEGE}


async def test_a_sent_notification_needs_a_sent_time(db_session):
    await assert_rejected(
        db_session,
        'INSERT INTO notifications (template, recipient_email, idempotency_key, status, created_by) '
        "VALUES ('welcome', 'pa@example.com', 'key-1', 'sent', 1)",
    )


async def test_a_delivery_needs_an_existing_event(db_session):
    await assert_rejected(
        db_session,
        'INSERT INTO domain_event_deliveries (event_id, handler) '
        "VALUES (gen_random_uuid(), 'notify_pa')",
    )


def test_ssn_is_masked_in_logs():
    assert _mask_sensitive({'ssn': '123-45-6789', 'ssn_last4': '6789', 'name': 'A'}) == {
        'ssn': '****',
        'ssn_last4': '****',
        'name': 'A',
    }
