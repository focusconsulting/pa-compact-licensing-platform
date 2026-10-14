"""History tables: one append-only row per change to an entity (ADR-0005, ADR-0008).

Rows can only be redacted, inside an expungement transaction.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel

from licensing_api.context import ChangeContext, actor_id
from licensing_api.repo.adverse_action import AdverseAction
from licensing_api.repo.base import TimestampTZ, entity_ref, utc_now
from licensing_api.repo.fee import Fee
from licensing_api.repo.participation_application import ParticipationApplication
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.privilege import Privilege
from licensing_api.repo.privilege_request import PrivilegeRequest
from licensing_api.repo.qualifying_license import QualifyingLicense
from licensing_api.repo.sii_report import SiiReport
from licensing_api.repo.state import State

# Keys and audit columns: the history row records them itself.
_UNTRACKED = frozenset({'id', 'public_id', 'created_at', 'created_by', 'updated_at', 'updated_by'})


class HistoryRecord(SQLModel):
    """Columns shared by every history table. Each subclass adds ``entity_id`` pointing at its entity.

    JSON fields use ``sa_type``, not ``sa_column``: a Column object cannot be shared by several tables.
    """

    id: int | None = Field(default=None, primary_key=True)
    changed_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ)
    changed_by: int = Field(foreign_key='users.id')
    # When the change took effect, if different from when it was recorded.
    effective_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    previous: dict[str, Any] | None = Field(default=None, sa_type=JSONB)
    updated: dict[str, Any] | None = Field(default=None, sa_type=JSONB)
    removed: dict[str, Any] | None = Field(default=None, sa_type=JSONB)


class PractitionerHistory(HistoryRecord, table=True):
    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'practitioners_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='practitioners.id')


class QualifyingLicenseHistory(HistoryRecord, table=True):
    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'qualifying_licenses_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='qualifying_licenses.id')


class ParticipationApplicationHistory(HistoryRecord, table=True):
    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'participation_applications_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='participation_applications.id')


class PrivilegeRequestHistory(HistoryRecord, table=True):
    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'privilege_requests_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='privilege_requests.id')


class PrivilegeHistory(HistoryRecord, table=True):
    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'privileges_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='privileges.id')


class AdverseActionHistory(HistoryRecord, table=True):
    """Every update a reporting state makes to an adverse action (Rule 4 §4.4(b)(3))."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'adverse_actions_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='adverse_actions.id')


class SiiReportHistory(HistoryRecord, table=True):
    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'sii_reports_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='sii_reports.id')


class StateHistory(HistoryRecord, table=True):
    """Changes to a state's configuration (S-01). Keyed by ``state_code``: states have no numeric id."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'states_history'  # type: ignore[assignment]

    state_code: str = Field(foreign_key='states.code', max_length=2)


class FeeHistory(HistoryRecord, table=True):
    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'fees_history'  # type: ignore[assignment]

    entity_id: int = Field(foreign_key='fees.id')


_HISTORY_TABLES: Mapping[type[SQLModel], type[HistoryRecord]] = {
    Practitioner: PractitionerHistory,
    QualifyingLicense: QualifyingLicenseHistory,
    ParticipationApplication: ParticipationApplicationHistory,
    PrivilegeRequest: PrivilegeRequestHistory,
    Privilege: PrivilegeHistory,
    AdverseAction: AdverseActionHistory,
    SiiReport: SiiReportHistory,
    State: StateHistory,
    Fee: FeeHistory,
}


def snapshot(entity: SQLModel) -> dict[str, Any]:
    """The entity's tracked fields as JSON values. Take it before changing the entity and pass it to ``write``."""
    return entity.model_dump(mode='json', exclude=set(_UNTRACKED))


async def write(
    session: AsyncSession,
    ctx: ChangeContext,
    entity: SQLModel,
    *,
    before: Mapping[str, Any] | None,
    effective_at: datetime | None = None,
) -> HistoryRecord | None:
    """Record one change to ``entity`` in its history table, in the caller's transaction.

    ``before`` is ``snapshot(entity)`` from before the change, or None for a new row.
    The row holds the whole ``before`` as ``previous``, the fields that changed to a
    value as ``updated``, and the fields that changed to null, with their old values,
    as ``removed``. Writes nothing and returns None when no tracked field changed.
    """
    history_table = _HISTORY_TABLES.get(type(entity))
    if history_table is None:
        raise ValueError(f'{type(entity).__name__} has no history table')
    await session.flush()
    after = snapshot(entity)
    changed = [
        field for field, value in after.items() if before is None or before.get(field) != value
    ]
    if before is not None and not changed:
        return None
    updated = {field: after[field] for field in changed if after[field] is not None}
    removed = {
        field: before[field] for field in changed if before is not None and after[field] is None
    }
    ref = entity_ref(entity)
    key = {'state_code': ref.key} if history_table is StateHistory else {'entity_id': ref.id}
    statement = (
        insert(history_table)
        .values(
            **key,
            changed_by=actor_id(ctx.actor),
            effective_at=effective_at,
            previous=dict(before) if before is not None else None,
            updated=updated or None,
            removed=removed or None,
        )
        .returning(history_table)
    )
    return (await session.scalars(statement)).one()
