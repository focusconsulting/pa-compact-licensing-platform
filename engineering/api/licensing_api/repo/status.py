"""Read-only models over the computed status views (F-02 phase 3, D1).

Each view evaluates its SQL function as of ``compact_today()`` in the reference
time zone (ADR-0006). To ask "as of" another date, query the function directly,
for example ``SELECT * FROM privilege_status_on(:as_of)``. Never write to these.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from sqlmodel import Field, SQLModel


class LicenseComputedStatus(StrEnum):
    ACTIVE = 'active'
    EXPIRED = 'expired'
    LAPSED = 'lapsed'
    INACTIVE = 'inactive'
    TERMINATED = 'terminated'
    ENCUMBERED = 'encumbered'


class PrivilegeComputedStatus(StrEnum):
    """What a privilege's holder and the public see (FLOW-06), in order of precedence."""

    INACTIVE = 'inactive'
    EXPIRED = 'expired'
    ENCUMBERED = 'encumbered'
    ACTIVE = 'active'


class QualifyingLicenseStatus(SQLModel, table=True):
    """A qualifying license's status today: terminated, the state's non-active status, expired, encumbered, or active."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'v_qualifying_license_status'  # type: ignore[assignment]

    qualifying_license_id: int = Field(primary_key=True, foreign_key='qualifying_licenses.id')
    status: str


class PrivilegeStatus(SQLModel, table=True):
    """A privilege's status today. ``status_reason`` is the deactivation reason when ``inactive``."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'v_privilege_status'  # type: ignore[assignment]

    privilege_id: int = Field(primary_key=True, foreign_key='privileges.id')
    status: str
    status_reason: str | None = None


class CompactEligibility(SQLModel, table=True):
    """Whether a practitioner is within the two-year bar today (ML §4.A.8).

    ``eligible_again_on`` is NULL while an adverse action against a qualifying
    license is still in force with no end date, or when the PA has never been barred.
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'v_compact_eligibility'  # type: ignore[assignment]

    practitioner_id: int = Field(primary_key=True, foreign_key='practitioners.id')
    is_barred: bool
    eligible_again_on: date | None = None
