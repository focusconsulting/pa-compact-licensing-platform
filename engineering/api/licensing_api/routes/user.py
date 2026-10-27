from typing import Annotated
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from licensing_api.permissions import require
from licensing_api.repo.user import User
from licensing_api.responses import example

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
        ),
    )

    user_id: UUID = Field(validation_alias='public_id')  # only ID we should expose externally
    email: str
    given_name: str | None
    family_name: str | None
    role: str
    state_code: str | None
    is_active: bool


@router.get(
    path='',
    name='Get current user',
    description='Returns information about the current user',
)
async def get_me(caller: Annotated[User, require()]) -> CurrentUser:
    """Return the signed-in caller's profile."""
    return CurrentUser.model_validate(caller)
