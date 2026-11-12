"""The FSMB client: against fsmb-mock for FSMB's answers, and a stub transport for the bearer's lifecycle."""

import json
import logging
from collections.abc import AsyncGenerator, Callable
from datetime import UTC, date, datetime

import httpx
import pytest

from licensing_api.config import Settings
from licensing_api.fsmb import (
    BoardActionStatus,
    FsmbClient,
    FsmbError,
    ReportStatus,
    create_fsmb_client,
)
from tests.conftest import TEST_SETTINGS

_CLEARED = '999999907'
_ALERTED = '999999915'
_FAILED_REPORT = '999999923'
_PENDING_REPORT = '999999931'
_UNAVAILABLE = '999999949'
_NOT_ON_ROSTER = '123456789'


@pytest.fixture
async def fsmb() -> AsyncGenerator[FsmbClient]:
    client = create_fsmb_client(TEST_SETTINGS)
    yield client
    await client.aclose()


async def test_a_cleared_member_has_a_succeeded_report(fsmb):
    member = await fsmb.get_member(_CLEARED)

    assert member is not None
    assert member.fid == _CLEARED
    assert member.full_name == 'Alexa Wood Checkey'
    assert member.birth_date == date(1988, 9, 2)
    assert member.board_action_status is BoardActionStatus.CLEARED
    assert member.current_report is not None
    assert member.current_report.report_status is ReportStatus.SUCCEEDED
    assert member.current_report.report_date_utc == datetime(2023, 1, 18, 19, 23, 7, tzinfo=UTC)


async def test_an_alerted_member_reports_board_actions(fsmb):
    member = await fsmb.get_member(_ALERTED)

    assert member is not None
    assert member.board_action_status is BoardActionStatus.ALERTED


@pytest.mark.parametrize(
    ('fid', 'report_status', 'is_complete'),
    [(_FAILED_REPORT, ReportStatus.FAILED, True), (_PENDING_REPORT, ReportStatus.PENDING, False)],
    ids=['failed', 'pending'],
)
async def test_a_member_without_a_succeeded_report_is_unknown(
    fsmb, fid, report_status, is_complete
):
    member = await fsmb.get_member(fid)

    assert member is not None
    assert member.board_action_status is BoardActionStatus.UNKNOWN
    assert member.current_report is not None
    assert member.current_report.report_status is report_status
    assert member.current_report.is_complete is is_complete


async def test_a_pending_report_has_no_date_yet(fsmb):
    member = await fsmb.get_member(_PENDING_REPORT)

    assert member is not None and member.current_report is not None
    assert member.current_report.report_date_utc is None


async def test_an_fid_not_on_the_roster_is_none(fsmb):
    assert await fsmb.get_member(_NOT_ON_ROSTER) is None


@pytest.mark.parametrize('fid', ['12345678', '1234567890', 'abcdefghi', '12345678 '])
async def test_an_fid_that_is_not_nine_digits_is_refused_before_calling(fid):
    def fail(request: httpx.Request) -> httpx.Response:
        raise AssertionError('FSMB was called')

    with pytest.raises(ValueError, match='nine digits'):
        await _stubbed(fail).get_member(fid)


async def test_an_fsmb_error_raises(fsmb):
    with pytest.raises(FsmbError, match='503'):
        await fsmb.get_member(_UNAVAILABLE)


async def test_refused_credentials_raise():
    settings = Settings(fsmb_api_url=TEST_SETTINGS.fsmb_api_url, fsmb_client_id='someone-else')
    client = create_fsmb_client(settings)
    try:
        with pytest.raises(FsmbError, match='refused the client credentials'):
            await client.get_member(_CLEARED)
    finally:
        await client.aclose()


async def test_calls_are_logged_without_the_member(fsmb, caplog):
    caplog.set_level(logging.INFO, logger='licensing_api.fsmb')

    await fsmb.get_member(_CLEARED)
    await fsmb.get_member(_NOT_ON_ROSTER)

    calls = [(r.__dict__['operation'], r.__dict__['outcome']) for r in caplog.records]
    assert calls == [('grant', 'ok'), ('get_member', 'ok'), ('get_member', 'missing')]
    assert all(isinstance(r.__dict__['duration_ms'], int) for r in caplog.records)
    assert _CLEARED not in caplog.text and 'Checkey' not in caplog.text


# Stub transport: the bearer's lifecycle, which fsmb-mock cannot expire or revoke.


def _grant(bearer: str, expires_in: int = 3600) -> httpx.Response:
    body = {'expires_in': expires_in, 'token_type': 'Bearer', 'scope': 'pdc.member_read'}
    return httpx.Response(200, json={'access_token': bearer, **body})


_MEMBER = {
    'fid': _CLEARED,
    'fullName': 'Alexa Wood Checkey',
    'birthDate': '1988-09-02',
    'boardActionStatus': 'Cleared',
}


class _Fsmb:
    """Issues bearers in turn and accepts only those in ``accepted``."""

    def __init__(self, *grants: httpx.Response, accepted: set[str]) -> None:
        self.grants = list(grants)
        self.accepted = accepted
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == '/connect/token':
            return self.grants.pop(0)
        if request.headers['Authorization'].removeprefix('Bearer ') in self.accepted:
            return httpx.Response(200, json=_MEMBER)
        return httpx.Response(401)

    @property
    def grant_requests(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path == '/connect/token']


def _stubbed(
    handler: Callable[[httpx.Request], httpx.Response], customer_key: str = 'me'
) -> FsmbClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url='https://fsmb.test')
    return FsmbClient(http, client_id='id', client_secret='secret', customer_key=customer_key)


async def test_the_grant_sends_the_client_credentials_for_the_member_scope():
    fsmb = _Fsmb(_grant('first'), accepted={'first'})

    await _stubbed(fsmb).get_member(_CLEARED)

    form = dict(httpx.QueryParams(fsmb.grant_requests[0].content.decode()))
    assert form == {
        'grant_type': 'client_credentials',
        'client_id': 'id',
        'client_secret': 'secret',
        'scope': 'pdc.member_read',
    }


async def test_one_bearer_serves_calls_until_it_nears_expiry():
    fsmb = _Fsmb(_grant('first'), accepted={'first'})
    client = _stubbed(fsmb)

    await client.get_member(_CLEARED)
    await client.get_member(_CLEARED)

    assert len(fsmb.grant_requests) == 1


async def test_a_bearer_within_a_minute_of_expiry_is_replaced():
    fsmb = _Fsmb(_grant('first', expires_in=60), _grant('second'), accepted={'first', 'second'})
    client = _stubbed(fsmb)

    await client.get_member(_CLEARED)
    await client.get_member(_CLEARED)

    assert len(fsmb.grant_requests) == 2
    assert fsmb.requests[-1].headers['Authorization'] == 'Bearer second'


async def test_a_rejected_bearer_is_replaced_and_the_call_retried_once():
    fsmb = _Fsmb(_grant('revoked'), _grant('fresh'), accepted={'fresh'})

    member = await _stubbed(fsmb).get_member(_CLEARED)

    assert member is not None
    assert [r.url.path for r in fsmb.requests] == [
        '/connect/token',
        f'/v1/rosters/me/members/{_CLEARED}',
        '/connect/token',
        f'/v1/rosters/me/members/{_CLEARED}',
    ]


async def test_a_second_rejection_raises():
    fsmb = _Fsmb(_grant('revoked'), _grant('also-revoked'), accepted=set())

    with pytest.raises(FsmbError, match='401'):
        await _stubbed(fsmb).get_member(_CLEARED)


async def test_a_caller_whose_bearer_was_rejected_reuses_one_already_replaced():
    fsmb = _Fsmb(_grant('fresh'), accepted={'fresh'})
    client = _stubbed(fsmb)
    first = await client._current_bearer()

    assert await client._current_bearer(rejected='revoked') == first
    assert len(fsmb.grant_requests) == 1


async def test_the_customer_key_is_a_single_path_segment():
    fsmb = _Fsmb(_grant('first'), accepted={'first'})

    await _stubbed(fsmb, customer_key='a/b').get_member(_CLEARED)

    assert fsmb.requests[-1].url.raw_path == f'/v1/rosters/a%2Fb/members/{_CLEARED}'.encode()


async def test_a_connection_failure_raises_and_is_logged(caplog):
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError('refused', request=request)

    with pytest.raises(FsmbError, match='ConnectError'):
        await _stubbed(unreachable).get_member(_CLEARED)

    assert caplog.records[-1].__dict__['outcome'] == 'failed'


async def test_a_member_body_with_an_unknown_field_raises_without_its_values():
    def extra_field(request: httpx.Request) -> httpx.Response:
        if request.url.path == '/connect/token':
            return _grant('first')
        return httpx.Response(200, json={**_MEMBER, 'ssn': '123-45-6789'})

    with pytest.raises(FsmbError) as raised:
        await _stubbed(extra_field).get_member(_CLEARED)

    assert str(raised.value) == 'FSMB sent a FsmbMember the client rejects: ssn.'
    assert raised.value.__cause__ is None and raised.value.__suppress_context__


async def test_a_malformed_grant_raises():
    def no_bearer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps({'expires_in': 3600}))

    with pytest.raises(FsmbError, match='_Grant the client rejects: access_token'):
        await _stubbed(no_bearer).get_member(_CLEARED)
