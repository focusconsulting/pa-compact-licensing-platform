"""Which PAs a state is related to, and so may see (Rule 4 §4.6(a), ADR-0020).

Each predicate is an ``EXISTS`` correlated on ``practitioner_id``, a column of the route's
query naming the PA, so a record outside the caller's state is never loaded and answers ``404``
(constitution Principle II). The column must belong to a table in that query's ``FROM``:
otherwise SQLAlchemy adds the table to the subquery instead, and every row matches. A
relationship, once formed, persists: denial, withdrawal, and expiry keep it.
"""

from __future__ import annotations

from sqlalchemy import ColumnElement, exists, or_, select
from sqlmodel import col

from licensing_api.repo.participation_application import (
    ApplicationStatus,
    ParticipationApplication,
)
from licensing_api.repo.privilege_request import PrivilegeRequest
from licensing_api.repo.qualifying_license import QualifyingLicense


def is_sql_for(state_code: str, practitioner_id: ColumnElement[int]) -> ColumnElement[bool]:
    """The PA has applied with ``state_code`` as their state of qualifying license, past a draft."""
    return exists(
        select(1).where(
            col(ParticipationApplication.practitioner_id) == practitioner_id,
            col(ParticipationApplication.sql_state_code) == state_code.upper(),
            col(ParticipationApplication.status) != ApplicationStatus.DRAFT,
        )
    )


def is_remote_for(state_code: str, practitioner_id: ColumnElement[int]) -> ColumnElement[bool]:
    """The PA has paid for a privilege request in ``state_code``; every privilege comes from one.

    ``submitted_at``, not status: an unpaid request can be withdrawn without the state ever
    receiving it (FLOW-06).
    """
    return exists(
        select(1).where(
            col(PrivilegeRequest.practitioner_id) == practitioner_id,
            col(PrivilegeRequest.remote_state_code) == state_code.upper(),
            col(PrivilegeRequest.submitted_at).is_not(None),
        )
    )


def holds_license_in(state_code: str, practitioner_id: ColumnElement[int]) -> ColumnElement[bool]:
    """A qualifying license in ``state_code`` is linked to the PA, whatever its status."""
    return exists(
        select(1).where(
            col(QualifyingLicense.practitioner_id) == practitioner_id,
            col(QualifyingLicense.state_code) == state_code.upper(),
        )
    )


def related_to(state_code: str, practitioner_id: ColumnElement[int]) -> ColumnElement[bool]:
    """Any relationship: the PAs whose uniform data set ``state_code`` may see."""
    return or_(
        is_sql_for(state_code, practitioner_id),
        is_remote_for(state_code, practitioner_id),
        holds_license_in(state_code, practitioner_id),
    )
