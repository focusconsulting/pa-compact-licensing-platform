"""Who may call a route: the declaration every ``/api`` route makes (ADR-0009, backlog D5)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession

from licensing_api.auth import AuthClaims, get_auth_claims
from licensing_api.dependencies import get_db_session
from licensing_api.errors import AppError, ErrorCode
from licensing_api.repo.user import User, get_user_by_email, get_user_by_public_id


class Role(StrEnum):
    """``chk_users_role``."""

    LICENSEE = 'licensee'
    STATE_STAFF = 'state_staff'
    STATE_ADMIN = 'state_admin'
    COMPACT_ADMIN = 'compact_admin'
    ADMIN = 'admin'


class Permission(StrEnum):
    """Held per state in ``users.permissions`` (D5). ``read_general`` is implicit for staff and not listed."""

    READ_PRIVATE = 'read_private'
    READ_SSN = 'read_ssn'
    WRITE = 'write'
    ADMIN = 'admin'


STAFF_ROLES = frozenset({Role.STATE_STAFF, Role.STATE_ADMIN})


@dataclass(frozen=True)
class RouteAccess:
    """A route's declaration. ``roles`` is None for a public route."""

    roles: frozenset[Role] | None
    permission: Permission | None = None
    state_param: str | None = None


# The attribute that marks a dependency as a route's access declaration, for route_access().
_ACCESS = '__route_access__'


def require(
    *roles: Role, permission: Permission | None = None, state_param: str | None = None
) -> Any:
    """``Depends`` admitting an active caller whose role is in ``roles``; yields the caller's ``User``.

    When ``permission`` is set, state staff must also hold it in the route's state: the
    path parameter named ``state_param``, or their own ``state_code``. Other listed roles
    pass without it, so ``compact_admin`` and ``admin`` reach a state route only when the
    route lists them (constitution Principle VII). Which rows the caller may see is the
    route's query's job (Principle II).
    """
    if not roles:
        raise ValueError('require() needs at least one role; use public() for an open route')
    if permission is not None and not STAFF_ROLES & set(roles):
        raise ValueError('A permission applies only to state staff; list a staff role')
    allowed = frozenset(roles)
    access = RouteAccess(roles=allowed, permission=permission, state_param=state_param)

    async def check(
        request: Request,
        claims: Annotated[AuthClaims, Depends(get_auth_claims)],
        session: Annotated[AsyncSession, Depends(get_db_session)],
    ) -> User:
        user = await _signed_in_user(session, claims)
        if user.role not in allowed:
            raise AppError(403, ErrorCode.Forbidden, ['Your role cannot use this route'])
        if permission is not None and user.role in STAFF_ROLES:
            state = request.path_params.get(state_param) if state_param else user.state_code
            held = user.permissions.get(state.upper(), []) if state else []
            if permission not in held:
                raise AppError(403, ErrorCode.Forbidden, [f'You need {permission} in this state'])
        return user

    setattr(check, _ACCESS, access)
    return Depends(check)


async def _open() -> None:
    return None


setattr(_open, _ACCESS, RouteAccess(roles=None))


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


async def _signed_in_user(session: AsyncSession, claims: AuthClaims) -> User:
    """The user the token belongs to, linking the token's ``sub`` on first sign-in (ADR-0009).

    A user is linked by email only while they have no ``sub``: a user already linked to
    another ``sub`` (the same email in another Cognito pool) is not this caller.
    """
    user = await get_user_by_public_id(session, claims.sub)
    if user is None:
        user = await get_user_by_email(session, claims.email)
        if user is None or user.public_id is not None:
            raise AppError(403, ErrorCode.UserNotFound, ['User not found'])
        if user.is_active:
            user.public_id = claims.sub
            await session.commit()
    if not user.is_active:
        raise AppError(403, ErrorCode.UserInactive, ['User is inactive'])
    return user
