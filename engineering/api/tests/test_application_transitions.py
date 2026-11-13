"""FLOW-06's participation application diagram and APPLICATION_TRANSITIONS say the same thing."""

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlmodel import col, select

from licensing_api.context import ChangeContext
from licensing_api.repo.application_transition import InvalidTransitionError, move
from licensing_api.repo.domain_event import DomainEvent, EventType
from licensing_api.repo.history import ParticipationApplicationHistory
from licensing_api.repo.participation_application import (
    APPLICATION_TRANSITIONS,
    ApplicationStatus,
)
from tests.factories import (
    make_application,
    make_eligible_application,
    make_practitioner,
    system_user_id,
)

_FLOW_06 = Path(__file__).parents[3] / 'product/context/flows/06-state-machines.md'


def _diagram_edges() -> set[tuple[str, str]]:
    section = _FLOW_06.read_text().split('## Participation application')[1].split('\n## ')[0]
    diagram = section.split('```mermaid')[1].split('```')[0]
    return {
        (source, target)
        for source, target in re.findall(r'^\s*(\S+) --> (\S+?):?(?:\s|$)', diagram, re.MULTILINE)
        if '[*]' not in (source, target)
    }


def test_flow_06_has_exactly_the_coded_transitions():
    coded = {
        (source.value, target.value)
        for source, targets in APPLICATION_TRANSITIONS.items()
        for target in targets
    }

    assert _diagram_edges() == coded


def test_every_status_is_reachable_in_flow_06():
    named = {status for edge in _diagram_edges() for status in edge}

    assert named == {status.value for status in ApplicationStatus}


async def test_a_move_flow_06_does_not_allow_is_refused(db_session):
    application = await make_application(db_session, await make_practitioner(db_session))
    ctx = ChangeContext(await system_user_id(db_session), 'req-move')

    with pytest.raises(InvalidTransitionError, match='draft cannot become eligible'):
        await move(db_session, ctx, application, ApplicationStatus.ELIGIBLE, None)

    assert application.status == ApplicationStatus.DRAFT


async def test_a_move_without_an_event_records_only_what_changed(db_session):
    application = await make_eligible_application(db_session, await make_practitioner(db_session))
    ctx = ChangeContext(await system_user_id(db_session), 'req-move')
    superseded_at = datetime(2026, 11, 1, tzinfo=timezone.utc)

    await move(
        db_session,
        ctx,
        application,
        ApplicationStatus.SUPERSEDED,
        None,
        superseded_at=superseded_at,
    )

    [history] = (
        await db_session.scalars(
            select(ParticipationApplicationHistory).where(
                col(ParticipationApplicationHistory.entity_id) == application.id
            )
        )
    ).all()
    assert set(history.updated) == {'status', 'superseded_at'}


async def test_submitting_records_the_whole_application_and_its_event(db_session):
    application = await make_application(db_session, await make_practitioner(db_session))
    ctx = ChangeContext(await system_user_id(db_session), 'req-move')
    opened_at = datetime(2026, 11, 2, tzinfo=timezone.utc)

    await move(
        db_session,
        ctx,
        application,
        ApplicationStatus.SUBMITTED,
        EventType.APPLICATION_SUBMITTED,
        opened_at=opened_at,
    )

    [history] = (
        await db_session.scalars(
            select(ParticipationApplicationHistory).where(
                col(ParticipationApplicationHistory.entity_id) == application.id
            )
        )
    ).all()
    assert history.previous is None
    assert history.updated['sql_state_code'] == 'KS'
    events = (
        await db_session.scalars(
            select(DomainEvent.type).where(col(DomainEvent.aggregate_id) == application.id)
        )
    ).all()
    assert events == [EventType.APPLICATION_SUBMITTED]
