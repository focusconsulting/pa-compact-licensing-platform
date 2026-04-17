from typing import Annotated

from fastapi import APIRouter, Depends

from licensing_api.auth import CurrentUser, get_current_user

router = APIRouter()


@router.get(
    path='/me',
    name='Get current user',
    description='Returns information about the current user',
)
async def get_me(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    return user
