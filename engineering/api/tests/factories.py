"""Builders that insert one valid row with overridable fields, for tests using ``db_session``."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

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
