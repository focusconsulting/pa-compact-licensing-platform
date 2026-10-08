"""Core entities from the F-02 phase 2 migrations: the rules the database enforces."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from licensing_api.repo.history import PractitionerHistory
from licensing_api.repo.participation_application import ApplicationKind, ApplicationStatus
from licensing_api.repo.practitioner import PractitionerSsn
from tests.factories import (
    assert_rejected,
    make_adverse_action,
    make_application,
    make_eligible_application,
    make_issued_privilege,
    make_practitioner,
    make_qualifying_license,
    make_submitted_request,
    system_user_id,
)

# --- practitioners ---------------------------------------------------------


async def test_a_practitioner_is_one_per_user(db_session):
    practitioner = await make_practitioner(db_session)

    await assert_rejected(
        db_session,
        'INSERT INTO practitioners (user_id, created_by) VALUES (:user_id, 1)',
        {'user_id': practitioner.user_id},
    )


async def test_a_verified_field_group_names_the_state_and_the_time(db_session):
    practitioner = await make_practitioner(db_session)

    await assert_rejected(
        db_session,
        "UPDATE practitioners SET identity_verified_by_state = 'KS', updated_by = 1 WHERE id = :id",
        {'id': practitioner.id},
    )


async def test_a_verified_field_group_is_accepted_with_both(db_session):
    practitioner = await make_practitioner(db_session)

    await db_session.execute(
        text(
            "UPDATE practitioners SET identity_verified_by_state = 'KS', "
            'identity_verified_at = now(), updated_by = 1 WHERE id = :id'
        ),
        {'id': practitioner.id},
    )
    await db_session.refresh(practitioner)

    assert practitioner.identity_verified_by_state == 'KS'


async def test_a_practitioner_with_applications_cannot_be_deleted(db_session):
    practitioner = await make_practitioner(db_session)
    await make_application(db_session, practitioner)

    await assert_rejected(
        db_session, 'DELETE FROM practitioners WHERE id = :id', {'id': practitioner.id}
    )


# --- practitioner_ssn ------------------------------------------------------


async def _make_ssn(db_session, practitioner, lookup_hash: bytes) -> PractitionerSsn:
    ssn = PractitionerSsn(
        practitioner_id=practitioner.id,
        ssn_ciphertext=b'ciphertext',
        ssn_key_version=1,
        ssn_lookup_hash=lookup_hash,
        ssn_last4='6789',
        created_by=await system_user_id(db_session),
    )
    db_session.add(ssn)
    await db_session.flush()
    return ssn


async def test_the_same_ssn_cannot_belong_to_two_practitioners(db_session):
    await _make_ssn(db_session, await make_practitioner(db_session), b'same-hash')

    second = await make_practitioner(db_session)
    await assert_rejected(
        db_session,
        'INSERT INTO practitioner_ssn (practitioner_id, ssn_ciphertext, ssn_key_version, '
        "ssn_lookup_hash, ssn_last4, created_by) VALUES (:id, 'x', 1, 'same-hash', '6789', 1)",
        {'id': second.id},
    )


async def test_ssn_last4_must_be_four_digits(db_session):
    practitioner = await make_practitioner(db_session)

    await assert_rejected(
        db_session,
        'INSERT INTO practitioner_ssn (practitioner_id, ssn_ciphertext, ssn_key_version, '
        "ssn_lookup_hash, ssn_last4, created_by) VALUES (:id, 'x', 1, 'h', '67a9', 1)",
        {'id': practitioner.id},
    )


# --- documents -------------------------------------------------------------


async def test_a_document_owner_type_must_be_known(db_session):
    await assert_rejected(
        db_session,
        'INSERT INTO documents (owner_type, owner_id, kind, storage_key, file_name, '
        "content_type, size_bytes, created_by) VALUES ('invoice', 1, 'proof', 'k1', 'a.pdf', "
        "'application/pdf', 10, 1)",
    )


# --- qualifying_licenses ---------------------------------------------------


async def test_a_license_number_is_unique_within_a_state(db_session):
    practitioner = await make_practitioner(db_session)
    license = await make_qualifying_license(db_session, practitioner)

    await assert_rejected(
        db_session,
        'INSERT INTO qualifying_licenses (state_code, license_number, state_reported_status, '
        "status_effective_on, is_unrestricted, created_by) VALUES ('KS', :number, 'active', "
        "'2024-01-01', TRUE, 1)",
        {'number': license.license_number},
    )


async def test_the_same_license_number_is_allowed_in_another_state(db_session):
    practitioner = await make_practitioner(db_session)
    license = await make_qualifying_license(db_session, practitioner)

    other = await make_qualifying_license(
        db_session, practitioner, state_code='OK', license_number=license.license_number
    )

    assert other.id != license.id


async def test_a_license_cannot_expire_before_it_was_issued(db_session):
    practitioner = await make_practitioner(db_session)

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await make_qualifying_license(
                db_session, practitioner, issued_on=date(2025, 1, 1), expires_on=date(2024, 1, 1)
            )


# --- participation_applications --------------------------------------------


async def test_an_eligible_application_has_every_required_field(db_session):
    application = await make_eligible_application(db_session, await make_practitioner(db_session))

    assert application.status == ApplicationStatus.ELIGIBLE


async def test_eligible_requires_the_background_check_date(db_session):
    application = await make_eligible_application(db_session, await make_practitioner(db_session))

    await assert_rejected(
        db_session,
        'UPDATE participation_applications SET cbc_completed_on = NULL, updated_by = 1 WHERE id = :id',
        {'id': application.id},
    )


async def test_eligible_requires_a_verified_license(db_session):
    application = await make_eligible_application(db_session, await make_practitioner(db_session))

    await assert_rejected(
        db_session,
        'UPDATE participation_applications SET license_verified_at = NULL, '
        'license_verified_by = NULL, updated_by = 1 WHERE id = :id',
        {'id': application.id},
    )


async def test_a_submitted_application_has_an_opened_time(db_session):
    application = await make_application(db_session, await make_practitioner(db_session))

    await assert_rejected(
        db_session,
        "UPDATE participation_applications SET status = 'submitted', updated_by = 1 WHERE id = :id",
        {'id': application.id},
    )


async def test_a_denial_needs_a_reason(db_session):
    application = await make_eligible_application(db_session, await make_practitioner(db_session))

    await assert_rejected(
        db_session,
        "UPDATE participation_applications SET status = 'denied', updated_by = 1 WHERE id = :id",
        {'id': application.id},
    )


async def test_withdrawing_eligibility_needs_a_time_and_reason(db_session):
    application = await make_eligible_application(db_session, await make_practitioner(db_session))

    await assert_rejected(
        db_session,
        "UPDATE participation_applications SET status = 'eligibility_withdrawn', updated_by = 1 "
        'WHERE id = :id',
        {'id': application.id},
    )


async def test_a_practitioner_has_one_open_application(db_session):
    practitioner = await make_practitioner(db_session)
    await make_application(db_session, practitioner)

    await assert_rejected(
        db_session,
        'INSERT INTO participation_applications (practitioner_id, sql_state_code, created_by) '
        "VALUES (:id, 'KS', 1)",
        {'id': practitioner.id},
    )


async def test_a_closed_application_does_not_block_a_new_one(db_session):
    practitioner = await make_practitioner(db_session)
    await make_eligible_application(db_session, practitioner)

    change = await make_application(db_session, practitioner, kind=ApplicationKind.CHANGE_SQL)

    assert change.status == ApplicationStatus.DRAFT


# --- privilege_requests ----------------------------------------------------


async def test_a_submitted_request_pins_the_license_expiry(db_session):
    application = await make_eligible_application(db_session, await make_practitioner(db_session))
    request = await make_submitted_request(db_session, application)

    await assert_rejected(
        db_session,
        'UPDATE privilege_requests SET ql_expires_on_snapshot = NULL, updated_by = 1 WHERE id = :id',
        {'id': request.id},
    )


async def test_a_practitioner_has_one_open_request_per_remote_state(db_session):
    application = await make_eligible_application(db_session, await make_practitioner(db_session))
    await make_submitted_request(db_session, application)

    await assert_rejected(
        db_session,
        'INSERT INTO privilege_requests (participation_application_id, practitioner_id, '
        "remote_state_code, qualifying_license_id, created_by) VALUES (:app, :pa, 'OK', :ql, 1)",
        {
            'app': application.id,
            'pa': application.practitioner_id,
            'ql': application.qualifying_license_id,
        },
    )


async def test_requests_to_different_remote_states_can_be_open_together(db_session):
    application = await make_eligible_application(db_session, await make_practitioner(db_session))
    await make_submitted_request(db_session, application)

    other = await make_submitted_request(db_session, application, remote_state_code='NE')

    assert other.remote_state_code == 'NE'


async def test_a_denied_request_needs_a_reason(db_session):
    application = await make_eligible_application(db_session, await make_practitioner(db_session))
    request = await make_submitted_request(db_session, application)

    await assert_rejected(
        db_session,
        "UPDATE privilege_requests SET status = 'denied', decided_at = now(), decided_by = 1, "
        'updated_by = 1 WHERE id = :id',
        {'id': request.id},
    )


# --- privileges ------------------------------------------------------------


async def test_an_issued_privilege_expires_on_the_pinned_date(db_session):
    privilege = await make_issued_privilege(db_session)

    assert privilege.expires_on == date(2027, 12, 31)


async def test_an_inactive_privilege_needs_a_reason_and_time(db_session):
    privilege = await make_issued_privilege(db_session)

    await assert_rejected(
        db_session,
        "UPDATE privileges SET administrator_status = 'inactive', updated_by = 1 WHERE id = :id",
        {'id': privilege.id},
    )


async def test_a_deactivation_reason_must_be_known(db_session):
    privilege = await make_issued_privilege(db_session)

    await assert_rejected(
        db_session,
        "UPDATE privileges SET administrator_status = 'inactive', deactivation_reason = 'expired', "
        'deactivated_at = now(), updated_by = 1 WHERE id = :id',
        {'id': privilege.id},
    )


async def test_a_privilege_number_is_unique(db_session):
    privilege = await make_issued_privilege(db_session)
    other = await make_issued_privilege(db_session)

    await assert_rejected(
        db_session,
        'UPDATE privileges SET privilege_number = :number, updated_by = 1 WHERE id = :id',
        {'number': privilege.privilege_number, 'id': other.id},
    )


# --- adverse_actions and sii_reports ---------------------------------------


async def test_an_adverse_action_needs_a_summary_or_an_order(db_session):
    action = await make_adverse_action(db_session, await make_issued_privilege(db_session))

    await assert_rejected(
        db_session,
        'UPDATE adverse_actions SET summary = NULL, updated_by = 1 WHERE id = :id',
        {'id': action.id},
    )


async def test_an_adverse_action_targets_what_it_is_against(db_session):
    action = await make_adverse_action(db_session, await make_issued_privilege(db_session))

    await assert_rejected(
        db_session,
        "UPDATE adverse_actions SET against = 'qualifying_license', updated_by = 1 WHERE id = :id",
        {'id': action.id},
    )


async def test_an_adverse_action_cannot_end_before_it_starts(db_session):
    action = await make_adverse_action(db_session, await make_issued_privilege(db_session))

    await assert_rejected(
        db_session,
        "UPDATE adverse_actions SET effective_until = '2026-06-30', updated_by = 1 WHERE id = :id",
        {'id': action.id},
    )


async def test_an_npdb_category_must_exist(db_session):
    action = await make_adverse_action(db_session, await make_issued_privilege(db_session))

    await assert_rejected(
        db_session,
        'INSERT INTO adverse_action_npdb_categories (adverse_action_id, npdb_category_code, '
        "created_by) VALUES (:id, 'unknown', 1)",
        {'id': action.id},
    )


async def test_an_sii_report_needs_a_way_to_reach_the_contact(db_session):
    practitioner = await make_practitioner(db_session)

    await assert_rejected(
        db_session,
        'INSERT INTO sii_reports (practitioner_id, reporting_state_code, description, '
        "contact_name, determined_on, created_by) VALUES (:id, 'KS', 'Under review', 'Board', "
        "'2026-07-01', 1)",
        {'id': practitioner.id},
    )


# --- history ---------------------------------------------------------------


async def test_history_rejects_update_and_delete(db_session):
    practitioner = await make_practitioner(db_session)
    entry = PractitionerHistory(
        entity_id=practitioner.id,
        changed_by=await system_user_id(db_session),
        updated={'legal_last_name': 'Assistant'},
    )
    db_session.add(entry)
    await db_session.flush()

    await assert_rejected(
        db_session,
        "UPDATE practitioners_history SET updated = '{}'::jsonb WHERE id = :id",
        {'id': entry.id},
    )
    await assert_rejected(
        db_session, 'DELETE FROM practitioners_history WHERE id = :id', {'id': entry.id}
    )


async def test_every_history_table_is_append_only(db_session):
    result = await db_session.execute(
        text(
            "SELECT c.relname FROM pg_class c WHERE c.relkind = 'r' "
            "AND c.relnamespace = 'public'::regnamespace AND c.relname LIKE '%\\_history' "
            'AND NOT EXISTS (SELECT 1 FROM pg_trigger t WHERE t.tgrelid = c.oid '
            "AND t.tgname = 'trg_' || c.relname || '_append_only')"
        )
    )

    assert list(result.scalars()) == []


async def test_every_table_with_audit_columns_has_the_trigger(db_session):
    result = await db_session.execute(
        text(
            'SELECT c.table_name FROM information_schema.columns c '
            "WHERE c.table_schema = 'public' AND c.column_name = 'updated_by' "
            'AND NOT EXISTS (SELECT 1 FROM pg_trigger t '
            "WHERE t.tgrelid = ('public.' || c.table_name)::regclass "
            "AND t.tgname = 'trg_' || c.table_name || '_audit_columns')"
        )
    )

    assert list(result.scalars()) == []


# --- review fixes ----------------------------------------------------------


async def test_eligible_requires_a_linked_license(db_session):
    application = await make_eligible_application(db_session, await make_practitioner(db_session))

    await assert_rejected(
        db_session,
        'UPDATE participation_applications SET qualifying_license_id = NULL, updated_by = 1 '
        'WHERE id = :id',
        {'id': application.id},
    )


async def test_an_application_keeps_the_license_the_pa_claimed(db_session):
    application = await make_application(
        db_session,
        await make_practitioner(db_session),
        claimed_license_number='KS-12345',
        claimed_license_expires_on=date(2027, 12, 31),
    )

    assert application.qualifying_license_id is None
    assert application.claimed_license_number == 'KS-12345'


async def test_a_practitioner_has_one_eligible_application(db_session):
    practitioner = await make_practitioner(db_session)
    await make_eligible_application(db_session, practitioner)

    with pytest.raises(DBAPIError):
        async with db_session.begin_nested():
            await make_eligible_application(
                db_session, practitioner, kind=ApplicationKind.CHANGE_SQL, sql_state_code='OK'
            )


async def test_superseding_lets_a_change_of_sql_become_eligible(db_session):
    practitioner = await make_practitioner(db_session)
    old = await make_eligible_application(db_session, practitioner)
    old.status = ApplicationStatus.SUPERSEDED
    old.superseded_at = datetime(2026, 9, 1, tzinfo=timezone.utc)
    old.updated_by = old.created_by
    await db_session.flush()

    new = await make_eligible_application(
        db_session, practitioner, kind=ApplicationKind.CHANGE_SQL, sql_state_code='OK'
    )

    assert new.status == ApplicationStatus.ELIGIBLE


async def test_a_superseded_application_records_when(db_session):
    application = await make_eligible_application(db_session, await make_practitioner(db_session))

    await assert_rejected(
        db_session,
        "UPDATE participation_applications SET status = 'superseded', updated_by = 1 WHERE id = :id",
        {'id': application.id},
    )


async def test_a_document_can_be_uploaded_before_its_owner_exists(db_session):
    await db_session.execute(
        text(
            'INSERT INTO documents (kind, storage_key, file_name, content_type, size_bytes, '
            "created_by) VALUES ('order', 'k-unowned', 'order.pdf', 'application/pdf', 10, 1)"
        )
    )


@pytest.mark.parametrize(
    ('owner_type', 'owner_id', 'owner_key'),
    [
        ('adverse_action', None, None),  # an owner type with no owner
        ('state', 1, None),  # a state is keyed by its code
        ('adverse_action', None, 'KS'),  # other owners are keyed by id
        (None, 1, None),  # an owner with no type
    ],
)
async def test_a_document_owner_is_complete_and_keyed_correctly(
    db_session, owner_type, owner_id, owner_key
):
    await assert_rejected(
        db_session,
        'INSERT INTO documents (owner_type, owner_id, owner_key, kind, storage_key, file_name, '
        "content_type, size_bytes, created_by) VALUES (:type, :id, :key, 'proof', 'k-bad', "
        "'a.pdf', 'application/pdf', 10, 1)",
        {'type': owner_type, 'id': owner_id, 'key': owner_key},
    )


async def test_a_state_can_own_a_document(db_session):
    await db_session.execute(
        text(
            'INSERT INTO documents (owner_type, owner_key, kind, storage_key, file_name, '
            "content_type, size_bytes, created_by) VALUES ('state', 'KS', "
            "'practice_requirements', 'k-ks', 'ks.pdf', 'application/pdf', 10, 1)"
        )
    )


async def test_a_fee_amount_is_scheduled_once_per_day(db_session):
    statement = (
        'INSERT INTO fees (state_code, fee_type, amount_cents, effective_from, created_by) '
        "VALUES (:state, 'privilege', 5000, '2026-10-01', 1)"
    )
    await db_session.execute(text(statement), {'state': 'KS'})
    await db_session.execute(text(statement), {'state': None})

    # The Commission's fee (state NULL) is unique too, not just state fees.
    await assert_rejected(db_session, statement, {'state': None})
    await assert_rejected(db_session, statement, {'state': 'KS'})


async def test_a_fee_cannot_be_negative_or_of_an_unknown_type(db_session):
    await assert_rejected(
        db_session,
        'INSERT INTO fees (state_code, fee_type, amount_cents, effective_from, created_by) '
        "VALUES ('KS', 'privilege', -1, '2026-10-01', 1)",
    )
    await assert_rejected(
        db_session,
        'INSERT INTO fees (state_code, fee_type, amount_cents, effective_from, created_by) '
        "VALUES ('KS', 'late_fee', 100, '2026-10-01', 1)",
    )


async def _next_privilege_number(db_session, state_code: str) -> str:
    result = await db_session.execute(
        text('SELECT next_privilege_number(:state, 1)'), {'state': state_code}
    )
    return result.scalar_one()


async def test_privilege_numbers_count_up_per_state(db_session):
    first_ks = await _next_privilege_number(db_session, 'KS')
    first_ok = await _next_privilege_number(db_session, 'OK')
    second_ks = await _next_privilege_number(db_session, 'KS')

    assert (first_ks, first_ok, second_ks) == ('PA-KS-000001', 'PA-OK-000001', 'PA-KS-000002')


async def test_privilege_numbers_grow_past_six_digits(db_session):
    await _next_privilege_number(db_session, 'KS')
    await db_session.execute(
        text("UPDATE privilege_number_sequences SET last_number = 999999 WHERE state_code = 'KS'")
    )

    assert await _next_privilege_number(db_session, 'KS') == 'PA-KS-1000000'


async def test_the_commission_can_deactivate_a_privilege(db_session):
    privilege = await make_issued_privilege(db_session)

    await db_session.execute(
        text(
            "UPDATE privileges SET administrator_status = 'inactive', "
            "deactivation_reason = 'commission_deactivated', deactivated_at = now(), "
            'updated_by = 1 WHERE id = :id'
        ),
        {'id': privilege.id},
    )
