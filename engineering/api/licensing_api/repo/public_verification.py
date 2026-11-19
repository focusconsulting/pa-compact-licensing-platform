"""Queries for public verification (FLOW-08): who the public may find, and their privileges.

They return whole rows, as every repo module does. What leaves the API is decided
by the response models in ``routes/public_verification.py``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, exists, func
from sqlalchemy import select as select_columns
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped
from sqlmodel import col, select
from sqlmodel.sql.expression import SelectOfScalar

from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.privilege import Privilege
from licensing_api.repo.state import State
from licensing_api.repo.status import PrivilegeComputedStatus, PrivilegeStatus

# What a list of holders may be sorted by, case-insensitively as the search matches.
HOLDER_SORT: Mapping[str, ColumnElement[Any]] = {
    'last_name': func.lower(col(Practitioner.legal_last_name)),
    'first_name': func.lower(col(Practitioner.legal_first_name)),
}
HOLDER_TIEBREAKER: Mapped[UUID] = col(Practitioner.public_id)


def holders() -> SelectOfScalar[Practitioner]:
    """Every PA the public may find: one who holds a privilege, active or not, with a name and a state of qualifying license on record."""
    return select(Practitioner).where(
        exists().where(col(Privilege.practitioner_id) == col(Practitioner.id)),
        col(Practitioner.legal_first_name).is_not(None),
        col(Practitioner.legal_last_name).is_not(None),
        col(Practitioner.current_sql_state_code).is_not(None),
    )


def holders_by_name(first_name: str, last_name: str) -> SelectOfScalar[Practitioner]:
    """Holders whose first and last names both equal the ones given, ignoring case. A prefix does not match."""
    return holders().where(
        func.lower(col(Practitioner.legal_last_name)) == last_name.lower(),
        func.lower(col(Practitioner.legal_first_name)) == first_name.lower(),
    )


def holders_by_privilege_number(number: str) -> SelectOfScalar[Practitioner]:
    """The holder of the privilege with exactly this number."""
    return holders().where(
        exists().where(
            col(Privilege.practitioner_id) == col(Practitioner.id),
            col(Privilege.privilege_number) == number,
        )
    )


async def get_holder(session: AsyncSession, public_id: UUID) -> Practitioner | None:
    """The holder with this ``public_id``; None for a practitioner who holds no privilege."""
    return await session.scalar(holders().where(col(Practitioner.public_id) == public_id))


async def privilege_states(
    session: AsyncSession, practitioners: Sequence[Practitioner]
) -> dict[int, set[str]]:
    """The states each of these PAs holds a privilege in, by practitioner id."""
    statement = select_columns(
        col(Privilege.practitioner_id), col(Privilege.remote_state_code)
    ).where(col(Privilege.practitioner_id).in_([p.id for p in practitioners]))
    held: dict[int, set[str]] = {}
    for practitioner_id, state_code in (await session.execute(statement)).tuples():
        held.setdefault(practitioner_id, set()).add(state_code)
    return held


async def privileges_of(
    session: AsyncSession, practitioner: Practitioner
) -> list[tuple[Privilege, PrivilegeComputedStatus]]:
    """Every privilege this PA holds, each with its status today."""
    statement = (
        select_columns(Privilege, col(PrivilegeStatus.status))
        .join(PrivilegeStatus, col(PrivilegeStatus.privilege_id) == col(Privilege.id))
        .where(col(Privilege.practitioner_id) == practitioner.id)
    )
    return [
        (privilege, PrivilegeComputedStatus(status))
        for privilege, status in (await session.execute(statement)).tuples()
    ]


async def state_names(session: AsyncSession) -> dict[str, str]:
    """Each state's name by its code."""
    rows = await session.execute(select_columns(col(State.code), col(State.name)))
    return dict(rows.tuples().all())
