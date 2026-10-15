"""Every /api route declares who may call it (ADR-0009). A route without require() or public() fails here."""

from fastapi.routing import APIRoute

from licensing_api.__main__ import app
from licensing_api.permissions import route_access

_API_ROUTES = [
    route for route in app.routes if isinstance(route, APIRoute) and route.path.startswith('/api')
]


def test_the_app_has_api_routes():
    assert _API_ROUTES


def test_every_api_route_declares_its_access():
    undeclared = [route.path for route in _API_ROUTES if route_access(route) is None]

    assert undeclared == []


def test_a_state_param_names_a_path_parameter():
    for route in _API_ROUTES:
        access = route_access(route)
        if access is not None and access.state_param is not None:
            assert f'{{{access.state_param}}}' in route.path, route.path
