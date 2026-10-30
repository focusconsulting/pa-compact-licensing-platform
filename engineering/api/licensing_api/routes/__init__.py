"""The persona namespaces every ``/api`` route lives under (backlog D3, F-03).

A resource module's router carries no namespace; it is listed here under the
namespace of the people who call it. ``tests/test_route_access.py`` holds each
namespace to its rule, which ``engineering/docs/roles-and-permissions.md`` lists.
"""

from collections.abc import Mapping, Sequence

from fastapi import APIRouter

from licensing_api.errors import ErrorResponse
from licensing_api.routes import audit, health, user

NAMESPACES: Mapping[str, Sequence[APIRouter]] = {
    # A PA's own record, and the signed-in user's own account.
    '/me': [user.router],
    # Anyone, signed in or not: verification and published configuration.
    '/public': [],
    # One state's staff, acting in the state named by the path.
    '/states/{state_code}': [],
    # Commission staff, across every state.
    '/commission': [audit.router],
    # The system operator.
    '/admin': [],
}

# A 422 carries ErrorResponse (errors.validation_error_handler), not FastAPI's default body.
api = APIRouter(prefix='/api', responses={422: {'model': ErrorResponse}})
# If we decide to exclude /health routes from /api, that is make them private,
# include the health.router directly to app. Then update the paths in
# infrastructure/iac/components/app/opentofu/ecs.tf
api.include_router(health.router)
for prefix, routers in NAMESPACES.items():
    for router in routers:
        api.include_router(router, prefix=prefix, tags=[prefix.split('/')[1]])
