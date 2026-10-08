"""Builders that insert one valid row with overridable fields, for tests using ``db_session``."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from licensing_api.repo.adverse_action import AdverseAction, AdverseActionTarget
from licensing_api.repo.participation_application import (
    ApplicationStatus,
    ParticipationApplication,
)
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.privilege import Privilege
from licensing_api.repo.privilege_request import PrivilegeRequest, PrivilegeRequestStatus
from licensing_api.repo.qualifying_license import LicenseStatus, QualifyingLicense
from licensing_api.repo.user import SYSTEM_USER_EMAIL, User


async def system_user_id(session: AsyncSession) -> int:
    result = await session.execute(select(User.id).where(User.email == SYSTEM_USER_EMAIL))
    return result.scalar_one()


async def make_user(session: AsyncSession, **overrides: Any) -> User:
    fields: dict[str, Any] = {
        'email': f'{uuid.uuid4().hex}@example.com',
        'public_id': None,
        'given_name': 'Test',
        'family_name': 'User',
        'role': 'compact_admin',
        'state_code': None,
        'is_active': True,
        'created_by': await system_user_id(session),
    }
    fields.update(overrides)
    user = User(**fields)
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def assert_rejected(
    session: AsyncSession, statement: str, params: dict[str, Any] | None = None
) -> None:
    """Asserts the database rejects a statement, rolling back only to a savepoint so the test can continue."""
    with pytest.raises(DBAPIError):
        async with session.begin_nested():
            await session.execute(text(statement), params or {})


async def make_practitioner(session: AsyncSession, **overrides: Any) -> Practitioner:
    system_id = await system_user_id(session)
    user = await make_user(session, role='licensee')
    fields: dict[str, Any] = {
        'user_id': user.id,
        'legal_first_name': 'Pat',
        'legal_last_name': 'Assistant',
        'date_of_birth': date(1990, 1, 1),
        'created_by': system_id,
    }
    fields.update(overrides)
    return await _add(session, Practitioner(**fields))


async def make_qualifying_license(
    session: AsyncSession, practitioner: Practitioner, **overrides: Any
) -> QualifyingLicense:
    fields: dict[str, Any] = {
        'practitioner_id': practitioner.id,
        'state_code': 'KS',
        'license_number': uuid.uuid4().hex[:10],
        'state_reported_status': LicenseStatus.ACTIVE,
        'status_effective_on': date(2024, 1, 1),
        'issued_on': date(2024, 1, 1),
        'expires_on': date(2027, 12, 31),
        'is_unrestricted': True,
        'created_by': await system_user_id(session),
    }
    fields.update(overrides)
    return await _add(session, QualifyingLicense(**fields))


async def make_application(
    session: AsyncSession, practitioner: Practitioner, **overrides: Any
) -> ParticipationApplication:
    fields: dict[str, Any] = {
        'practitioner_id': practitioner.id,
        'sql_state_code': 'KS',
        'created_by': await system_user_id(session),
    }
    fields.update(overrides)
    return await _add(session, ParticipationApplication(**fields))


async def make_eligible_application(
    session: AsyncSession, practitioner: Practitioner, **overrides: Any
) -> ParticipationApplication:
    """An application the SQL has decided eligible, with every field that decision requires (FLOW-02)."""
    system_id = await system_user_id(session)
    license = await make_qualifying_license(session, practitioner)
    decided = datetime(2026, 6, 1, tzinfo=timezone.utc)
    fields: dict[str, Any] = {
        'qualifying_license_id': license.id,
        'status': ApplicationStatus.ELIGIBLE,
        'opened_at': decided,
        'license_verified_at': decided,
        'license_verified_by': system_id,
        'cbc_completed_on': date(2026, 5, 20),
        'decided_at': decided,
        'decided_by': system_id,
    }
    fields.update(overrides)
    return await make_application(session, practitioner, **fields)


async def make_submitted_request(
    session: AsyncSession, application: ParticipationApplication, **overrides: Any
) -> PrivilegeRequest:
    """A paid request received by the remote state, with the license expiry pinned (Rule 3 §3.5(a))."""
    fields: dict[str, Any] = {
        'participation_application_id': application.id,
        'practitioner_id': application.practitioner_id,
        'remote_state_code': 'OK',
        'qualifying_license_id': application.qualifying_license_id,
        'status': PrivilegeRequestStatus.SUBMITTED,
        'ql_expires_on_snapshot': date(2027, 12, 31),
        'submitted_at': datetime(2026, 6, 2, tzinfo=timezone.utc),
        'created_by': await system_user_id(session),
    }
    fields.update(overrides)
    return await _add(session, PrivilegeRequest(**fields))


async def make_privilege(
    session: AsyncSession, request: PrivilegeRequest, **overrides: Any
) -> Privilege:
    """Issues the request: marks it issued and creates the privilege with the pinned expiry."""
    system_id = await system_user_id(session)
    issued = datetime(2026, 6, 3, tzinfo=timezone.utc)
    request.status = PrivilegeRequestStatus.ISSUED
    request.decided_at = issued
    request.decided_by = system_id
    request.updated_by = system_id
    assert request.ql_expires_on_snapshot is not None
    fields: dict[str, Any] = {
        'privilege_request_id': request.id,
        'practitioner_id': request.practitioner_id,
        'remote_state_code': request.remote_state_code,
        'qualifying_license_id': request.qualifying_license_id,
        'privilege_number': f'PA-{request.remote_state_code}-{uuid.uuid4().hex[:6]}',
        'issued_at': issued,
        'expires_on': request.ql_expires_on_snapshot,
        'created_by': system_id,
    }
    fields.update(overrides)
    return await _add(session, Privilege(**fields))


async def make_issued_privilege(session: AsyncSession, **overrides: Any) -> Privilege:
    """A practitioner, eligible application, submitted request, and issued privilege in one call."""
    application = await make_eligible_application(session, await make_practitioner(session))
    request = await make_submitted_request(session, application)
    return await make_privilege(session, request, **overrides)


async def make_adverse_action(
    session: AsyncSession, privilege: Privilege, **overrides: Any
) -> AdverseAction:
    """An adverse action against a privilege by default; override ``against`` and the target for a license."""
    fields: dict[str, Any] = {
        'practitioner_id': privilege.practitioner_id,
        'reporting_state_code': privilege.remote_state_code,
        'against': AdverseActionTarget.PRIVILEGE,
        'privilege_id': privilege.id,
        'action_type_code': 'suspension',
        'summary': 'Suspended pending review.',
        'ordered_on': date(2026, 7, 1),
        'effective_from': date(2026, 7, 1),
        'created_by': await system_user_id(session),
    }
    fields.update(overrides)
    return await _add(session, AdverseAction(**fields))


async def _add[T](session: AsyncSession, row: T) -> T:
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row
