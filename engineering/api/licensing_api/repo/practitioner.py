from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlmodel import Field

from licensing_api.repo.base import AuditColumns, TimestampTZ


class Practitioner(AuditColumns, table=True):
    """A PA's uniform data set (Rule 4 §4.3(c)), held by the Commission and written by several parties.

    The PA enters the fields; the state of qualifying license verifies them. Each
    field group (identity, residence, contact, education, certification) records
    who entered it and which state verified it when. Tier: private. Owner: platform.
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'practitioners'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    public_id: UUID = Field(default_factory=uuid4, unique=True)
    user_id: int = Field(foreign_key='users.id', unique=True)
    current_sql_state_code: str | None = Field(default=None, foreign_key='states.code')

    legal_first_name: str | None = None
    legal_middle_name: str | None = None
    legal_last_name: str | None = None
    name_suffix: str | None = None
    sex_code: str | None = Field(default=None, foreign_key='ref_sex.code')
    date_of_birth: date | None = None
    residence_line1: str | None = None
    residence_line2: str | None = None
    residence_city: str | None = None
    residence_region: str | None = None
    residence_postal_code: str | None = None
    residence_country_code: str | None = None
    phone: str | None = None
    correspondence_email: str | None = None
    pa_program_name: str | None = None
    pa_program_graduation_year: int | None = None
    nccpa_certification_number: str | None = None
    nccpa_certification_status: str | None = None
    nccpa_certification_expires_on: date | None = None
    npi: str | None = None

    identity_entered_by: int | None = Field(default=None, foreign_key='users.id')
    identity_verified_by_state: str | None = Field(default=None, foreign_key='states.code')
    identity_verified_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    residence_entered_by: int | None = Field(default=None, foreign_key='users.id')
    residence_verified_by_state: str | None = Field(default=None, foreign_key='states.code')
    residence_verified_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    contact_entered_by: int | None = Field(default=None, foreign_key='users.id')
    contact_verified_by_state: str | None = Field(default=None, foreign_key='states.code')
    contact_verified_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    education_entered_by: int | None = Field(default=None, foreign_key='users.id')
    education_verified_by_state: str | None = Field(default=None, foreign_key='states.code')
    education_verified_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    certification_entered_by: int | None = Field(default=None, foreign_key='users.id')
    certification_verified_by_state: str | None = Field(default=None, foreign_key='states.code')
    certification_verified_at: datetime | None = Field(default=None, sa_type=TimestampTZ)


class PractitionerSsn(AuditColumns, table=True):
    """A practitioner's SSN, encrypted by the application (ADR-0007). Tier: restricted.

    Never read in full without ``read_ssn`` and an ``audit_log`` row. Changes are
    audited without the value, so there is no history table.
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'practitioner_ssn'  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    practitioner_id: int = Field(foreign_key='practitioners.id', unique=True)
    ssn_ciphertext: bytes
    ssn_key_version: int
    ssn_lookup_hash: bytes = Field(unique=True)
    ssn_last4: str = Field(max_length=4)
