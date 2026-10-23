"""Every /api route declares who may call it (ADR-0009) and sits in a persona namespace whose rule it meets (backlog D3)."""

from collections.abc import Callable, Iterable
from typing import Annotated

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from licensing_api.__main__ import app
from licensing_api.permissions import Permission, RouteAccess, public, require, route_access
from licensing_api.repo.user import User
from licensing_api.routes import NAMESPACES

_HEALTH = '/api/health'

# Each namespace's rule: None when a route's declaration meets it, else what is wrong.
_RULES: dict[str, Callable[[RouteAccess], str | None]] = {
    '/me': lambda access: None if access.signed_in else 'must be signed in',
    '/public': lambda access: None if not access.signed_in else 'must be public()',
    '/states/{state_code}': lambda access: (
        None
        if access.signed_in and access.state_param == 'state_code'
        else "must declare state_param='state_code'"
    ),
    # read_private is not enough: with no state in the path it is checked in the caller's own
    # state, so a state staff member's grant would pass.
    '/commission': lambda access: (
        None if access.permission == Permission.COMPACT_ADMIN else 'must require compact_admin'
    ),
    '/admin': lambda access: (
        None if access.permission == Permission.SYSTEM_ADMIN else 'must require system_admin'
    ),
}


def _api_routes(routes: Iterable[object]) -> list[APIRoute]:
    return [r for r in routes if isinstance(r, APIRoute) and r.path.startswith('/api')]


def _namespace(path: str) -> str | None:
    for prefix in NAMESPACES:
        full = f'/api{prefix}'
        if path == full or path.startswith(f'{full}/'):
            return prefix
    return None


def _violations(routes: Iterable[object]) -> list[str]:
    found = []
    for route in _api_routes(routes):
        access = route_access(route)
        if access is None:
            found.append(f'{route.path}: declares neither require() nor public()')
        elif not route.path.startswith(_HEALTH):
            namespace = _namespace(route.path)
            problem = 'is in no namespace' if namespace is None else _RULES[namespace](access)
            if problem is not None:
                found.append(f'{route.path}: {problem}')
    return found


def test_the_app_has_api_routes():
    assert _api_routes(app.routes)


def test_every_namespace_has_a_rule():
    assert set(_RULES) == set(NAMESPACES)


def test_every_api_route_meets_its_namespace_rule():
    assert _violations(app.routes) == []


def test_a_state_param_names_a_path_parameter():
    for route in _api_routes(app.routes):
        access = route_access(route)
        if access is not None and access.state_param is not None:
            assert f'{{{access.state_param}}}' in route.path, route.path


def _app_with(prefix: str, *, access: object | None = None, dependencies: list | None = None):
    """An app with one GET route under ``/api{prefix}``, declared with ``access`` or ``dependencies``."""
    router = APIRouter(dependencies=dependencies or [])
    if access is None:

        @router.get('/thing', name='Thing', description='A route under test')
        async def thing() -> None:
            return None
    else:

        @router.get('/thing', name='Thing', description='A route under test')
        async def thing_with_caller(caller: Annotated[User, access]) -> None:
            return None

    test_app = FastAPI()
    test_app.include_router(router, prefix=f'/api{prefix}')
    return test_app


@pytest.mark.parametrize(
    ('prefix', 'access', 'dependencies'),
    [
        ('/me', require(), None),
        ('/public', None, [public()]),
        ('/states/{state_code}', require(Permission.WRITE, state_param='state_code'), None),
        ('/commission', require(Permission.COMPACT_ADMIN), None),
        ('/admin', require(Permission.SYSTEM_ADMIN), None),
        ('/health', None, [public()]),
    ],
)
def test_a_route_meeting_its_rule_passes(prefix, access, dependencies):
    assert _violations(_app_with(prefix, access=access, dependencies=dependencies).routes) == []


@pytest.mark.parametrize(
    ('prefix', 'access', 'dependencies', 'problem'),
    [
        ('/elsewhere', require(), None, 'is in no namespace'),
        ('/me', None, [public()], 'must be signed in'),
        ('/public', require(), None, 'must be public()'),
        ('/states/{state_code}', require(Permission.WRITE), None, 'state_param'),
        ('/commission', require(Permission.READ_PRIVATE), None, 'must require compact_admin'),
        ('/admin', require(Permission.COMPACT_ADMIN), None, 'must require system_admin'),
        ('/me', None, None, 'declares neither'),
    ],
)
def test_a_route_breaking_its_rule_fails(prefix, access, dependencies, problem):
    (violation,) = _violations(_app_with(prefix, access=access, dependencies=dependencies).routes)

    assert problem in violation
