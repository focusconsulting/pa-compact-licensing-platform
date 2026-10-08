from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, ForeignKey, String, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel

from licensing_api.repo.base import TimestampTZ, utc_now

SYSTEM_USER_EMAIL = 'system@pa-compact.invalid'


class User(SQLModel, table=True):
    """A person who can sign in, or the system user that workers and jobs write as.

    ``permissions`` maps a state code to the permissions held there, for example
    ``{"KS": ["write", "read_private"]}`` (D5).
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'users'  # type: ignore[assignment]

    id: int = Field(primary_key=True)
    email: str = Field(index=True, unique=True)
    public_id: UUID | None
    given_name: str | None
    family_name: str | None
    role: str
    # users and states reference each other (states.created_by); use_alter breaks the cycle
    # so SQLAlchemy can still order inserts.
    state_code: str | None = Field(
        default=None,
        sa_column=Column(
            String(2), ForeignKey('states.code', name='fk_users_state_code', use_alter=True)
        ),
    )
    is_active: bool
    permissions: dict[str, list[str]] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    )
    created_at: datetime = Field(default_factory=utc_now, sa_type=TimestampTZ)
    created_by: int = Field(foreign_key='users.id')
    updated_at: datetime | None = Field(default=None, nullable=False, sa_type=TimestampTZ)
    updated_by: int | None = Field(default=None, foreign_key='users.id', nullable=False)


async def get_user_by_public_id(session: AsyncSession, public_id: UUID) -> User | None:
    statement = select(User).filter_by(public_id=public_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    statement = select(User).filter_by(email=email)
    result = await session.execute(statement)
    return result.scalar_one_or_none()
