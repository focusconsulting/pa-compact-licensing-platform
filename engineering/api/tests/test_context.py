"""The change context and request IDs (ADR-0009)."""

import logging
import uuid

import pytest
from sqlalchemy import select
from starlette.requests import Request

from licensing_api.auth import AuthClaims
from licensing_api.context import (
    SYSTEM,
    Actor,
    ChangeContext,
    actor_id,
    change_context,
    stamp_update,
    system_context,
)
from tests.factories import make_issued_privilege, make_user, system_user_id


async def test_actor_id_resolves_a_user_by_sub(db_session):
    sub = uuid.uuid4()
    user = await make_user(db_session, public_id=sub)

    assert await db_session.scalar(select(actor_id(Actor(sub)))) == user.id


async def test_actor_id_resolves_the_system_user(db_session):
    assert await db_session.scalar(select(actor_id(SYSTEM))) == await system_user_id(db_session)


def test_system_context_acts_as_the_system_user():
    assert system_context('job-1') == system_context('job-1')
    assert system_context('job-1').actor == SYSTEM
    assert system_context().request_id is None


async def test_change_context_uses_the_callers_sub_and_the_request_id():
    sub = uuid.uuid4()
    request = Request({'type': 'http', 'state': {'request_id': 'req-4'}})

    ctx = await change_context(request, AuthClaims(sub=sub, email='pa@example.com'))

    assert ctx.actor == Actor(sub)
    assert ctx.request_id == 'req-4'


def test_every_response_carries_a_new_request_id(client):
    response = client.get('/api/health/live')

    assert len(response.headers['X-Request-ID']) == 32


def test_a_valid_inbound_request_id_is_kept(client):
    response = client.get('/api/health/live', headers={'X-Request-ID': '1-abc.def_9'})

    assert response.headers['X-Request-ID'] == '1-abc.def_9'


@pytest.mark.parametrize('inbound', ['has spaces', 'x' * 129, 'line\nbreak'])
def test_an_unsafe_inbound_request_id_is_replaced(client, inbound):
    response = client.get('/api/health/live', headers={'X-Request-ID': inbound})

    assert response.headers['X-Request-ID'] != inbound
    assert len(response.headers['X-Request-ID']) == 32


def test_the_request_log_line_carries_the_request_id(client, caplog):
    with caplog.at_level(logging.INFO, logger='licensing_api.request_logger'):
        response = client.get('/api/health/live', headers={'X-Request-ID': 'trace-123'})

    assert response.headers['X-Request-ID'] == 'trace-123'
    assert any(getattr(record, 'request_id', None) == 'trace-123' for record in caplog.records)


async def test_stamp_update_sets_updated_by_to_the_actor(db_session):
    sub = uuid.uuid4()
    user = await make_user(db_session, public_id=sub)
    privilege = await make_issued_privilege(db_session)

    stamp_update(privilege, ChangeContext(Actor(sub), None))
    privilege.deactivation_note = 'Changed.'
    await db_session.flush()
    await db_session.refresh(privilege)

    assert privilege.updated_by == user.id
