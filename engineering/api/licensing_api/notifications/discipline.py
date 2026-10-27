"""Email for adverse action and significant investigative information events (FLOW-07).

Every state where the PA holds a license or privilege is told, except the state that
reported: it already knows. Staff email says only which state reported and links to sign-in.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from licensing_api.context import ChangeContext
from licensing_api.events import handler
from licensing_api.notifications.recipients import (
    aggregate,
    commission_ops,
    practitioner,
    queue,
    state_contacts,
    state_name,
    states_holding,
)
from licensing_api.repo.adverse_action import AdverseAction, AdverseActionTarget
from licensing_api.repo.domain_event import DomainEvent, EventType
from licensing_api.repo.sii_report import SiiReport
from licensing_api.repo.state_contact import ContactPurpose


@handler(
    'notifications.send_adverse_action',
    EventType.ADVERSE_ACTION_REPORTED,
    EventType.ADVERSE_ACTION_LIFTED,
)
async def send_adverse_action(
    session: AsyncSession, ctx: ChangeContext, event: DomainEvent
) -> None:
    """Tell the PA, the other states where they hold a license or privilege, and the Commission (Rule 5 §5.6(b))."""
    action = await aggregate(session, AdverseAction, event)
    pa = await practitioner(session, action.practitioner_id)
    reported = event.type == EventType.ADVERSE_ACTION_REPORTED
    context = {
        'reporting_state_name': await state_name(session, action.reporting_state_code),
        'against_license': action.against == AdverseActionTarget.QUALIFYING_LICENSE,
        'is_emergency': action.is_emergency,
    }
    pa_template = 'adverse_action_reported' if reported else 'adverse_action_lifted'
    pa_context = context | {'first_name': pa.first_name}
    await queue(session, ctx, event, pa_template, [pa.recipient], pa_context)
    other_states = await states_holding(session, action.practitioner_id) - {
        action.reporting_state_code
    }
    staff = await state_contacts(session, other_states, ContactPurpose.DISCIPLINE)
    await queue(session, ctx, event, f'{pa_template}_staff', staff + commission_ops(), context)


@handler('notifications.send_sii', EventType.SII_FLAGGED, EventType.SII_CLOSED)
async def send_sii(session: AsyncSession, ctx: ChangeContext, event: DomainEvent) -> None:
    """Tell the other states where the PA holds a license or privilege; never the PA (ML §8.C)."""
    report = await aggregate(session, SiiReport, event)
    other_states = await states_holding(session, report.practitioner_id) - {
        report.reporting_state_code
    }
    template = 'sii_flagged_state' if event.type == EventType.SII_FLAGGED else 'sii_closed_state'
    context = {'reporting_state_name': await state_name(session, report.reporting_state_code)}
    staff = await state_contacts(session, other_states, ContactPurpose.DISCIPLINE)
    await queue(session, ctx, event, template, staff, context)


DISCIPLINE_HANDLERS = (send_adverse_action, send_sii)
