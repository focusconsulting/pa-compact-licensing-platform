"""Core entities from the F-02 phase 2 migrations: the rules the database enforces."""

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from licensing_api.repo.history import PractitionerHistory
from licensing_api.repo.participation_application import ApplicationKind, ApplicationStatus
from licensing_api.repo.practitioner import PractitionerSsn
from tests.factories import (
    assert_rejected,
    make_application,
    make_eligible_application,
    make_practitioner,
    make_qualifying_license,
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
