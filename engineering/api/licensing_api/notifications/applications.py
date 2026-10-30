"""Email for practitioner and application events: FLOW-07's "notify" consumers.

Each event's aggregate is the practitioner or the application. Emails link to sign-in,
and carry no notes: an information request says only that one is waiting.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, or_, select

from licensing_api.context import ChangeContext
from licensing_api.events import handler
from licensing_api.notifications.recipients import (
    commission_ops,
    practitioner,
    queue,
    state_contacts,
    state_name,
)
from licensing_api.repo.domain_event import DomainEvent, EventType
from licensing_api.repo.participation_application import ParticipationApplication
from licensing_api.repo.privilege import AdministratorStatus, DeactivationReason, Privilege
from licensing_api.repo.reference import RefDenialReason
from licensing_api.repo.state_contact import ContactPurpose


async def _application(session: AsyncSession, event: DomainEvent) -> ParticipationApplication:
    statement = select(ParticipationApplication).where(
        col(ParticipationApplication.id) == event.aggregate_id
    )
    return (await session.scalars(statement)).one()


@handler('notifications.send_welcome', EventType.PRACTITIONER_REGISTERED)
async def send_welcome(session: AsyncSession, ctx: ChangeContext, event: DomainEvent) -> None:
    """Welcome a newly registered PA."""
    if event.aggregate_id is None:
        raise ValueError(f'{event.type} event {event.event_id} has no aggregate_id')
    pa = await practitioner(session, event.aggregate_id)
    await queue(session, ctx, event, 'welcome', [pa.recipient], {'first_name': pa.first_name})


@handler('notifications.send_application_submitted', EventType.APPLICATION_SUBMITTED)
async def send_application_submitted(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Confirm to the PA, and tell the state of qualifying license, that an application arrived."""
    application = await _application(session, event)
    pa = await practitioner(session, application.practitioner_id)
    context = {'state_name': await state_name(session, application.sql_state_code)}
    pa_context = context | {'first_name': pa.first_name}
    await queue(session, ctx, event, 'application_submitted', [pa.recipient], pa_context)
    sql = await state_contacts(session, application.sql_state_code, ContactPurpose.APPLICATIONS)
    await queue(session, ctx, event, 'application_submitted_state', sql, context)


@handler('notifications.send_application_info_requested', EventType.APPLICATION_INFO_REQUESTED)
async def send_application_info_requested(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Tell the PA the state needs more from them. A link only, never the note (FLOW-07, D15)."""
    application = await _application(session, event)
    pa = await practitioner(session, application.practitioner_id)
    context = {
        'first_name': pa.first_name,
        'state_name': await state_name(session, application.sql_state_code),
    }
    await queue(session, ctx, event, 'application_info_requested', [pa.recipient], context)


@handler('notifications.send_application_resubmitted', EventType.APPLICATION_RESUBMITTED)
async def send_application_resubmitted(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Tell the state of qualifying license the PA answered its request."""
    application = await _application(session, event)
    sql = await state_contacts(session, application.sql_state_code, ContactPurpose.APPLICATIONS)
    context = {'state_name': await state_name(session, application.sql_state_code)}
    await queue(session, ctx, event, 'application_resubmitted_state', sql, context)


@handler(
    'notifications.send_application_decided',
    EventType.APPLICATION_ELIGIBLE,
    EventType.APPLICATION_DENIED,
)
async def send_application_decided(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Tell the PA and the Commission the state's decision; a denial names its reason and the appeal route."""
    application = await _application(session, event)
    pa = await practitioner(session, application.practitioner_id)
    sql_state = await state_name(session, application.sql_state_code)
    eligible = event.type == EventType.APPLICATION_ELIGIBLE
    context: dict[str, object] = {'first_name': pa.first_name, 'state_name': sql_state}
    if not eligible:
        context['denial_reason'] = await _denial_reason(session, application)
    template = 'application_eligible' if eligible else 'application_denied'
    await queue(session, ctx, event, template, [pa.recipient], context)
    commission = {'state_name': sql_state, 'eligible': eligible}
    await queue(session, ctx, event, 'application_decided_commission', commission_ops(), commission)


async def _denial_reason(session: AsyncSession, application: ParticipationApplication) -> str:
    # A denied application always has a reason (chk_participation_applications_denial_reason).
    statement = select(col(RefDenialReason.label)).where(
        col(RefDenialReason.code) == application.denial_reason_code
    )
    return (await session.scalars(statement)).one()


@handler('notifications.send_application_withdrawn', EventType.APPLICATION_WITHDRAWN)
async def send_application_withdrawn(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Tell the PA and the state of qualifying license that the application was withdrawn."""
    application = await _application(session, event)
    pa = await practitioner(session, application.practitioner_id)
    context = {'state_name': await state_name(session, application.sql_state_code)}
    pa_context = context | {'first_name': pa.first_name}
    await queue(session, ctx, event, 'application_withdrawn', [pa.recipient], pa_context)
    sql = await state_contacts(session, application.sql_state_code, ContactPurpose.APPLICATIONS)
    await queue(session, ctx, event, 'application_withdrawn_state', sql, context)


@handler('notifications.send_eligibility_withdrawn', EventType.APPLICATION_ELIGIBILITY_WITHDRAWN)
async def send_eligibility_withdrawn(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Tell the PA, and each remote state where they hold a privilege, that compact eligibility was withdrawn.

    The cascade may already have deactivated those privileges, so a privilege counts if it
    is active or was deactivated for this reason (Rule 3 §3.9).
    """
    application = await _application(session, event)
    pa = await practitioner(session, application.practitioner_id)
    sql_state = await state_name(session, application.sql_state_code)
    await queue(
        session,
        ctx,
        event,
        'application_eligibility_withdrawn',
        [pa.recipient],
        {'first_name': pa.first_name, 'state_name': sql_state},
    )
    remote_states = select(col(Privilege.remote_state_code)).where(
        col(Privilege.practitioner_id) == application.practitioner_id,
        or_(
            col(Privilege.administrator_status) == AdministratorStatus.ACTIVE,
            col(Privilege.deactivation_reason) == DeactivationReason.ELIGIBILITY_WITHDRAWN,
        ),
    )
    for remote_state in sorted(set((await session.scalars(remote_states)).all())):
        await queue(
            session,
            ctx,
            event,
            'application_eligibility_withdrawn_state',
            await state_contacts(session, remote_state, ContactPurpose.PRIVILEGES),
            {'state_name': sql_state, 'remote_state_name': await state_name(session, remote_state)},
        )


APPLICATION_HANDLERS = (
    send_welcome,
    send_application_submitted,
    send_application_info_requested,
    send_application_resubmitted,
    send_application_decided,
    send_application_withdrawn,
    send_eligibility_withdrawn,
)
