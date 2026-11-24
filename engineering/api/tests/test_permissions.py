"""require() and public(), through routes as clients call them (ADR-0009)."""

import re
import uuid
from collections.abc import AsyncGenerator, Callable, Generator
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Annotated, Any
from unittest.mock import patch

import pytest
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute, iter_route_contexts
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_object_session, create_async_engine
from sqlalchemy.pool import NullPool

from licensing_api.__main__ import app
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
    GRANTABLE,
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


@router.get(
    '/commission/ssn',
    name='Commission SSN',
    description='Reveal an SSN across every state',
    dependencies=[require(Permission.COMPACT_ADMIN), require(Permission.READ_SSN)],
)
async def commission_ssn() -> dict[str, str]:
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
    test_app.include_router(_matrix_router())
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


async def _flush(user: User) -> None:
    session = async_object_session(user)
    assert session is not None
    await session.flush()


async def _set_permissions(user: User, permissions: dict[str, list[str]]) -> None:
    user.permissions = permissions
    await _flush(user)


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


@pytest.mark.parametrize('role', ['compact_admin', 'admin'])
def test_a_commission_user_has_no_standing_in_a_state_path(guard, auth_header, role):
    client, add_user = guard
    add_user('commission@example.com', role=role, permissions={'KS': ['read_private']})

    response = client.get('/states/KS/private', headers=auth_header('commission@example.com'))

    assert response.status_code == 403
    assert response.json() == {'code': ErrorCode.Forbidden, 'details': ['You have no access to KS']}


@pytest.mark.parametrize(
    ('permissions', 'status'),
    [
        ({}, 403),
        ({'MO': ['read_private']}, 200),
        ({'MO': ['not_a_permission']}, 403),
        ({'MO': ['read_general']}, 403),
    ],
)
def test_staff_have_standing_in_another_state_only_through_a_grant_there(
    guard, auth_header, permissions, status
):
    client, add_user = guard
    _staff(add_user, 'staff@example.com', permissions)

    response = client.get('/states/MO/private', headers=auth_header('staff@example.com'))

    assert response.status_code == status


@pytest.mark.parametrize(
    ('role', 'permissions', 'status'),
    [
        ('compact_admin', {'*': ['read_ssn']}, 200),
        ('compact_admin', {}, 403),
        ('compact_admin', {'KS': ['read_ssn']}, 403),
        ('admin', {'*': ['read_ssn']}, 403),
        ('licensee', {'*': ['read_ssn']}, 403),
    ],
)
def test_only_a_compact_admin_holds_commission_grants(
    guard, auth_header, role, permissions, status
):
    client, add_user = guard
    add_user('commission@example.com', role=role, permissions=permissions)

    response = client.get('/commission/ssn', headers=auth_header('commission@example.com'))

    assert response.status_code == status


def test_the_commission_key_is_not_a_state(guard, auth_header):
    client, add_user = guard
    add_user('commission@example.com', role='compact_admin', permissions={'*': ['read_ssn']})

    response = client.get('/states/*/private', headers=auth_header('commission@example.com'))

    assert response.status_code == 403


@pytest.mark.parametrize('granted', ['compact_admin', 'system_admin', 'manage_own_record'])
def test_a_role_permission_cannot_be_granted(guard, auth_header, granted):
    client, add_user = guard
    _staff(add_user, 'staff@example.com', {'KS': [granted]})

    response = client.get('/commission/ssn', headers=auth_header('staff@example.com'))

    assert response.status_code == 403


def test_a_permission_change_takes_effect_on_the_next_request(guard, auth_header):
    client, add_user = guard
    staff = _staff(add_user, 'staff@example.com', {})
    headers = auth_header('staff@example.com')
    assert client.get('/states/KS/write', headers=headers).status_code == 403

    client.portal.call(_set_permissions, staff, {'KS': ['write']})
    assert client.get('/states/KS/write', headers=headers).status_code == 200

    client.portal.call(_set_permissions, staff, {})
    assert client.get('/states/KS/write', headers=headers).status_code == 403


def test_a_deactivated_user_is_refused_on_the_next_request(guard, auth_header):
    client, add_user = guard
    staff = _staff(add_user, 'staff@example.com', {'KS': ['write']})
    headers = auth_header('staff@example.com')
    assert client.get('/states/KS/write', headers=headers).status_code == 200

    staff.is_active = False
    client.portal.call(_flush, staff)
    response = client.get('/states/KS/write', headers=headers)

    assert response.status_code == 403
    assert response.json()['code'] == ErrorCode.UserInactive


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


def test_every_role_has_permissions_and_grants():
    assert set(ROLE_PERMISSIONS) == set(Role)
    assert set(GRANTABLE) == set(Role)


def test_route_access_reads_each_declaration():
    access = {
        route.path: route_access(route)
        for route in iter_route_contexts(_test_app().routes)
        if isinstance(route.original_route, APIRoute)
    }

    assert access['/open'] is not None and access['/open'].signed_in is False
    assert access['/signed-in'] is not None and access['/signed-in'].permission is None
    assert access['/states/{state_code}/write'] is not None
    assert access['/states/{state_code}/write'].permission == Permission.WRITE
    assert access['/states/{state_code}/write'].state_param == 'state_code'
    assert access['/nested'] is not None and access['/nested'].permission == Permission.WRITE
    assert access['/undeclared'] is None


_ROLES_DOC = Path(__file__).parents[2] / 'docs/roles-and-permissions.md'


def _doc_table(heading: str) -> dict[str, list[str]]:
    """The rows under ``## heading``: each row's first-column code name to its other code names."""
    section = _ROLES_DOC.read_text().split(f'## {heading}\n')[1].split('\n## ')[0]
    rows = (line.split('|')[1:-1] for line in section.splitlines() if line.startswith('| `'))
    return {
        re.findall(r'`([a-z_]+)`', cells[0])[0]: re.findall(r'`([a-z_]+)`', cells[-1])
        for cells in rows
    }


def test_the_roles_doc_matches_role_permissions():
    documented = {role: set(held) for role, held in _doc_table('Roles').items()}
    assert documented == {
        role.value: {p.value for p in held} for role, held in ROLE_PERMISSIONS.items()
    }


def test_the_roles_doc_describes_every_permission():
    assert set(_doc_table('Permissions')) == {permission.value for permission in Permission}


@dataclass(frozen=True)
class MatrixRow:
    """One row of the permission matrix: what the route family declares, and each role's cell."""

    index: int
    family: str
    namespace: str
    declares: tuple[str, ...]
    cells: dict[Role, str]


_NAMESPACES = ('/me', '/public', '/states', '/commission', '/admin')


def _matrix() -> list[MatrixRow]:
    section = _ROLES_DOC.read_text().split('## Permission matrix\n')[1].split('\n## ')[0]
    lines = [line for line in section.splitlines() if line.startswith('| ')][1:]
    rows: list[MatrixRow] = []
    namespace = ''
    for index, line in enumerate(lines):
        family, declares, _, *cells = (cell.strip() for cell in line.split('|')[1:-1])
        # A row with no path ("The private fields in those responses") continues the one above.
        namespace = next((n for n in _NAMESPACES if f'`{n}' in family), namespace)
        names = tuple(n for n in re.findall(r'`([a-z_]+)', declares) if n != 'st')
        public_cell = cells[0] if names == ('public',) else None
        rows.append(
            MatrixRow(
                index=index,
                family=family,
                namespace=namespace,
                declares=names,
                cells={role: public_cell or cell for role, cell in zip(Role, cells, strict=True)},
            )
        )
    return rows


MATRIX = _matrix()


def _path(row: MatrixRow, state: str = 'KS') -> str:
    return f'/matrix/{row.index}' + (f'/states/{state}' if row.namespace == '/states' else '')


def _matrix_router() -> APIRouter:
    matrix = APIRouter()
    for row in MATRIX:
        if row.declares == ('public',):
            dependencies = [public()]
        elif row.declares == ('require',):
            dependencies = [require()]
        else:
            state_param = 'state_code' if row.namespace == '/states' else None
            dependencies = [require(Permission(p), state_param=state_param) for p in row.declares]
        matrix.add_api_route(
            _path(row, '{state_code}'),
            open_route,
            name=f'Matrix row {row.index}',
            description=row.family,
            dependencies=dependencies,
        )
    return matrix


# Where each role holds grants: staff in their state, the Commission under '*' (ADR-0020).
_GRANT_KEY = {
    Role.LICENSEE: '*',
    Role.STATE_STAFF: 'KS',
    Role.STATE_ADMIN: 'KS',
    Role.COMPACT_ADMIN: '*',
    Role.ADMIN: '*',
}


def _cases() -> list[Any]:
    cases = []
    for row in MATRIX:
        for role, cell in row.cells.items():
            label = f'{row.index}-{role}'
            permissions = [p for p in row.declares if p in set(Permission)]
            granted = {_GRANT_KEY[role]: permissions}
            if cell == 'grant':
                cases.append(pytest.param(row, role, granted, 200, id=f'{label}-granted'))
                cases.append(pytest.param(row, role, {}, 403, id=f'{label}-not-granted'))
            elif cell == '—':
                # Refused even holding every grant the row names.
                cases.append(pytest.param(row, role, granted, 403, id=label))
            else:
                cases.append(pytest.param(row, role, {}, 200, id=label))
    return cases


@pytest.mark.parametrize(('row', 'role', 'permissions', 'status'), _cases())
def test_the_permission_matrix(guard, auth_header, row, role, permissions, status):
    client, add_user = guard
    state_code = 'KS' if role in (Role.STATE_STAFF, Role.STATE_ADMIN) else None
    add_user('caller@example.com', role=role, state_code=state_code, permissions=permissions)
    headers = auth_header('caller@example.com')

    assert client.get(_path(row), headers=headers).status_code == status
    if row.namespace == '/states':
        assert client.get(_path(row, 'MO'), headers=headers).status_code == 403


def test_the_permission_matrix_covers_every_namespace_and_role():
    assert {row.namespace for row in MATRIX} == set(_NAMESPACES)
    assert all(set(row.cells) == set(Role) for row in MATRIX)


def test_a_public_matrix_row_needs_no_token(guard):
    client, _ = guard

    for row in MATRIX:
        if row.declares == ('public',):
            assert client.get(_path(row)).status_code == 200


def test_every_api_route_declares_what_the_matrix_lists_for_its_namespace():
    declared = {
        (row.namespace, p)
        for row in MATRIX
        for p in row.declares
        if p in set(Permission) or p == 'public'
    } | {(row.namespace, None) for row in MATRIX if row.declares == ('require',)}
    found = set()
    for route in iter_route_contexts(app.routes):
        path = route.path or ''
        if not isinstance(route.original_route, APIRoute) or path.startswith('/api/health'):
            continue
        namespace = next((n for n in _NAMESPACES if path.startswith(f'/api{n}')), None)
        access = route_access(route)
        if namespace is None or access is None:
            continue
        found.add((namespace, 'public' if not access.signed_in else access.permission))

    assert found
    assert found <= declared
