"""Who may call a route: the declaration every ``/api`` route makes (ADR-0009, backlog D5)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from licensing_api.context import current_user
from licensing_api.errors import AppError, ErrorCode
from licensing_api.repo.user import User


class Role(StrEnum):
    """``chk_users_role``. Routes never check a role; they check the permissions it grants."""

    LICENSEE = 'licensee'
    STATE_STAFF = 'state_staff'
    STATE_ADMIN = 'state_admin'
    COMPACT_ADMIN = 'compact_admin'
    ADMIN = 'admin'


class Permission(StrEnum):
    # Granted by role, in every state.
    MANAGE_OWN_RECORD = 'manage_own_record'
    READ_GENERAL = 'read_general'
    COMPACT_ADMIN = 'compact_admin'
    # Granted per state in users.permissions (D5); READ_PRIVATE also comes with the Commission roles.
    READ_PRIVATE = 'read_private'
    READ_SSN = 'read_ssn'
    WRITE = 'write'
    ADMIN = 'admin'


# What each role may do everywhere. Commission roles can read any state's records but write none
# (constitution Principle VII); a state's writes come only from a per-state grant.
ROLE_PERMISSIONS: Mapping[Role, frozenset[Permission]] = {
    Role.LICENSEE: frozenset({Permission.MANAGE_OWN_RECORD}),
    Role.STATE_STAFF: frozenset({Permission.READ_GENERAL}),
    Role.STATE_ADMIN: frozenset({Permission.READ_GENERAL}),
    Role.COMPACT_ADMIN: frozenset(
        {Permission.READ_GENERAL, Permission.READ_PRIVATE, Permission.COMPACT_ADMIN}
    ),
    Role.ADMIN: frozenset(
        {Permission.READ_GENERAL, Permission.READ_PRIVATE, Permission.COMPACT_ADMIN}
    ),
}


@dataclass(frozen=True)
class RouteAccess:
    """A route's declaration. ``signed_in`` is False for a public route."""

    signed_in: bool
    permission: Permission | None = None
    state_param: str | None = None


# The attribute that marks a dependency as a route's access declaration, for route_access().
_ACCESS = '__route_access__'


def held_permissions(user: User, state_code: str | None) -> frozenset[str]:
    """Everything ``user`` may do in ``state_code``: their role's permissions plus that state's grants.

    A grant naming no ``Permission`` matches nothing, so a bad value in ``users.permissions`` denies.
    """
    granted = user.permissions.get(state_code.upper(), []) if state_code else []
    return ROLE_PERMISSIONS[Role(user.role)] | frozenset(granted)


def require(permission: Permission | None = None, *, state_param: str | None = None) -> Any:
    """``Depends`` admitting an active caller who holds ``permission``; yields the caller's ``User``.

    The state is the path parameter named ``state_param``, or the caller's own
    ``state_code``. With no ``permission``, any active user passes. Which rows the
    caller may see is the route's query's job (constitution Principle II).
    """
    access = RouteAccess(signed_in=True, permission=permission, state_param=state_param)

    async def check(request: Request, user: Annotated[User, Depends(current_user)]) -> User:
        if permission is None:
            return user
        state = request.path_params.get(state_param) if state_param else user.state_code
        if permission not in held_permissions(user, state):
            raise AppError(403, ErrorCode.Forbidden, [f'You need the {permission} permission'])
        return user

    setattr(check, _ACCESS, access)
    return Depends(check)


async def _open() -> None:
    return None


setattr(_open, _ACCESS, RouteAccess(signed_in=False))


def public() -> Any:
    """``Depends`` declaring a route open to anyone, signed in or not."""
    return Depends(_open)


def route_access(route: APIRoute) -> RouteAccess | None:
    """The access declaration in ``route``'s dependencies, or None when it has none."""
    return _find_access(route.dependant)


def _find_access(dependant: Dependant) -> RouteAccess | None:
    for dependency in dependant.dependencies:
        access = getattr(dependency.call, _ACCESS, None)
        if isinstance(access, RouteAccess):
            return access
        found = _find_access(dependency)
        if found is not None:
            return found
    return None
