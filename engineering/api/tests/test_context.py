"""The signed-in user, the change context, and request IDs (ADR-0009)."""

import logging
import uuid

import pytest
from starlette.requests import Request

from licensing_api.auth import AuthClaims
from licensing_api.context import change_context, current_user, system_context
from licensing_api.errors import AppError, ErrorCode
from tests.factories import make_user, system_user_id


def _claims(email: str, sub: uuid.UUID | None = None) -> AuthClaims:
    return AuthClaims(sub=sub or uuid.uuid4(), email=email)


async def test_current_user_finds_the_user_by_sub(db_session):
    sub = uuid.uuid4()
    user = await make_user(db_session, public_id=sub)

    assert await current_user(_claims('other@example.com', sub), db_session) is user


async def test_first_sign_in_links_the_token_by_email(db_session):
    user = await make_user(db_session, email='new@example.com')
    claims = _claims('new@example.com')

    assert await current_user(claims, db_session) is user
    assert user.public_id == claims.sub


async def test_a_user_linked_to_another_sub_is_not_this_caller(db_session):
    await make_user(db_session, email='shared@example.com', public_id=uuid.uuid4())

    with pytest.raises(AppError) as error:
        await current_user(_claims('shared@example.com'), db_session)

    assert (error.value.status_code, error.value.code) == (403, ErrorCode.UserNotFound)


async def test_an_unknown_user_is_not_found(db_session):
    with pytest.raises(AppError) as error:
        await current_user(_claims('nobody@example.com'), db_session)

    assert error.value.code == ErrorCode.UserNotFound


async def test_an_inactive_user_is_refused_and_not_linked(db_session):
    user = await make_user(db_session, email='gone@example.com', is_active=False)

    with pytest.raises(AppError) as error:
        await current_user(_claims('gone@example.com'), db_session)

    assert error.value.code == ErrorCode.UserInactive
    assert user.public_id is None


async def test_change_context_uses_the_callers_id_and_the_request_id(db_session):
    user = await make_user(db_session)
    request = Request({'type': 'http', 'state': {'request_id': 'req-4'}})

    ctx = await change_context(request, user)

    assert (ctx.user_id, ctx.request_id) == (user.id, 'req-4')


async def test_system_context_acts_as_the_system_user(db_session):
    ctx = await system_context(db_session, 'job-1')

    assert (ctx.user_id, ctx.request_id) == (await system_user_id(db_session), 'job-1')


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
