from __future__ import annotations

from datetime import date
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field

from licensing_api.repo.base import AuditColumns


class FeeType(StrEnum):
    # The SQL and Commission fees to apply for participation (Rule 3 §3.4(a)(7)).
    PARTICIPATION = 'participation'
    # The remote state and Commission fees per privilege (Rule 3 §3.4(c)(4)).
    PRIVILEGE = 'privilege'
    RENEWAL = 'renewal'


class Fee(AuditColumns, table=True):
    """One amount in the fee schedule. Owner: epic 7 (S-01 writes it); read by epics 8 and 9.

    ``state_code`` NULL is the Commission's own fee of that type. Amounts are never
    edited: a new amount is a new row with a later ``effective_from``, and the one
    in force on a day is the latest on or before it.
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'fees'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    public_id: UUID = Field(default_factory=uuid4, unique=True)
    state_code: str | None = Field(default=None, foreign_key='states.code', max_length=2)
    fee_type: str
    amount_cents: int
    effective_from: date
