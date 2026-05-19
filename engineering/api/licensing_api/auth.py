from __future__ import annotations

import logging
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict

from licensing_api.config import Settings, get_settings
from licensing_api.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)

_bearer = HTTPBearer()


class AuthClaims(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sub: UUID
    email: str


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


async def get_auth_claims(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthClaims:
    """Unpacks relevant data from auth claims"""
    claims = _verify_token(credentials.credentials, settings)
    return AuthClaims.model_validate(claims)
