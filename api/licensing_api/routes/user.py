from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from licensing_api.auth import AuthClaims, get_auth_claims
from licensing_api.dependencies import get_db_session
from licensing_api.errors import AppError, ErrorCode
from licensing_api.repo.user import get_user_by_email, get_user_by_public_id

router = APIRouter()


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: UUID = Field(validation_alias='public_id')  # only ID we should expose externally
    email: str
    given_name: str | None
    family_name: str | None
    role: str
    state_code: str | None
    is_active: bool


@router.get(
    path='/me',
    name='Get current user',
    description='Returns information about the current user',
)
async def get_me(
    claims: Annotated[AuthClaims, Depends(get_auth_claims)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CurrentUser:
    user = await get_user_by_public_id(session, claims.sub)
    if user is None:
        user = await get_user_by_email(session, claims.email)
        if user is None:
            raise AppError(403, ErrorCode.UserNotFound, ['User not found'])
        if user.public_id is None:
            user.public_id = claims.sub
            await session.commit()

    if not user.is_active:
        raise AppError(403, ErrorCode.UserInactive, ['User is inactive'])

    return CurrentUser.model_validate(user)
