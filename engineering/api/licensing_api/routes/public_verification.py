"""Public verification: anyone may confirm that a PA holds a compact privilege (SOW §2.1).

The response models are the allow-list (Rule 4 §4.5(b)-(d), Q-12): they forbid
extra fields and are built field by field, so nothing else on a practitioner or a
privilege can reach a response. A field is added to one only by changing FLOW-08
(``product/context/flows/08-public-verification.md``), which says why each is
public; ``tests/test_public_verification.py`` pins the list.
"""

import logging
from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel.sql.expression import SelectOfScalar

from licensing_api.days import compact_date_at, reference_time_zone
from licensing_api.dependencies import get_db_session
from licensing_api.errors import AppError, ErrorCode, ErrorResponse
from licensing_api.permissions import public
from licensing_api.repo.pagination import paginate
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.public_verification import (
    HOLDER_SORT,
    HOLDER_TIEBREAKER,
    get_holder,
    holders_by_name,
    holders_by_privilege_number,
    privilege_states,
    privileges_of,
    state_names,
)
from licensing_api.repo.status import PUBLIC_STATUS, PublicPrivilegeStatus
from licensing_api.responses import Data, Paged, PageQuery, example, page_query

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix='/privilege-holders',
    dependencies=[public()],
    responses={
        429: {
            'model': ErrorResponse,
            'description': 'Too many requests from one address. The web firewall sends this, not the API.',
        }
    },
)

_SEARCH_PARAMETERS = frozenset(
    {'first_name', 'last_name', 'privilege_number', 'page', 'page_size', 'sort'}
)
_NAME_LENGTH = 100
# next_privilege_number's format: PA, the state, and at least six digits.
_PRIVILEGE_NUMBER = r'^[Pp][Aa]-[A-Za-z]{2}-\d{6,}$'


class StateRef(BaseModel):
    """A state by code and name, for a response that names a state without describing it."""

    model_config = ConfigDict(extra='forbid', json_schema_extra=example(code='OK', name='Oklahoma'))

    code: str
    name: str


_KANSAS = StateRef(code='KS', name='Kansas')
_OKLAHOMA = StateRef(code='OK', name='Oklahoma')
_PRIVILEGE_EXAMPLE: dict[str, Any] = {
    'state': _OKLAHOMA,
    'number': 'PA-OK-000123',
    'status': PublicPrivilegeStatus.ACTIVE,
    'issued_on': date(2026, 11, 2),
    'expires_on': date(2027, 12, 31),
}


class PublicPrivilege(BaseModel):
    """A privilege as the public sees it: no reason for its status, and nothing about discipline."""

    model_config = ConfigDict(extra='forbid', json_schema_extra=example(**_PRIVILEGE_EXAMPLE))

    state: StateRef
    number: str
    status: PublicPrivilegeStatus
    issued_on: date
    expires_on: date


_PRIVILEGE = PublicPrivilege(**_PRIVILEGE_EXAMPLE)
_HOLDER_EXAMPLE: dict[str, Any] = {
    'id': UUID('5f0c2d6e-8a41-4b7c-9d13-6e2f4a8b1c90'),
    'first_name': 'Pat',
    'last_name': 'Morgan',
    'name_suffix': None,
    'state_of_qualifying_license': _KANSAS,
}


class PrivilegeHolderSummary(BaseModel):
    """A PA who holds a privilege, and the states they hold one in."""

    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra=example(**_HOLDER_EXAMPLE, privilege_states=[_OKLAHOMA]),
    )

    id: UUID
    first_name: str
    last_name: str
    name_suffix: str | None
    state_of_qualifying_license: StateRef
    privilege_states: list[StateRef]


class PrivilegeHolder(BaseModel):
    """A PA who holds a privilege, and each privilege with its status and dates."""

    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra=example(**_HOLDER_EXAMPLE, privileges=[_PRIVILEGE]),
    )

    id: UUID
    first_name: str
    last_name: str
    name_suffix: str | None
    state_of_qualifying_license: StateRef
    privileges: list[PublicPrivilege]


async def _known_parameters(request: Request) -> None:
    """Refuses a query parameter the search does not take, so a typo is not a silently ignored filter."""
    if unknown := sorted(set(request.query_params) - _SEARCH_PARAMETERS):
        raise AppError(
            422,
            ErrorCode.ValidationError,
            [f'query.{name}: unknown parameter' for name in unknown],
        )


def _search(
    first_name: str | None, last_name: str | None, privilege_number: str | None
) -> tuple[str, SelectOfScalar[Practitioner]]:
    """The search's mode and statement. Both names together or a number alone; anything else could enumerate."""
    first, last = (first_name or '').strip(), (last_name or '').strip()
    if privilege_number and first_name is None and last_name is None:
        return 'privilege_number', holders_by_privilege_number(privilege_number.upper())
    if first and last and privilege_number is None:
        return 'name', holders_by_name(first, last)
    raise AppError(
        422,
        ErrorCode.ValidationError,
        ['query: search by first_name and last_name together, or by privilege_number alone'],
    )


def _state(names: dict[str, str], code: str | None) -> dict[str, Any]:
    """A state as a ``StateRef``'s fields."""
    return {'code': code, 'name': names.get(code) if code else None}


def _holder_fields(holder: Practitioner, names: dict[str, str]) -> dict[str, Any]:
    """The fields both holder models share. The models validate them: a holder always has each (``repo.holders``)."""
    return {
        'id': holder.public_id,
        'first_name': holder.legal_first_name,
        'last_name': holder.legal_last_name,
        'name_suffix': holder.name_suffix,
        'state_of_qualifying_license': _state(names, holder.current_sql_state_code),
    }


@router.get(
    '',
    name='Search privilege holders',
    description=(
        'PAs who hold a compact privilege, active or not. Search by `first_name` and `last_name` '
        'together, or by `privilege_number` alone. Names must match in full, ignoring case. '
        'No match is an empty list.'
    ),
    dependencies=[Depends(_known_parameters)],
)
async def search_privilege_holders(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[
        PageQuery, page_query('last_name', 'first_name', default_sort='last_name,first_name')
    ],
    # Each is optional only because the other search exists; _search requires one whole search.
    first_name: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=_NAME_LENGTH,
            description='Required with `last_name`, unless searching by `privilege_number`',
        ),
    ] = None,
    last_name: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=_NAME_LENGTH,
            description='Required with `first_name`, unless searching by `privilege_number`',
        ),
    ] = None,
    privilege_number: Annotated[
        str | None,
        Query(
            pattern=_PRIVILEGE_NUMBER,
            description='For example `PA-OK-000123`. Not with a name',
        ),
    ] = None,
) -> Paged[PrivilegeHolderSummary]:
    """Page through the holders a search matches; the log line never carries the search terms."""
    mode, statement = _search(first_name, last_name, privilege_number)
    found, total = await paginate(
        session, statement, query, HOLDER_SORT, tiebreaker=HOLDER_TIEBREAKER
    )
    logger.info('public verification search', extra={'mode': mode, 'results': total})
    names = await state_names(session)
    held = await privilege_states(session, found)
    return Paged(
        data=[
            PrivilegeHolderSummary.model_validate(
                {
                    **_holder_fields(holder, names),
                    'privilege_states': sorted(
                        (_state(names, code) for code in held[holder.id or 0]),
                        key=lambda state: state['name'],
                    ),
                }
            )
            for holder in found
        ],
        page=query.page_of(total),
    )


@router.get(
    '/{holder_id}',
    name='Get a privilege holder',
    description=(
        "A PA's compact privileges: the state, number, status, and dates of each. A privilege that "
        'is not active shows as `expired` or `inactive`, with no reason.'
    ),
)
async def get_privilege_holder(
    holder_id: Annotated[UUID, Path(description='The `id` from a search result')],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[PrivilegeHolder]:
    """One holder; a PA with no privilege is as absent as an unknown id."""
    holder = await get_holder(session, holder_id)
    if holder is None:
        raise AppError(404, ErrorCode.NotFound, ['No such privilege holder'])
    names = await state_names(session)
    time_zone = await reference_time_zone(session)
    privileges = [
        {
            'state': _state(names, privilege.remote_state_code),
            'number': privilege.privilege_number,
            'status': PUBLIC_STATUS[status],
            'issued_on': compact_date_at(privilege.issued_at, time_zone),
            'expires_on': privilege.expires_on,
        }
        for privilege, status in await privileges_of(session, holder)
    ]
    return Data(
        data=PrivilegeHolder.model_validate(
            {
                **_holder_fields(holder, names),
                'privileges': sorted(privileges, key=lambda p: (p['state']['name'], p['number'])),
            }
        )
    )
