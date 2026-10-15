"""require() and public(), through routes as clients call them (ADR-0009)."""

import uuid
from collections.abc import AsyncGenerator, Callable, Generator
from functools import partial
from typing import Annotated, Any
from unittest.mock import patch

import pytest
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from licensing_api.config import Settings, get_settings
from licensing_api.dependencies import get_db_session
from licensing_api.errors import (
    AppError,
    ErrorCode,
    app_error_handler,
    http_exception_handler,
    validation_error_handler,
)
from licensing_api.permissions import Permission, Role, public, require, route_access
from licensing_api.repo.user import User
from tests.conftest import TEST_SETTINGS
from tests.factories import make_user

router = APIRouter()


@router.get('/staff-only', name='Staff only', description='Any state staff')
async def staff_only(
    caller: Annotated[User, require(Role.STATE_STAFF, Role.STATE_ADMIN)],
) -> dict[str, str]:
    return {'email': caller.email}


@router.get(
    '/states/{state_code}/write',
    name='State write',
    description='Staff with write in the path state, or a compact admin',
    dependencies=[
        require(
            Role.STATE_STAFF,
            Role.STATE_ADMIN,
            Role.COMPACT_ADMIN,
            permission=Permission.WRITE,
            state_param='state_code',
        )
    ],
)
async def state_write(state_code: str) -> dict[str, str]:
    return {'state': state_code}


@router.get(
    '/own-state/write',
    name='Own state write',
    description='Staff with write in their own state',
    dependencies=[require(Role.STATE_STAFF, permission=Permission.WRITE)],
)
async def own_state_write() -> dict[str, str]:
    return {'ok': 'yes'}


@router.get('/open', name='Open', description='Anyone', dependencies=[public()])
async def open_route() -> dict[str, str]:
    return {'ok': 'yes'}


async def _staff_email(caller: Annotated[User, require(Role.STATE_STAFF)]) -> str:
    return caller.email


@router.get('/nested', name='Nested', description='Declares access through another dependency')
async def nested(email: Annotated[str, Depends(_staff_email)]) -> dict[str, str]:
    return {'email': email}


@router.get('/undeclared', name='Undeclared', description='Has a dependency, but no declaration')
async def undeclared(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str]:
    return {'environment': settings.environment}


def _test_app() -> FastAPI:
    test_app = FastAPI()
    test_app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    test_app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    test_app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    test_app.include_router(router)
    test_app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    return test_app


Guard = tuple[TestClient, Callable[..., User]]


@pytest.fixture
def guard(client, jwks) -> Generator[Guard]:
    """A client for the test routes, and a helper that adds a user visible to them; all rolled back."""
    test_app = _test_app()
    with (
        patch('licensing_api.auth._get_jwks', return_value=jwks),
        TestClient(test_app) as guard_client,
    ):

        async def _open() -> tuple[Any, Any, Any, AsyncSession]:
            engine = create_async_engine(TEST_SETTINGS.db_url, poolclass=NullPool)
            connection = await engine.connect()
            transaction = await connection.begin()
            session = AsyncSession(
                bind=connection, join_transaction_mode='create_savepoint', expire_on_commit=False
            )
            return engine, connection, transaction, session

        engine, connection, transaction, session = guard_client.portal.call(_open)

        async def _session() -> AsyncGenerator[AsyncSession]:
            yield session

        test_app.dependency_overrides[get_db_session] = _session

        def add_user(email: str, *, linked: bool = True, **fields: Any) -> User:
            fields.setdefault(
                'public_id', uuid.uuid5(uuid.NAMESPACE_URL, email) if linked else None
            )
            return guard_client.portal.call(partial(make_user, session, email=email, **fields))

        try:
            yield guard_client, add_user
        finally:

            async def _close() -> None:
                await session.close()
                await transaction.rollback()
                await connection.close()
                await engine.dispose()

            guard_client.portal.call(_close)


def _staff(add_user: Callable[..., User], email: str, permissions: dict[str, list[str]]) -> User:
    return add_user(email, role='state_staff', state_code='KS', permissions=permissions)


def test_a_listed_role_is_admitted(guard, auth_header):
    client, add_user = guard
    _staff(add_user, 'staff@example.com', {})

    response = client.get('/staff-only', headers=auth_header('staff@example.com'))

    assert response.status_code == 200
    assert response.json() == {'email': 'staff@example.com'}


def test_an_unlisted_role_is_forbidden(guard, auth_header):
    client, add_user = guard
    add_user('pa@example.com', role='licensee')

    response = client.get('/staff-only', headers=auth_header('pa@example.com'))

    assert response.status_code == 403
    assert response.json() == {
        'code': ErrorCode.Forbidden,
        'details': ['Your role cannot use this route'],
    }


@pytest.mark.parametrize(
    ('permissions', 'path', 'status'),
    [
        ({'KS': ['write']}, '/states/KS/write', 200),
        ({'KS': ['write']}, '/states/ks/write', 200),
        ({'KS': ['write']}, '/states/NE/write', 403),
        ({'KS': ['read_private']}, '/states/KS/write', 403),
        ({'NE': ['write']}, '/states/KS/write', 403),
    ],
)
def test_state_staff_need_the_permission_in_the_path_state(
    guard, auth_header, permissions, path, status
):
    client, add_user = guard
    _staff(add_user, 'staff@example.com', permissions)

    response = client.get(path, headers=auth_header('staff@example.com'))

    assert response.status_code == status


@pytest.mark.parametrize(
    ('permissions', 'status'), [({'KS': ['write']}, 200), ({'NE': ['write']}, 403)]
)
def test_state_staff_need_the_permission_in_their_own_state(
    guard, auth_header, permissions, status
):
    client, add_user = guard
    _staff(add_user, 'staff@example.com', permissions)

    response = client.get('/own-state/write', headers=auth_header('staff@example.com'))

    assert response.status_code == status


def test_a_compact_admin_passes_state_checks_only_where_listed(guard, auth_header):
    client, add_user = guard
    add_user('commission@example.com', role='compact_admin')
    headers = auth_header('commission@example.com')

    assert client.get('/states/KS/write', headers=headers).status_code == 200
    assert client.get('/staff-only', headers=headers).status_code == 403


def test_an_unknown_user_is_not_found(guard, auth_header):
    client, _ = guard

    response = client.get('/staff-only', headers=auth_header('nobody@example.com'))

    assert response.status_code == 403
    assert response.json()['code'] == ErrorCode.UserNotFound


def test_an_inactive_user_is_refused(guard, auth_header):
    client, add_user = guard
    add_user('gone@example.com', role='state_staff', state_code='KS', is_active=False)

    response = client.get('/staff-only', headers=auth_header('gone@example.com'))

    assert response.status_code == 403
    assert response.json()['code'] == ErrorCode.UserInactive


def test_first_sign_in_links_the_token_to_the_user_by_email(guard, auth_header):
    client, add_user = guard
    user = add_user('new@example.com', linked=False, role='state_staff', state_code='KS')

    response = client.get('/staff-only', headers=auth_header('new@example.com'))

    assert response.status_code == 200
    assert user.public_id == uuid.uuid5(uuid.NAMESPACE_URL, 'new@example.com')


def test_an_inactive_user_is_not_linked(guard, auth_header):
    client, add_user = guard
    user = add_user(
        'gone@example.com', linked=False, role='state_staff', state_code='KS', is_active=False
    )

    response = client.get('/staff-only', headers=auth_header('gone@example.com'))

    assert response.json()['code'] == ErrorCode.UserInactive
    assert user.public_id is None


def test_a_user_linked_to_another_sub_is_not_this_caller(guard, auth_header):
    client, add_user = guard
    add_user('shared@example.com', public_id=uuid.uuid4(), role='state_staff', state_code='KS')

    response = client.get('/staff-only', headers=auth_header('shared@example.com'))

    assert response.status_code == 403
    assert response.json()['code'] == ErrorCode.UserNotFound


def test_a_public_route_needs_no_token(guard):
    client, _ = guard

    assert client.get('/open').status_code == 200


def test_require_needs_a_role():
    with pytest.raises(ValueError, match='at least one role'):
        require()


def test_a_permission_needs_a_staff_role():
    with pytest.raises(ValueError, match='only to state staff'):
        require(Role.COMPACT_ADMIN, permission=Permission.WRITE)


def test_route_access_reads_each_declaration():
    access = {
        route.path: route_access(route)
        for route in _test_app().routes
        if hasattr(route, 'dependant')
    }

    assert access['/open'] is not None and access['/open'].roles is None
    assert access['/states/{state_code}/write'] is not None
    assert access['/states/{state_code}/write'].state_param == 'state_code'
    assert access['/staff-only'] is not None
    assert access['/staff-only'].roles == {Role.STATE_STAFF, Role.STATE_ADMIN}
    assert access['/undeclared'] is None
    assert access['/nested'] is not None
    assert access['/nested'].roles == {Role.STATE_STAFF}
