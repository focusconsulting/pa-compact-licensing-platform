"""Email for privilege, payment, and qualifying license events: FLOW-07's "notify" consumers.

A request or payment event's aggregate is the privilege request; an issue, deactivation,
or expiry event's is the privilege; a license event's is the qualifying license.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, or_, select

from licensing_api.context import ChangeContext
from licensing_api.events import handler
from licensing_api.notifications.recipients import (
    Recipient,
    aggregate,
    commission_ops,
    practitioner,
    queue,
    state_contacts,
    state_name,
)
from licensing_api.repo.domain_event import DomainEvent, EventType
from licensing_api.repo.privilege import AdministratorStatus, DeactivationReason, Privilege
from licensing_api.repo.privilege_request import PrivilegeRequest
from licensing_api.repo.qualifying_license import QualifyingLicense
from licensing_api.repo.reference import RefDenialReason
from licensing_api.repo.state_contact import ContactPurpose

# Deactivations the license cascade makes, so a state learns of the change that ended its privilege.
_LICENSE_DEACTIVATIONS = (
    DeactivationReason.QUALIFYING_LICENSE_INACTIVE,
    DeactivationReason.QUALIFYING_LICENSE_TERMINATED,
)


@handler('notifications.send_privilege_requested', EventType.PRIVILEGE_REQUESTED)
async def send_privilege_requested(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Send the PA a receipt, and tell the remote state a paid request arrived."""
    request = await aggregate(session, PrivilegeRequest, event)
    pa = await practitioner(session, request.practitioner_id)
    context = {'remote_state_name': await state_name(session, request.remote_state_code)}
    pa_context = context | {'first_name': pa.first_name}
    await queue(session, ctx, event, 'privilege_requested', [pa.recipient], pa_context)
    rs = await state_contacts(session, request.remote_state_code, ContactPurpose.PRIVILEGES)
    await queue(session, ctx, event, 'privilege_requested_state', rs, context)


@handler('notifications.send_payment_declined', EventType.PAYMENT_DECLINED)
async def send_payment_declined(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Tell the PA their payment was declined, so they can try again."""
    request = await aggregate(session, PrivilegeRequest, event)
    pa = await practitioner(session, request.practitioner_id)
    context = {
        'first_name': pa.first_name,
        'remote_state_name': await state_name(session, request.remote_state_code),
    }
    await queue(session, ctx, event, 'payment_declined', [pa.recipient], context)


@handler('notifications.send_privilege_issued', EventType.PRIVILEGE_ISSUED)
async def send_privilege_issued(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Give the PA their privilege number and expiry; tell the state of qualifying license and the Commission."""
    privilege = await aggregate(session, Privilege, event)
    pa = await practitioner(session, privilege.practitioner_id)
    context = {'remote_state_name': await state_name(session, privilege.remote_state_code)}
    pa_context = context | {
        'first_name': pa.first_name,
        'privilege_number': privilege.privilege_number,
        'expires_on': privilege.expires_on.isoformat(),
    }
    await queue(session, ctx, event, 'privilege_issued', [pa.recipient], pa_context)
    staff = await _sql_contacts(session, privilege.qualifying_license_id) + commission_ops()
    await queue(session, ctx, event, 'privilege_issued_staff', staff, context)


@handler('notifications.send_privilege_denied', EventType.PRIVILEGE_DENIED)
async def send_privilege_denied(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Tell the PA the remote state's denial and its reason; tell the state of qualifying license and the Commission."""
    request = await aggregate(session, PrivilegeRequest, event)
    pa = await practitioner(session, request.practitioner_id)
    # A denied request always has a reason (chk_privilege_requests_denial_reason).
    reason = select(col(RefDenialReason.label)).where(
        col(RefDenialReason.code) == request.denial_reason_code
    )
    context = {'remote_state_name': await state_name(session, request.remote_state_code)}
    pa_context = context | {
        'first_name': pa.first_name,
        'denial_reason': (await session.scalars(reason)).one(),
    }
    await queue(session, ctx, event, 'privilege_denied', [pa.recipient], pa_context)
    staff = await _sql_contacts(session, request.qualifying_license_id) + commission_ops()
    await queue(session, ctx, event, 'privilege_denied_staff', staff, context)


@handler('notifications.send_privilege_deactivated', EventType.PRIVILEGE_DEACTIVATED)
async def send_privilege_deactivated(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Tell the PA, with the deactivating state's note, and the remote state that issued the privilege."""
    privilege = await aggregate(session, Privilege, event)
    pa = await practitioner(session, privilege.practitioner_id)
    context = {
        'remote_state_name': await state_name(session, privilege.remote_state_code),
        'privilege_number': privilege.privilege_number,
    }
    pa_context = context | {'first_name': pa.first_name, 'note': privilege.deactivation_note}
    await queue(session, ctx, event, 'privilege_deactivated', [pa.recipient], pa_context)
    rs = await state_contacts(session, privilege.remote_state_code, ContactPurpose.PRIVILEGES)
    await queue(session, ctx, event, 'privilege_deactivated_state', rs, context)


@handler(
    'notifications.send_privilege_expiry',
    EventType.PRIVILEGE_EXPIRING,
    EventType.PRIVILEGE_EXPIRED,
)
async def send_privilege_expiry(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Remind the PA a privilege expires soon, or tell them it has; each reminder is its own event."""
    privilege = await aggregate(session, Privilege, event)
    pa = await practitioner(session, privilege.practitioner_id)
    context = {
        'first_name': pa.first_name,
        'remote_state_name': await state_name(session, privilege.remote_state_code),
        'privilege_number': privilege.privilege_number,
        'expires_on': privilege.expires_on.isoformat(),
    }
    expiring = event.type == EventType.PRIVILEGE_EXPIRING
    template = 'privilege_expiring' if expiring else 'privilege_expired'
    await queue(session, ctx, event, template, [pa.recipient], context)


@handler('notifications.send_license_status_changed', EventType.QUALIFYING_LICENSE_STATUS_CHANGED)
async def send_license_status_changed(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Tell the PA, and each remote state whose privilege rests on this license, its new status.

    A privilege counts if it is active or the cascade has just deactivated it for this license.
    """
    license = await aggregate(session, QualifyingLicense, event)
    if license.practitioner_id is None:
        # A license the state reported before any PA claimed it: nobody to tell yet.
        return
    context = {
        'state_name': await state_name(session, license.state_code),
        'status': license.state_reported_status,
    }
    pa = await practitioner(session, license.practitioner_id)
    pa_context = context | {'first_name': pa.first_name}
    await queue(session, ctx, event, 'license_status_changed', [pa.recipient], pa_context)
    remote_states = select(col(Privilege.remote_state_code)).where(
        col(Privilege.qualifying_license_id) == license.id,
        or_(
            col(Privilege.administrator_status) == AdministratorStatus.ACTIVE,
            col(Privilege.deactivation_reason).in_(_LICENSE_DEACTIVATIONS),
        ),
    )
    rs = await state_contacts(
        session, set((await session.scalars(remote_states)).all()), ContactPurpose.PRIVILEGES
    )
    await queue(session, ctx, event, 'license_status_changed_state', rs, context)


async def _sql_contacts(session: AsyncSession, qualifying_license_id: int) -> list[Recipient]:
    """The ``applications`` contacts of the state that issued the qualifying license."""
    statement = select(col(QualifyingLicense.state_code)).where(
        col(QualifyingLicense.id) == qualifying_license_id
    )
    sql_state = (await session.scalars(statement)).one()
    return await state_contacts(session, sql_state, ContactPurpose.APPLICATIONS)


PRIVILEGE_HANDLERS = (
    send_privilege_requested,
    send_payment_declined,
    send_privilege_issued,
    send_privilege_denied,
    send_privilege_deactivated,
    send_privilege_expiry,
    send_license_status_changed,
)
