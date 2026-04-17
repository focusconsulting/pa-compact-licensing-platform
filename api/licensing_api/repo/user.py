from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = 'users'  # type: ignore[assignment]

    id: int = Field(primary_key=True)
    email: str = Field(index=True, unique=True)
    public_id: UUID | None
    given_name: str | None
    family_name: str | None
    role: str
    state_code: str | None
    is_active: bool
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: int | None = Field(foreign_key='users.id')


async def get_user_by_public_id(session: AsyncSession, public_id: UUID) -> User | None:
    statement = select(User).filter_by(public_id=public_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    statement = select(User).filter_by(email=email)
    result = await session.execute(statement)
    return result.scalar_one_or_none()
