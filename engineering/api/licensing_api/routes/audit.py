from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from licensing_api.dependencies import get_db_session
from licensing_api.permissions import Permission, require
from licensing_api.repo.audit_log import AuditLogEntry, audit_entries
from licensing_api.repo.pagination import paginate
from licensing_api.repo.user import User, emails_by_id, get_user_by_email
from licensing_api.responses import Paged, PageQuery, page_query

router = APIRouter(prefix='/audit')


class AuditEntryOut(BaseModel):
    """One staff read of private data or security event. ``before`` and ``after`` never hold an SSN."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            'examples': [
                {
                    'occurred_at': '2026-10-21T14:05:00Z',
                    'action': 'ssn.revealed',
                    'entity_type': 'practitioner',
                    'entity_id': 42,
                    'entity_key': None,
                    'actor_email': 'pat.morgan@example.com',
                    'reason': 'Verifying identity for an application',
                    'request_id': '9b2e4f7a1c3d4e5f8a6b7c8d9e0f1a2b',
                    'before': None,
                    'after': None,
                }
            ]
        },
    )

    occurred_at: datetime
    action: str
    entity_type: str
    entity_id: int | None
    entity_key: str | None
    actor_email: str | None
    reason: str | None
    request_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None


@router.get(
    '',
    name='List audit log entries',
    description=(
        'Staff reads of private data and security events, newest first. Filters combine; '
        '`occurred_to` is exclusive. Changes to records are in their history, not here.'
    ),
)
async def list_audit_entries(
    _caller: Annotated[User, require(Permission.COMPACT_ADMIN)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    query: Annotated[PageQuery, page_query('occurred_at', default_sort='-occurred_at')],
    action: Annotated[str | None, Query(description='For example `ssn.revealed`')] = None,
    entity_type: Annotated[str | None, Query(description='A table name')] = None,
    entity_id: int | None = None,
    entity_key: str | None = None,
    actor_email: str | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
) -> Paged[AuditEntryOut]:
    """Page through the audit log; an unknown ``actor_email`` matches nothing."""
    actor_user_id = None
    if actor_email is not None:
        actor = await get_user_by_email(session, actor_email)
        if actor is None:
            return Paged(data=[], page=query.page_of(0))
        actor_user_id = actor.id
    statement = audit_entries(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_key=entity_key,
        actor_user_id=actor_user_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    rows, total = await paginate(
        session,
        statement,
        query,
        {'occurred_at': col(AuditLogEntry.occurred_at)},
        tiebreaker=col(AuditLogEntry.id),
    )
    emails = await emails_by_id(session, (r.actor_user_id for r in rows if r.actor_user_id))
    return Paged(
        data=[
            AuditEntryOut.model_validate(
                {**row.model_dump(), 'actor_email': emails.get(row.actor_user_id or 0)}
            )
            for row in rows
        ],
        page=query.page_of(total),
    )
