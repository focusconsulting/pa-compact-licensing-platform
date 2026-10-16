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
from licensing_api.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    Role,
    public,
    require,
    route_access,
)
from licensing_api.repo.user import User
from tests.conftest import TEST_SETTINGS
from tests.factories import make_user

router = APIRouter()


@router.get('/signed-in', name='Signed in', description='Any active user')
async def signed_in(caller: Annotated[User, require()]) -> dict[str, str]:
    return {'email': caller.email}


@router.get(
    '/states/{state_code}/write',
    name='State write',
    description='Write in the path state',
    dependencies=[require(Permission.WRITE, state_param='state_code')],
)
async def state_write(state_code: str) -> dict[str, str]:
    return {'state': state_code}


@router.get(
    '/states/{state_code}/private',
    name='State private read',
    description='Read private data in the path state',
    dependencies=[require(Permission.READ_PRIVATE, state_param='state_code')],
)
async def state_private(state_code: str) -> dict[str, str]:
    return {'state': state_code}


@router.get(
    '/own-state/write',
    name='Own state write',
    description="Write in the caller's own state",
    dependencies=[require(Permission.WRITE)],
)
async def own_state_write() -> dict[str, str]:
    return {'ok': 'yes'}


@router.get(
    '/me/record',
    name='Own record',
    description='A PA managing their own record',
    dependencies=[require(Permission.MANAGE_OWN_RECORD)],
)
async def own_record() -> dict[str, str]:
    return {'ok': 'yes'}


@router.get('/open', name='Open', description='Anyone', dependencies=[public()])
async def open_route() -> dict[str, str]:
    return {'ok': 'yes'}


async def _writer_email(caller: Annotated[User, require(Permission.WRITE)]) -> str:
    return caller.email


@router.get('/nested', name='Nested', description='Declares access through another dependency')
async def nested(email: Annotated[str, Depends(_writer_email)]) -> dict[str, str]:
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


def test_any_active_user_passes_a_route_with_no_permission(guard, auth_header):
    client, add_user = guard
    add_user('pa@example.com', role='licensee')

    response = client.get('/signed-in', headers=auth_header('pa@example.com'))

    assert response.status_code == 200
    assert response.json() == {'email': 'pa@example.com'}


@pytest.mark.parametrize(
    ('permissions', 'path', 'status'),
    [
        ({'KS': ['write']}, '/states/KS/write', 200),
        ({'KS': ['write']}, '/states/ks/write', 200),
        ({'KS': ['write']}, '/states/NE/write', 403),
        ({'KS': ['read_private']}, '/states/KS/write', 403),
        ({'NE': ['write']}, '/states/KS/write', 403),
        ({'KS': ['not_a_permission']}, '/states/KS/write', 403),
    ],
)
def test_state_staff_need_the_grant_in_the_path_state(
    guard, auth_header, permissions, path, status
):
    client, add_user = guard
    _staff(add_user, 'staff@example.com', permissions)

    response = client.get(path, headers=auth_header('staff@example.com'))

    assert response.status_code == status


@pytest.mark.parametrize(
    ('permissions', 'status'), [({'KS': ['write']}, 200), ({'NE': ['write']}, 403)]
)
def test_state_staff_need_the_grant_in_their_own_state(guard, auth_header, permissions, status):
    client, add_user = guard
    _staff(add_user, 'staff@example.com', permissions)

    response = client.get('/own-state/write', headers=auth_header('staff@example.com'))

    assert response.status_code == status


def test_a_missing_permission_is_forbidden(guard, auth_header):
    client, add_user = guard
    _staff(add_user, 'staff@example.com', {})

    response = client.get('/states/KS/write', headers=auth_header('staff@example.com'))

    assert response.status_code == 403
    assert response.json() == {
        'code': ErrorCode.Forbidden,
        'details': ['You need the write permission'],
    }


def test_a_commission_user_reads_any_state_but_writes_none(guard, auth_header):
    client, add_user = guard
    add_user('commission@example.com', role='compact_admin')
    headers = auth_header('commission@example.com')

    assert client.get('/states/KS/private', headers=headers).status_code == 200
    assert client.get('/states/NE/private', headers=headers).status_code == 200
    assert client.get('/states/KS/write', headers=headers).status_code == 403


def test_only_a_licensee_manages_their_own_record(guard, auth_header):
    client, add_user = guard
    add_user('pa@example.com', role='licensee')
    _staff(add_user, 'staff@example.com', {'KS': ['write', 'admin']})

    assert client.get('/me/record', headers=auth_header('pa@example.com')).status_code == 200
    assert client.get('/me/record', headers=auth_header('staff@example.com')).status_code == 403


def test_an_unknown_caller_keeps_its_error_code(guard, auth_header):
    client, _ = guard

    response = client.get('/signed-in', headers=auth_header('nobody@example.com'))

    assert response.status_code == 403
    assert response.json()['code'] == ErrorCode.UserNotFound


def test_a_public_route_needs_no_token(guard):
    client, _ = guard

    assert client.get('/open').status_code == 200


def test_every_role_has_permissions():
    assert set(ROLE_PERMISSIONS) == set(Role)


def test_route_access_reads_each_declaration():
    access = {
        route.path: route_access(route)
        for route in _test_app().routes
        if hasattr(route, 'dependant')
    }

    assert access['/open'] is not None and access['/open'].signed_in is False
    assert access['/signed-in'] is not None and access['/signed-in'].permission is None
    assert access['/states/{state_code}/write'] is not None
    assert access['/states/{state_code}/write'].permission == Permission.WRITE
    assert access['/states/{state_code}/write'].state_param == 'state_code'
    assert access['/nested'] is not None and access['/nested'].permission == Permission.WRITE
    assert access['/undeclared'] is None
