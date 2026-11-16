"""Queries for public verification.

Each selects only the columns the public allow-list names
(``engineering/docs/public-verification.md``), never a whole practitioner or
privilege row, and collapses the computed status to the public one before it
leaves this module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
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
from licensing_api.repo.status import (
    PUBLIC_STATUS,
    PrivilegeComputedStatus,
    PrivilegeStatus,
    PublicPrivilegeStatus,
)

# What a list of holders may be sorted by, case-insensitively as the search matches.
HOLDER_SORT: Mapping[str, ColumnElement[Any]] = {
    'last_name': func.lower(col(Practitioner.legal_last_name)),
    'first_name': func.lower(col(Practitioner.legal_first_name)),
}
HOLDER_TIEBREAKER: Mapped[UUID] = col(Practitioner.public_id)


@dataclass(frozen=True)
class Holder:
    """A PA who holds at least one privilege, as the public may see them."""

    public_id: UUID
    first_name: str
    last_name: str
    name_suffix: str | None
    sql_state_code: str
    sql_state_name: str


@dataclass(frozen=True)
class HeldPrivilege:
    """One privilege of a holder, with its public status."""

    state_code: str
    state_name: str
    number: str
    issued_at: datetime
    expires_on: date
    status: PublicPrivilegeStatus


def _holder_ids() -> SelectOfScalar[UUID]:
    """The ``public_id`` of every practitioner the public may find: one with a privilege, a name, and a state of qualifying license."""
    return select(col(Practitioner.public_id)).where(
        exists().where(col(Privilege.practitioner_id) == col(Practitioner.id)),
        col(Practitioner.legal_first_name).is_not(None),
        col(Practitioner.legal_last_name).is_not(None),
        col(Practitioner.current_sql_state_code).is_not(None),
    )


def holders_by_name(first_name: str, last_name: str) -> SelectOfScalar[UUID]:
    """Holders whose first and last names both equal the ones given, ignoring case. A prefix does not match."""
    return _holder_ids().where(
        func.lower(col(Practitioner.legal_last_name)) == last_name.lower(),
        func.lower(col(Practitioner.legal_first_name)) == first_name.lower(),
    )


def holders_by_privilege_number(number: str) -> SelectOfScalar[UUID]:
    """The holder of the privilege with exactly this number."""
    return _holder_ids().where(
        exists().where(
            col(Privilege.practitioner_id) == col(Practitioner.id),
            col(Privilege.privilege_number) == number,
        )
    )


def holder_by_id(public_id: UUID) -> SelectOfScalar[UUID]:
    """The holder with this ``public_id``; nothing for a practitioner who holds no privilege."""
    return _holder_ids().where(col(Practitioner.public_id) == public_id)


async def holders(session: AsyncSession, public_ids: Sequence[UUID]) -> list[Holder]:
    """The holders with these ids, in the order given."""
    statement = (
        select_columns(
            col(Practitioner.public_id),
            col(Practitioner.legal_first_name),
            col(Practitioner.legal_last_name),
            col(Practitioner.name_suffix),
            col(State.code).label('state_code'),
            col(State.name).label('state_name'),
        )
        .join(State, col(State.code) == col(Practitioner.current_sql_state_code))
        .where(col(Practitioner.public_id).in_(public_ids))
    )
    found = {
        row.public_id: Holder(
            public_id=row.public_id,
            # Nullable columns, but _holder_ids admits only practitioners with both names.
            first_name=row.legal_first_name,
            last_name=row.legal_last_name,
            name_suffix=row.name_suffix,
            sql_state_code=row.state_code,
            sql_state_name=row.state_name,
        )
        for row in (await session.execute(statement)).all()
    }
    return [found[public_id] for public_id in public_ids]


async def privileges_of(
    session: AsyncSession, public_ids: Sequence[UUID]
) -> dict[UUID, list[HeldPrivilege]]:
    """Every privilege of each of these holders, by state name then number, in one query."""
    statement = (
        select_columns(
            col(Practitioner.public_id),
            col(State.code),
            col(State.name),
            col(Privilege.privilege_number),
            col(Privilege.issued_at),
            col(Privilege.expires_on),
            col(PrivilegeStatus.status),
        )
        .join(Privilege, col(Privilege.practitioner_id) == col(Practitioner.id))
        .join(State, col(State.code) == col(Privilege.remote_state_code))
        .join(PrivilegeStatus, col(PrivilegeStatus.privilege_id) == col(Privilege.id))
        .where(col(Practitioner.public_id).in_(public_ids))
        .order_by(col(State.name), col(Privilege.privilege_number))
    )
    held: dict[UUID, list[HeldPrivilege]] = {public_id: [] for public_id in public_ids}
    for public_id, code, name, number, issued_at, expires_on, status in (
        await session.execute(statement)
    ).tuples():
        held[public_id].append(
            HeldPrivilege(
                state_code=code,
                state_name=name,
                number=number,
                issued_at=issued_at,
                expires_on=expires_on,
                status=PUBLIC_STATUS[PrivilegeComputedStatus(status)],
            )
        )
    return held
