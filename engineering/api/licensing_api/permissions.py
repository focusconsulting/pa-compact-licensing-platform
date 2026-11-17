"""Who may call a route: the declaration every ``/api`` route makes (ADR-0009, backlog D5)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.dependencies.models import Dependant
from fastapi.routing import RouteContext

from licensing_api.context import current_user
from licensing_api.errors import AppError, ErrorCode
from licensing_api.repo.user import User


class Role(StrEnum):
    """``chk_users_role``. Routes never check a role; they check the permissions it grants."""

    # A PA. Manages their own profile, applications, payments, and privileges.
    LICENSEE = 'licensee'
    # A state licensing board employee, tied to one state. What they may do there comes from
    # their per-state grants.
    STATE_STAFF = 'state_staff'
    # State staff who also manage their own state's users and settings (fees, proofs, contacts).
    STATE_ADMIN = 'state_admin'
    # Commission staff. Read every state, configure the compact, and override a privilege.
    COMPACT_ADMIN = 'compact_admin'
    # System operator: Focus during the pilot, then Commission IT.
    ADMIN = 'admin'


class Permission(StrEnum):
    """What a caller may do: granted by role in every state (``ROLE_PERMISSIONS``), or per state in ``users.permissions``."""

    # Granted by role, in every state.
    # Act on the caller's own practitioner record; the route's query limits it to theirs.
    MANAGE_OWN_RECORD = 'manage_own_record'
    # See the non-private fields of practitioners, licenses, and privileges. Every staff role has it.
    READ_GENERAL = 'read_general'
    # Configure the compact: fees, which states are live, report lists, privilege overrides.
    COMPACT_ADMIN = 'compact_admin'
    # Operate the system: the /admin routes. Only the admin role holds it.
    SYSTEM_ADMIN = 'system_admin'
    # Granted per state in users.permissions (D5); READ_PRIVATE also comes with the Commission roles.
    # See private fields: date of birth, address, and the SSN's last four digits.
    READ_PRIVATE = 'read_private'
    # Reveal a full SSN. Every reveal is audited (ADR-0007).
    READ_SSN = 'read_ssn'
    # Change the state's records: licenses, eligibility decisions, privileges, adverse actions.
    WRITE = 'write'
    # Manage the state's staff users, their grants, and the state's settings.
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
        {
            Permission.READ_GENERAL,
            Permission.READ_PRIVATE,
            Permission.COMPACT_ADMIN,
            Permission.SYSTEM_ADMIN,
        }
    ),
}


# The users.permissions key for a Commission user's grants (ADR-0020). It names no state, so it
# gives no standing in one.
COMMISSION_KEY = '*'

_STATE_GRANTS = frozenset(
    {Permission.READ_PRIVATE, Permission.READ_SSN, Permission.WRITE, Permission.ADMIN}
)

# What each role may be granted: staff per state, a compact_admin under COMMISSION_KEY. Any other
# grant matches nothing, so a bad value in users.permissions denies rather than escalates.
GRANTABLE: Mapping[Role, frozenset[Permission]] = {
    Role.LICENSEE: frozenset(),
    Role.STATE_STAFF: _STATE_GRANTS,
    Role.STATE_ADMIN: _STATE_GRANTS,
    Role.COMPACT_ADMIN: frozenset({Permission.READ_SSN}),
    Role.ADMIN: frozenset(),
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
    """Everything ``user`` may do in ``state_code``: their role's permissions plus their grants there.

    With no state, the grants are the ones held under ``COMMISSION_KEY``.
    """
    key = COMMISSION_KEY if state_code is None else state_code.upper()
    return ROLE_PERMISSIONS[Role(user.role)] | _grants(user, key)


def has_standing(user: User, state_code: str) -> bool:
    """Whether ``user`` belongs to ``state_code``: it is their state, or they hold a grant there (ADR-0020)."""
    state_code = state_code.upper()
    if state_code == COMMISSION_KEY:
        return False
    return state_code == user.state_code or bool(_grants(user, state_code))


def _grants(user: User, key: str) -> frozenset[Permission]:
    # Staff hold grants under state codes, Commission users (who have no state) under COMMISSION_KEY.
    if (key == COMMISSION_KEY) != (user.state_code is None):
        return frozenset()
    return GRANTABLE[Role(user.role)] & frozenset(user.permissions.get(key, []))


def require(permission: Permission | None = None, *, state_param: str | None = None) -> Any:
    """``Depends`` admitting an active caller who holds ``permission``; yields the caller's ``User``.

    The state is the path parameter named ``state_param``, where the caller must have
    standing, or the caller's own ``state_code``. With no ``permission``, any active user
    with standing passes. Which rows the caller may see is the route's query's job
    (constitution Principle II).
    """
    access = RouteAccess(signed_in=True, permission=permission, state_param=state_param)

    async def check(request: Request, user: Annotated[User, Depends(current_user)]) -> User:
        if state_param is None:
            state = user.state_code
        else:
            state = request.path_params[state_param]
            if not has_standing(user, state):
                raise AppError(403, ErrorCode.Forbidden, [f'You have no access to {state}'])
        if permission is not None and permission not in held_permissions(user, state):
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


def route_access(route: RouteContext) -> RouteAccess | None:
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
