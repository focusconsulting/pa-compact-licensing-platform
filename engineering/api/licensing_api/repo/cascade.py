"""The privilege cascade: the one function every epic calls to deactivate privileges (FLOW-05).

Its own module because ``history`` imports ``privilege``.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.repo import history
from licensing_api.repo.domain_event import EventType, emit
from licensing_api.repo.privilege import AdministratorStatus, DeactivationReason, Privilege

if TYPE_CHECKING:
    # Annotations only: licensing_api.context imports the repo package, so a runtime import would be circular.
    from licensing_api.context import ChangeContext


async def deactivate_privileges(
    session: AsyncSession,
    ctx: ChangeContext,
    *,
    practitioner_id: int,
    reason: DeactivationReason,
    effective_at: datetime,
    note: str | None = None,
    remote_state_code: str | None = None,
) -> list[Privilege]:
    """Deactivate every active privilege of the practitioner, or only those in one remote state.

    Runs in the caller's transaction, beside the change that triggers it: sets
    ``administrator_status``, the reason, ``deactivated_at`` (``effective_at``), and
    the note, with one history row and one ``privilege.deactivated`` event per
    privilege. The PA's notification comes from that event's handler. Nothing
    reactivates a privilege (ML §4.C), so an inactive one is left as it is.
    """
    statement = (
        select(Privilege)
        .where(
            col(Privilege.practitioner_id) == practitioner_id,
            col(Privilege.administrator_status) == AdministratorStatus.ACTIVE,
        )
        .order_by(col(Privilege.id))
        .with_for_update()
    )
    if remote_state_code is not None:
        statement = statement.where(col(Privilege.remote_state_code) == remote_state_code)
    privileges = list((await session.scalars(statement)).all())
    for privilege in privileges:
        before = history.snapshot(privilege)
        privilege.administrator_status = AdministratorStatus.INACTIVE
        privilege.deactivation_reason = reason
        privilege.deactivated_at = effective_at
        privilege.deactivation_note = note
        privilege.updated_by = ctx.user_id
        await history.write(session, ctx, privilege, before=before, effective_at=effective_at)
        await emit(
            session,
            ctx,
            EventType.PRIVILEGE_DEACTIVATED,
            privilege,
            {
                'privilege_id': privilege.id,
                'practitioner_id': practitioner_id,
                'remote_state_code': privilege.remote_state_code,
                'reason': reason,
            },
        )
    return privileges
