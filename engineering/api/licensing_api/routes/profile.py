"""The PA's own profile: the parts of the uniform data set the application's first step collects (Rule 4 §4.3(c)).

Each change writes history and ``practitioner.profile_changed``, and records the PA as the
group's ``entered_by``; a state's verification stamp stays (platform contract, "Profile fields").
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, StringConstraints
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.context import ChangeContext, change_context
from licensing_api.dependencies import get_db_session
from licensing_api.errors import AppError, ErrorCode
from licensing_api.permissions import Permission, require
from licensing_api.repo import history
from licensing_api.repo.base import utc_now
from licensing_api.repo.domain_event import EventType, emit
from licensing_api.repo.practitioner import Practitioner, PractitionerOtherName
from licensing_api.repo.user import User
from licensing_api.responses import Data, example

me = APIRouter(prefix='/profile')

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]

# The profile fields each group holds; a change to one records the PA as the group's ``entered_by``.
_GROUPS = {
    'identity': ('date_of_birth',),
    'residence': (
        'residence_line1',
        'residence_line2',
        'residence_city',
        'residence_region',
        'residence_postal_code',
        'residence_country_code',
    ),
    'certification': ('nccpa_certification_number',),
}


class Residence(BaseModel):
    """The PA's primary residence, where legal papers can be served by mail (Rule 3 §3.4(a)(3))."""

    model_config = ConfigDict(extra='forbid')

    line1: Text
    line2: Text | None = None
    city: Text
    region: Text | None = None
    postal_code: Text | None = None
    country_code: Annotated[str, StringConstraints(pattern=r'^[A-Z]{2}$')]


class OtherName(BaseModel):
    """A name the PA uses or has used. ``last_name`` is required."""

    model_config = ConfigDict(extra='forbid')

    first_name: Text | None = None
    middle_name: Text | None = None
    last_name: Text
    name_suffix: Text | None = None


_RESIDENCE_EXAMPLE = {
    'line1': '100 Sample Street',
    'line2': None,
    'city': 'Sample City',
    'region': 'KS',
    'postal_code': '66601',
    'country_code': 'US',
}


class ProfileOut(BaseModel):
    """The profile fields the application's first step shows. ``residence`` is null until the PA enters one."""

    model_config = ConfigDict(
        json_schema_extra=example(
            legal_first_name='Jordan',
            legal_last_name='Sample',
            date_of_birth=date(1988, 3, 14),
            residence=_RESIDENCE_EXAMPLE,
            nccpa_certification_number='1234567',
            other_names=[],
        )
    )

    legal_first_name: str | None
    legal_last_name: str | None
    date_of_birth: date | None
    residence: Residence | None
    nccpa_certification_number: str | None
    other_names: list[OtherName]


class ProfileUpdate(BaseModel):
    """Fields to change. Omitted fields keep their value; ``other_names`` replaces the whole list."""

    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra=example(
            date_of_birth=date(1988, 3, 14),
            residence=_RESIDENCE_EXAMPLE,
            nccpa_certification_number='1234567',
            other_names=[{'last_name': 'Smith'}],
        ),
    )

    date_of_birth: date | None = None
    residence: Residence | None = None
    nccpa_certification_number: Text | None = None
    other_names: list[OtherName] | None = None


@me.get('', name='Get my profile', description='Your profile, as the application shows it.')
async def get_my_profile(
    caller: Annotated[User, require(Permission.MANAGE_OWN_RECORD)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[ProfileOut]:
    """Read-only legal names come from the PA's registration."""
    practitioner = await _practitioner(session, caller)
    return Data(data=await _out(session, practitioner))


@me.patch(
    '',
    name='Save my profile',
    description=(
        'Changes your date of birth, residence address, NCCPA certification number, or other names. A '
        "change keeps your state's verification and is shown to it in your history."
    ),
)
async def save_my_profile(
    body: ProfileUpdate,
    caller: Annotated[User, require(Permission.MANAGE_OWN_RECORD)],
    ctx: Annotated[ChangeContext, Depends(change_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[ProfileOut]:
    """One history row for the practitioner and one per added or removed name, and one event if anything changed."""
    practitioner = await _practitioner(session, caller, for_update=True)
    before = history.snapshot(practitioner)
    changes = body.model_dump(exclude_unset=True, exclude={'residence', 'other_names'})
    if body.residence is not None:
        changes |= {f'residence_{k}': v for k, v in body.residence.model_dump().items()}
    for name, value in changes.items():
        setattr(practitioner, name, value)
    after = history.snapshot(practitioner)
    for group, fields in _GROUPS.items():
        if any(before[f] != after[f] for f in fields):
            setattr(practitioner, f'{group}_entered_by', ctx.user_id)
    names_changed = body.other_names is not None and await _replace_other_names(
        session, ctx, practitioner, body.other_names
    )
    if names_changed:
        practitioner.identity_entered_by = ctx.user_id
    practitioner.updated_by = ctx.user_id
    recorded = await history.write(session, ctx, practitioner, before=before)
    if recorded is not None or names_changed:
        await emit(session, ctx, EventType.PRACTITIONER_PROFILE_CHANGED, practitioner)
    await session.commit()
    return Data(data=await _out(session, practitioner))


async def _practitioner(
    session: AsyncSession, caller: User, *, for_update: bool = False
) -> Practitioner:
    statement = select(Practitioner).where(col(Practitioner.user_id) == caller.id)
    if for_update:
        statement = statement.with_for_update()
    practitioner = (await session.scalars(statement)).one_or_none()
    if practitioner is None:
        raise AppError(404, ErrorCode.NotFound, ['You have no practitioner record'])
    return practitioner


async def _current_names(
    session: AsyncSession, practitioner_id: int | None
) -> list[PractitionerOtherName]:
    statement = (
        select(PractitionerOtherName)
        .where(
            col(PractitionerOtherName.practitioner_id) == practitioner_id,
            col(PractitionerOtherName.removed_at).is_(None),
        )
        .order_by(col(PractitionerOtherName.id))
    )
    return list((await session.scalars(statement)).all())


def _key(name: PractitionerOtherName | OtherName) -> tuple[str | None, ...]:
    return (name.first_name, name.middle_name, name.last_name, name.name_suffix)


async def _replace_other_names(
    session: AsyncSession, ctx: ChangeContext, practitioner: Practitioner, wanted: list[OtherName]
) -> bool:
    """Remove names no longer listed and add new ones; a name listed again is left alone."""
    current = await _current_names(session, practitioner.id)
    wanted_keys = {_key(n) for n in wanted}
    kept_keys = {_key(n) for n in current}
    changed = False
    for name in current:
        if _key(name) not in wanted_keys:
            snapshot = history.snapshot(name)
            name.removed_at = utc_now()
            name.updated_by = ctx.user_id
            await history.write(session, ctx, name, before=snapshot)
            changed = True
    for name in wanted:
        if _key(name) not in kept_keys:
            kept_keys.add(_key(name))
            row = PractitionerOtherName(
                practitioner_id=practitioner.id,  # type: ignore[arg-type]  # a loaded practitioner has an id
                created_by=ctx.user_id,
                **name.model_dump(),
            )
            session.add(row)
            await history.write(session, ctx, row, before=None)
            changed = True
    return changed


async def _out(session: AsyncSession, practitioner: Practitioner) -> ProfileOut:
    residence = None
    if practitioner.residence_line1 is not None:
        # Not validated: staff or an import may have entered a partial address.
        residence = Residence.model_construct(
            line1=practitioner.residence_line1,
            line2=practitioner.residence_line2,
            city=practitioner.residence_city,
            region=practitioner.residence_region,
            postal_code=practitioner.residence_postal_code,
            country_code=practitioner.residence_country_code,
        )
    names = await _current_names(session, practitioner.id)
    return ProfileOut(
        legal_first_name=practitioner.legal_first_name,
        legal_last_name=practitioner.legal_last_name,
        date_of_birth=practitioner.date_of_birth,
        residence=residence,
        nccpa_certification_number=practitioner.nccpa_certification_number,
        other_names=[OtherName.model_validate(n, from_attributes=True) for n in names],
    )
