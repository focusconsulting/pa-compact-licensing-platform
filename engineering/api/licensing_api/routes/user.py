from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from licensing_api.permissions import Permission, held_permissions, require
from licensing_api.repo.user import User
from licensing_api.responses import Data, example

router = APIRouter()


class CurrentUser(BaseModel):
    """The signed-in user's profile. ``user_id`` is their public ID, never the internal ``users.id``."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra=example(
            user_id=UUID('6f1c2b0e-8d4a-4c3e-9b7a-2f5d1e0c9a84'),
            email='pat.morgan@example.com',
            given_name='Pat',
            family_name='Morgan',
            role='state_staff',
            state_code='KS',
            is_active=True,
            permissions=[Permission.READ_GENERAL, Permission.WRITE],
        ),
    )

    user_id: UUID = Field(validation_alias='public_id')  # only ID we should expose externally
    email: str
    given_name: str | None
    family_name: str | None
    role: str
    state_code: str | None
    is_active: bool
    # Held in their own state, for showing navigation. Routes still check every request.
    permissions: list[Permission]


@router.get(
    path='',
    name='Get current user',
    description='Returns information about the current user',
)
async def get_me(caller: Annotated[User, require()]) -> Data[CurrentUser]:
    """Return the signed-in caller's profile."""
    held = held_permissions(caller, caller.state_code)
    # ``User.permissions`` is the grants map, so the profile is built from a dict, not the row.
    profile = caller.model_dump() | {'permissions': [p for p in Permission if p in held]}
    return Data(data=CurrentUser.model_validate(profile))
