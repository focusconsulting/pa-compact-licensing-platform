from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field

from licensing_api.repo.base import AuditColumns, TimestampTZ, utc_now


class AdverseActionTarget(StrEnum):
    QUALIFYING_LICENSE = 'qualifying_license'
    PRIVILEGE = 'privilege'


class AdverseAction(AuditColumns, table=True):
    """Discipline a state reports against a qualifying license or one privilege (Rule 4 §4.4(a)-(b)). Owner: epic 9.

    Exactly one of ``qualifying_license_id`` and ``privilege_id`` is set, matching
    ``against``. The report carries a summary, an order document, or both. An
    action is in force from ``effective_from`` through ``effective_until``
    (inclusive), or indefinitely while that is NULL. ``is_public = false`` keeps it
    out of public verification. Tier: states and Commission, except public actions.
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'adverse_actions'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    public_id: UUID = Field(default_factory=uuid4, unique=True)
    practitioner_id: int = Field(foreign_key='practitioners.id')
    reporting_state_code: str = Field(foreign_key='states.code')
    against: str
    qualifying_license_id: int | None = Field(default=None, foreign_key='qualifying_licenses.id')
    privilege_id: int | None = Field(default=None, foreign_key='privileges.id')
    action_type_code: str = Field(foreign_key='ref_adverse_action_types.code')
    summary: str | None = None
    order_document_id: int | None = Field(default=None, foreign_key='documents.id')
    ordered_on: date
    effective_from: date
    effective_until: date | None = None
    is_emergency: bool = False
    is_public: bool = False
    reported_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ)


class AdverseActionNpdbCategory(AuditColumns, table=True):
    """An optional NPDB basis-for-action category on an adverse action (Q-17)."""

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'adverse_action_npdb_categories'  # type: ignore[assignment]

    adverse_action_id: int = Field(primary_key=True, foreign_key='adverse_actions.id')
    npdb_category_code: str = Field(primary_key=True, foreign_key='ref_npdb_categories.code')
