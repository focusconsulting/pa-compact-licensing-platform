"""Lookup tables for value lists the Commission has not settled, so an answer is a data change (ADR-0005)."""

from __future__ import annotations

from enum import StrEnum

from sqlmodel import Field

from licensing_api.repo.base import AuditColumns


class ReferenceValue(AuditColumns):
    """Columns shared by every lookup table. Inactive values stay so existing rows keep their meaning."""

    code: str = Field(primary_key=True)
    label: str
    sort_order: int
    is_active: bool = True


class RefSex(ReferenceValue, table=True):
    """Values for the uniform data set's sex field (Rule 4 §4.3(c)(3)); filled once Q-10 is answered."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'ref_sex'  # type: ignore[assignment]


class RefAdverseActionType(ReferenceValue, table=True):
    """Kinds of adverse action, seeded from the examples in ML §2.A; Q-17 may extend them."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'ref_adverse_action_types'  # type: ignore[assignment]


class RefNpdbCategory(ReferenceValue, table=True):
    """NPDB basis-for-action categories, optional on an adverse action; filled once Q-17 is answered."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'ref_npdb_categories'  # type: ignore[assignment]


class DenialScope(StrEnum):
    """Whether a denial reason applies to the SQL's eligibility decision or a remote state's privilege decision."""

    ELIGIBILITY = 'eligibility'
    PRIVILEGE = 'privilege'


class RefDenialReason(ReferenceValue, table=True):
    """Reasons a state may give for a denial. Never criminal history record information (ML §8.B.4); Q-08 confirms the list."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'ref_denial_reasons'  # type: ignore[assignment]

    applies_to: str
