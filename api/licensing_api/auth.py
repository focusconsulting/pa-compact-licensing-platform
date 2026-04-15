from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import asyncpg
import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from licensing_api.config import Settings, get_settings
from licensing_api.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)

_bearer = HTTPBearer()


class CurrentUser(BaseModel):
    id: int
    email: str
    public_id: UUID | None
    given_name: str | None
    family_name: str | None
    role: str
    state_code: str | None
    is_active: bool


def _get_db_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.db_pool


@lru_cache
def _get_jwks(jwks_url: str) -> dict:
    """Fetch and cache Cognito JWKS. Cached per worker process."""
    with httpx.Client(timeout=10) as client:
        response = client.get(jwks_url)
        response.raise_for_status()
    return response.json()


def _verify_token(token: str, settings: Settings) -> dict:
    """Validate a Cognito ID token and return its claims."""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise AppError(401, ErrorCode.InvalidToken, ['Invalid token format']) from e

    jwks = _get_jwks(settings.cognito_jwks_url)
    kid = unverified_header.get('kid')
    key = next((k for k in jwks['keys'] if k['kid'] == kid), None)
    if key is None:
        raise AppError(401, ErrorCode.InvalidToken, ['Unknown signing key'])

    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            audience=settings.cognito_client_id,
        )
    except JWTError as e:
        raise AppError(401, ErrorCode.InvalidToken, ['Token validation failed']) from e

    if claims.get('token_use') != 'id':
        raise AppError(401, ErrorCode.InvalidToken, ['Expected Cognito ID token'])

    return claims


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[asyncpg.Pool, Depends(_get_db_pool)],
) -> CurrentUser:
    """Verify the Bearer token and return the authenticated user from the database."""
    claims = _verify_token(credentials.credentials, settings)
    email: str = claims['email']

    row = await db.fetchrow(
        """
        SELECT id, email, public_id, given_name, family_name,
               role, state_code, is_active
        FROM users
        WHERE email = $1
        """,
        email,
    )
    if row is None:
        raise AppError(403, ErrorCode.UserNotFound, ['User not found'])
    if not row['is_active']:
        raise AppError(403, ErrorCode.UserInactive, ['User is inactive'])

    return CurrentUser(
        id=row['id'],
        email=row['email'],
        public_id=row['public_id'],
        given_name=row['given_name'],
        family_name=row['family_name'],
        role=row['role'],
        state_code=row['state_code'],
        is_active=row['is_active'],
    )
