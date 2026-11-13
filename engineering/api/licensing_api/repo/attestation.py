"""The attestations catalogue, and the attestations a PA accepted on an application (platform contract)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKeyConstraint, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, col, select
from sqlmodel.sql.expression import SelectOfScalar

from licensing_api.repo.base import AuditColumns, TimestampTZ, utc_now

if TYPE_CHECKING:
    # Annotations only: licensing_api.context imports the repo package, so a runtime import would be circular.
    from licensing_api.context import ChangeContext


class AttestationAppliesTo(StrEnum):
    """What an attestation is for: the PA's participation application, the state's eligibility check, or a privilege request."""

    PARTICIPATION = 'participation'
    # The Rule 3 §3.3(a) requirements the state checks (§3.4(b)(1)); the PA does not accept them.
    ELIGIBILITY = 'eligibility'
    PRIVILEGE = 'privilege'


class Attestation(AuditColumns, table=True):
    """One version of a statement a PA accepts. Only ``retired_at`` ever changes; new wording is a new version."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'attestations'  # type: ignore[assignment]

    code: str = Field(primary_key=True)
    version: int = Field(primary_key=True)
    applies_to: str
    state_code: str | None = Field(default=None, foreign_key='states.code')
    sort_order: int
    text: str
    source: str
    retired_at: datetime | None = Field(default=None, sa_type=TimestampTZ)


class ParticipationApplicationAttestation(AuditColumns, table=True):
    """An attestation a PA accepted on a participation application. Append-only; the latest version per code counts."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'participation_application_attestations'  # type: ignore[assignment]
    __table_args__ = (
        ForeignKeyConstraint(
            ['attestation_code', 'attestation_version'],
            ['attestations.code', 'attestations.version'],
        ),
    )

    participation_application_id: int = Field(
        primary_key=True, foreign_key='participation_applications.id'
    )
    attestation_code: str = Field(primary_key=True)
    attestation_version: int = Field(primary_key=True)
    # In the key: a resubmission accepts the same version again (Rule 3 §3.7(a)(1)).
    accepted_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ, primary_key=True)


def current_attestations(applies_to: AttestationAppliesTo) -> SelectOfScalar[Attestation]:
    """The highest unretired version of each code that applies to every state, in display order."""
    latest = (
        select(Attestation.code, func.max(Attestation.version).label('version'))
        .where(
            col(Attestation.applies_to) == applies_to,
            col(Attestation.state_code).is_(None),
            col(Attestation.retired_at).is_(None),
        )
        .group_by(col(Attestation.code))
        .subquery()
    )
    return (
        select(Attestation)
        .join(
            latest,
            (col(Attestation.code) == latest.c.code)
            & (col(Attestation.version) == latest.c.version),
        )
        .order_by(col(Attestation.sort_order), col(Attestation.code))
    )


async def accept(
    session: AsyncSession,
    ctx: ChangeContext,
    application_id: int,
    attestation: Attestation,
    since: datetime | None = None,
) -> None:
    """Record that the PA accepted this version on their application.

    Accepting it again is a no-op, unless every acceptance came before ``since``: the state's
    latest request for information, after which the PA accepts each statement again.
    """
    if attestation.applies_to != AttestationAppliesTo.PARTICIPATION:
        raise ValueError(f'{attestation.code} is not a participation attestation')
    if (attestation.code, attestation.version) in await _accepted(session, application_id, since):
        return
    statement = (
        insert(ParticipationApplicationAttestation)
        .values(
            participation_application_id=application_id,
            attestation_code=attestation.code,
            attestation_version=attestation.version,
            accepted_at=utc_now(),
            created_by=ctx.user_id,
        )
        .on_conflict_do_nothing()
    )
    await session.execute(statement)


async def out_of_date_codes(
    session: AsyncSession, application_id: int, since: datetime | None = None
) -> Sequence[str]:
    """Current participation attestations the application has not accepted at their current version since ``since``.

    Submit and resubmit refuse while any are left: ``409 ATTESTATIONS_OUT_OF_DATE`` (platform contract).
    """
    current = (
        await session.scalars(current_attestations(AttestationAppliesTo.PARTICIPATION))
    ).all()
    accepted = await _accepted(session, application_id, since)
    return [a.code for a in current if (a.code, a.version) not in accepted]


async def _accepted(
    session: AsyncSession, application_id: int, since: datetime | None
) -> set[tuple[str, int]]:
    statement = select(
        ParticipationApplicationAttestation.attestation_code,
        ParticipationApplicationAttestation.attestation_version,
    ).where(col(ParticipationApplicationAttestation.participation_application_id) == application_id)
    if since is not None:
        statement = statement.where(col(ParticipationApplicationAttestation.accepted_at) > since)
    return {(code, version) for code, version in await session.execute(statement)}
