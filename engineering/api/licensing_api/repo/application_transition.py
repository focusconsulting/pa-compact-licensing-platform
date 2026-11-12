"""Moving a participation application between statuses (platform contract, "Participation applications").

Its own module because ``history`` imports the application model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from licensing_api.repo import history
from licensing_api.repo.domain_event import EventType, emit
from licensing_api.repo.participation_application import (
    APPLICATION_TRANSITIONS,
    ApplicationStatus,
    ParticipationApplication,
)

if TYPE_CHECKING:
    # Annotations only: licensing_api.context imports the repo package, so a runtime import would be circular.
    from licensing_api.context import ChangeContext

# The application as the PA sends it: history starts when the SQL receives it, so these
# moves record the whole application rather than what changed since the last history row.
_SENT = frozenset({EventType.APPLICATION_SUBMITTED, EventType.APPLICATION_RESUBMITTED})


class InvalidTransitionError(ValueError):
    """``APPLICATION_TRANSITIONS`` does not allow the move."""


async def move(
    session: AsyncSession,
    ctx: ChangeContext,
    application: ParticipationApplication,
    to: ApplicationStatus,
    event: EventType | None,
    **fields: Any,
) -> None:
    """Set the status and ``fields``, then write history and ``event`` in the caller's transaction. The caller commits."""
    current = ApplicationStatus(application.status)
    if to not in APPLICATION_TRANSITIONS.get(current, frozenset()):
        raise InvalidTransitionError(f'An application that is {current} cannot become {to}')
    before = None if event in _SENT else history.snapshot(application)
    for name, value in {'status': to, **fields}.items():
        setattr(application, name, value)
    application.updated_by = ctx.user_id
    await history.write(session, ctx, application, before=before)
    if event is not None:
        await emit(session, ctx, event, application)
