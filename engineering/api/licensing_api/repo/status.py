"""Computed status (F-02 phase 3, D1): the queries, the SQL functions built from them, and read-only view models.

Each status is a query written against the models, so a renamed or removed column
fails the type checker and the tests rather than a function in the database. The
``post-apply`` migration hook runs ``status_ddl()`` on every startup (ADR-0005), so
the functions in the database are always these queries.

Each function takes the date to evaluate (``as_of``); each view evaluates it as of
``compact_today()`` in the reference time zone (ADR-0006). To ask "as of" another
date, query the function, e.g. ``SELECT * FROM privilege_status_on(:as_of)``.
End dates are inclusive.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    ColumnElement,
    Date,
    Exists,
    Interval,
    Select,
    and_,
    case,
    cast,
    exists,
    false,
    func,
    literal_column,
    null,
    or_,
)
from sqlalchemy.dialects import postgresql
from sqlmodel import Field, SQLModel, col, select

from licensing_api.repo.adverse_action import AdverseAction, AdverseActionTarget
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.privilege import AdministratorStatus, Privilege
from licensing_api.repo.qualifying_license import LicenseStatus, QualifyingLicense

# The SQL functions' parameter: the day being evaluated.
AS_OF: ColumnElement[date] = literal_column('as_of', Date)


class LicenseComputedStatus(StrEnum):
    """The statuses ``QualifyingLicenseStatus`` reports: the state's reported statuses, plus ``encumbered``."""

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


def _in_force(target: Any, target_id: Any) -> Exists:
    """An adverse action against ``target_id`` in force on ``as_of``: started, and not yet ended."""
    return exists().where(
        col(target) == target_id,
        col(AdverseAction.effective_from) <= AS_OF,
        or_(
            col(AdverseAction.effective_until).is_(None),
            col(AdverseAction.effective_until) >= AS_OF,
        ),
    )


def qualifying_license_status_query() -> Select[Any]:
    """``(qualifying_license_id, status)``, taking the first that applies.

    The reported status is the current one; ``as_of`` applies to the dates.
    """
    license = QualifyingLicense
    status = case(
        # The PA's voluntary termination ends the license (Rule 3 §3.6(a)).
        (
            and_(col(license.terminated_on).is_not(None), col(license.terminated_on) <= AS_OF),
            LicenseComputedStatus.TERMINATED.value,
        ),
        # The state verifies and submits the license's status (Rule 4 §4.3(c)(11)).
        (
            col(license.state_reported_status) != LicenseStatus.ACTIVE.value,
            col(license.state_reported_status),
        ),
        # ... and its expiration date (Rule 4 §4.3(c)(11)).
        (
            and_(col(license.expires_on).is_not(None), AS_OF > col(license.expires_on)),
            LicenseComputedStatus.EXPIRED.value,
        ),
        # A qualifying license is unrestricted (ML §2.R); an adverse action restricts it (ML §2.A).
        (
            _in_force(AdverseAction.qualifying_license_id, col(license.id)),
            LicenseComputedStatus.ENCUMBERED.value,
        ),
        else_=LicenseComputedStatus.ACTIVE.value,
    )
    return select(col(license.id), status)


def privilege_status_query() -> Select[Any]:
    """``(privilege_id, status, status_reason)``, taking the first that applies (ADR-0005, FLOW-06).

    An adverse action against the qualifying license reaches privileges through the
    cascade that deactivates them (FLOW-05), not through this query.
    """
    privilege = Privilege
    is_inactive = col(privilege.administrator_status) == AdministratorStatus.INACTIVE.value
    status = case(
        (is_inactive, PrivilegeComputedStatus.INACTIVE.value),
        # Pinned to the license expiry in effect when the PA applied; renewal does not move it (Rule 3 §3.5(a)).
        (AS_OF > col(privilege.expires_on), PrivilegeComputedStatus.EXPIRED.value),
        # Valid unless terminated pursuant to an adverse action (ML §4.B).
        (
            _in_force(AdverseAction.privilege_id, col(privilege.id)),
            PrivilegeComputedStatus.ENCUMBERED.value,
        ),
        else_=PrivilegeComputedStatus.ACTIVE.value,
    )
    reason = case((is_inactive, col(privilege.deactivation_reason)), else_=null())
    return select(col(privilege.id), status, reason)


def compact_eligibility_query() -> Select[Any]:
    """``(practitioner_id, is_barred, eligible_again_on)``: the two-year bar (ML §4.A.8).

    A PA is barred while an adverse action against a qualifying license is in force,
    and for two years from "the date on which the License ... is no longer limited or
    restricted". ``effective_until`` is the last restricted day, so that date is the
    day after it. ``eligible_again_on`` is NULL while any such action has no end date.
    Actions that start after ``as_of``, and actions against a privilege, do not bar.
    """
    action = AdverseAction
    started = (
        select(
            col(action.practitioner_id).label('practitioner_id'),
            cast(
                col(action.effective_until) + 1 + literal_column("INTERVAL '2 years'", Interval),
                Date,
            ).label('bar_ends_on'),
            col(action.effective_until).is_(None).label('is_open_ended'),
        )
        .where(
            col(action.against) == AdverseActionTarget.QUALIFYING_LICENSE.value,
            col(action.effective_from) <= AS_OF,
        )
        .cte('started')
    )
    per_practitioner = (
        select(
            started.c.practitioner_id,
            func.bool_or(started.c.is_open_ended).label('has_open_ended'),
            func.max(started.c.bar_ends_on).label('latest_bar_end'),
        )
        .group_by(started.c.practitioner_id)
        .cte('per_practitioner')
    )
    practitioner_id = col(Practitioner.id)
    return select(
        practitioner_id,
        func.coalesce(
            or_(per_practitioner.c.has_open_ended, AS_OF < per_practitioner.c.latest_bar_end),
            false(),
        ),
        case((per_practitioner.c.has_open_ended, null()), else_=per_practitioner.c.latest_bar_end),
    ).outerjoin(per_practitioner, per_practitioner.c.practitioner_id == practitioner_id)


@dataclass(frozen=True)
class StatusFunction:
    """A computed-status SQL function and the view that evaluates it as of today."""

    name: str
    returns: str
    query: Callable[[], Select[Any]]
    view: str
    view_columns: str


STATUS_FUNCTIONS = (
    StatusFunction(
        name='qualifying_license_status_on',
        returns='qualifying_license_id BIGINT, status TEXT',
        query=qualifying_license_status_query,
        view='v_qualifying_license_status',
        view_columns='qualifying_license_id, status',
    ),
    StatusFunction(
        name='privilege_status_on',
        returns='privilege_id BIGINT, status TEXT, status_reason TEXT',
        query=privilege_status_query,
        view='v_privilege_status',
        view_columns='privilege_id, status, status_reason',
    ),
    StatusFunction(
        name='compact_eligibility_on',
        returns='practitioner_id BIGINT, is_barred BOOLEAN, eligible_again_on DATE',
        query=compact_eligibility_query,
        view='v_compact_eligibility',
        view_columns='practitioner_id, is_barred, eligible_again_on',
    ),
)


def function_body(function: StatusFunction) -> str:
    """The function's query as the SQL Postgres stores as its body."""
    compiled = function.query().compile(
        dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
    )
    return f'\n{compiled}\n'


def status_ddl() -> list[str]:
    """``CREATE OR REPLACE`` statements for every status function, then every view.

    ``CREATE OR REPLACE`` keeps anything that depends on them. It cannot change a
    function's output columns: that change needs a migration that drops the view and
    the function first.
    """
    functions = [
        f'CREATE OR REPLACE FUNCTION {f.name}(as_of DATE) RETURNS TABLE ({f.returns}) '
        f'LANGUAGE sql STABLE AS $body${function_body(f)}$body$'
        for f in STATUS_FUNCTIONS
    ]
    views = [
        f'CREATE OR REPLACE VIEW {f.view} AS SELECT {f.view_columns} FROM {f.name}(compact_today())'
        for f in STATUS_FUNCTIONS
    ]
    return functions + views
