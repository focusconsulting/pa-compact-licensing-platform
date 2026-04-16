from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated, Any
from uuid import UUID

import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from licensing_api.config import Settings, get_settings
from licensing_api.dependencies import get_db_session
from licensing_api.errors import AppError, ErrorCode
from licensing_api.repo.user import get_user_by_email, get_user_by_public_id

logger = logging.getLogger(__name__)

_bearer = HTTPBearer()


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID = Field(validation_alias='public_id')
    email: str
    given_name: str | None
    family_name: str | None
    role: str
    state_code: str | None
    is_active: bool


def _get_db_pool(request: Request) -> Any:
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
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CurrentUser:
    """Verify the Bearer token and return the authenticated user from the database."""
    claims = _verify_token(credentials.credentials, settings)
    sub = UUID(claims['sub'])
    email: str = claims['email']

    user = await get_user_by_public_id(session, sub)
    if user is None:
        user = await get_user_by_email(session, email)
        if user is None:
            raise AppError(403, ErrorCode.UserNotFound, ['User not found'])
        if user.public_id is None:
            user.public_id = sub
            await session.commit()

    if not user.is_active:
        raise AppError(403, ErrorCode.UserInactive, ['User is inactive'])

    return CurrentUser.model_validate(user)
