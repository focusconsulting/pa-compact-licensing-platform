"""The FSMB client: against fsmb-mock for FSMB's answers, and a stub transport for the bearer's lifecycle."""

import logging
from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime

import httpx
import pytest

from licensing_api.config import Settings
from licensing_api.fsmb import (
    REPORT_NOT_READY,
    BoardActionStatus,
    FsmbClient,
    FsmbError,
    FsmbReport,
    create_fsmb_client,
)
from tests.conftest import TEST_SETTINGS

_ALERTED = '999999915'
_CLEARED = '999999907'
_SPARSE = '999999923'
_NOT_READY = '999999931'
_UNAVAILABLE = '999999949'
_NOT_ON_ROSTER = '123456789'


@pytest.fixture
async def fsmb() -> AsyncGenerator[FsmbClient]:
    client = create_fsmb_client(TEST_SETTINGS)
    yield client
    await client.aclose()


async def _report(fsmb: FsmbClient, fid: str) -> FsmbReport:
    report = await fsmb.get_current_report(fid)
    assert isinstance(report, FsmbReport)
    return report


async def test_a_report_carries_identity_education_licenses_and_npi(fsmb):
    report = await _report(fsmb, _ALERTED)

    assert report.fid == _ALERTED
    assert report.as_of_date_time_utc == datetime(2023, 1, 18, 19, 13, 7, 30000, tzinfo=UTC)
    assert report.names.legal.last_name == 'Testermancho'
    assert [n.last_name for n in report.names.other or []] == ['Testman']
    assert report.birth_date is not None and report.birth_date.date == datetime(1978, 8, 8)
    education = report.medical_education
    assert education is not None and education.school is not None
    assert education.school.cibis_code == '049030'
    assert [(lic.issuer_name, lic.status, lic.expiration_date) for lic in report.licenses or []][
        :2
    ] == [('AL', 'Active', datetime(2030, 6, 30)), ('AK', 'Expired', datetime(2012, 6, 30))]
    assert [n.npi_number for n in report.npi or []] == ['1435537299']


async def test_an_alerted_report_carries_its_board_orders(fsmb):
    report = await _report(fsmb, _ALERTED)

    assert report.board_action_status is BoardActionStatus.ALERTED
    (order,) = report.board_orders or []
    assert order.issue_date == datetime(2019, 3, 14)
    assert order.disciplinary_entity.name == 'ARIZONA'
    (action,) = order.actions or []
    assert (action.action_code, action.is_prejudicial, action.term_years) == ('PROB', True, 2)
    assert action.expiration_date == datetime(2021, 3, 31)
    assert action.action_stayed is None


async def test_certifications_keep_partial_dates_in_part(fsmb):
    report = await _report(fsmb, _ALERTED)

    assert report.abms is not None
    general, _ = report.abms.certifications or []
    assert general.effective_date is not None
    assert general.effective_date.date == datetime(2008, 7, 1)
    assert general.expiration_date is not None
    assert (general.expiration_date.year, general.expiration_date.date) == ('2028', None)
    assert report.dea is not None
    assert [c.dea_number for c in report.dea.certifications or []] == ['AT1234563']


async def test_a_cleared_report_has_no_orders(fsmb):
    report = await _report(fsmb, _CLEARED)

    assert report.board_action_status is BoardActionStatus.CLEARED
    assert report.board_orders == []
    assert report.aoa is not None
    assert [c.certification_name for c in report.aoa.certifications or []] == [
        'Family Medicine/OMT'
    ]


async def test_a_report_with_only_what_fsmb_requires_is_accepted(fsmb):
    report = await _report(fsmb, _SPARSE)

    assert report.names.legal.last_name == 'Sparseley'
    assert report.birth_date is not None
    assert (report.birth_date.year, report.birth_date.date) == ('1990', None)
    assert (
        report.medical_education is None and report.licenses is None and report.board_orders is None
    )


async def test_a_member_without_a_report_yet_is_not_ready(fsmb):
    assert await fsmb.get_current_report(_NOT_READY) is REPORT_NOT_READY


async def test_an_fid_not_on_the_roster_is_none(fsmb):
    assert await fsmb.get_current_report(_NOT_ON_ROSTER) is None


@pytest.mark.parametrize('fid', ['12345678', '1234567890', 'abcdefghi', '12345678 '])
async def test_an_fid_that_is_not_nine_digits_is_refused_before_calling(fid):
    def fail(request: httpx.Request) -> httpx.Response:
        raise AssertionError('FSMB was called')

    with pytest.raises(ValueError, match='nine digits'):
        await _stubbed(fail).get_current_report(fid)


async def test_an_fsmb_error_raises(fsmb):
    with pytest.raises(FsmbError, match='503'):
        await fsmb.get_current_report(_UNAVAILABLE)


async def test_refused_credentials_raise():
    settings = Settings(fsmb_api_url=TEST_SETTINGS.fsmb_api_url, fsmb_client_id='someone-else')
    client = create_fsmb_client(settings)
    try:
        with pytest.raises(FsmbError, match='refused the client credentials'):
            await client.get_current_report(_ALERTED)
    finally:
        await client.aclose()


async def test_calls_are_logged_without_the_physician(fsmb, caplog):
    caplog.set_level(logging.INFO, logger='licensing_api.fsmb')

    await fsmb.get_current_report(_ALERTED)
    await fsmb.get_current_report(_NOT_READY)
    await fsmb.get_current_report(_NOT_ON_ROSTER)

    calls = [(r.__dict__['operation'], r.__dict__['outcome']) for r in caplog.records]
    assert calls == [
        ('grant', 'ok'),
        ('get_current_report', 'ok'),
        ('get_current_report', 'not_ready'),
        ('get_current_report', 'missing'),
    ]
    assert all(isinstance(r.__dict__['duration_ms'], int) for r in caplog.records)
    assert _ALERTED not in caplog.text and 'Testermancho' not in caplog.text


# Stub transport: the bearer's lifecycle and malformed bodies, which fsmb-mock does not produce.

_REPORT = {
    'fid': _ALERTED,
    'reportId': 1,
    'asOfDateTimeUtc': '2023-01-18T19:13:07',
    'boardActionStatus': 'Cleared',
    'names': {'legal': {'lastName': 'Testermancho', 'reportDate': '2022-07-25T00:00:00'}},
}


def _grant(bearer: str, expires_in: int = 3600) -> httpx.Response:
    body = {'expires_in': expires_in, 'token_type': 'Bearer', 'scope': 'pdc.member_read'}
    return httpx.Response(200, json={'access_token': bearer, **body})


class _Fsmb:
    """Issues bearers in turn, accepts only those in ``accepted``, and answers with ``report``."""

    def __init__(
        self, *grants: httpx.Response, accepted: set[str], report: dict | None = None
    ) -> None:
        self.grants = list(grants)
        self.accepted = accepted
        self.report = report or _REPORT
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == '/connect/token':
            return self.grants.pop(0)
        if request.headers['Authorization'].removeprefix('Bearer ') in self.accepted:
            return httpx.Response(200, json=self.report)
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

    await _stubbed(fsmb).get_current_report(_ALERTED)

    form = dict(httpx.QueryParams(fsmb.grant_requests[0].content.decode()))
    assert form == {
        'grant_type': 'client_credentials',
        'client_id': 'id',
        'client_secret': 'secret',
        'scope': 'pdc.member_read',
    }
    assert 'Authorization' not in fsmb.grant_requests[0].headers


async def test_one_bearer_serves_calls_until_it_nears_expiry():
    fsmb = _Fsmb(_grant('first'), accepted={'first'})
    client = _stubbed(fsmb)

    await client.get_current_report(_ALERTED)
    await client.get_current_report(_ALERTED)

    assert len(fsmb.grant_requests) == 1


async def test_a_bearer_within_a_minute_of_expiry_is_replaced():
    fsmb = _Fsmb(_grant('first', expires_in=60), _grant('second'), accepted={'first', 'second'})
    client = _stubbed(fsmb)

    await client.get_current_report(_ALERTED)
    await client.get_current_report(_ALERTED)

    assert len(fsmb.grant_requests) == 2
    assert fsmb.requests[-1].headers['Authorization'] == 'Bearer second'


async def test_a_rejected_bearer_is_replaced_and_the_call_retried_once():
    fsmb = _Fsmb(_grant('revoked'), _grant('fresh'), accepted={'fresh'})

    report = await _stubbed(fsmb).get_current_report(_ALERTED)

    assert isinstance(report, FsmbReport)
    report_path = f'/v1/rosters/me/members/{_ALERTED}/reports/current/data'
    assert [r.url.path for r in fsmb.requests] == [
        '/connect/token',
        report_path,
        '/connect/token',
        report_path,
    ]


async def test_a_second_rejection_raises():
    fsmb = _Fsmb(_grant('revoked'), _grant('also-revoked'), accepted=set())

    with pytest.raises(FsmbError, match='401'):
        await _stubbed(fsmb).get_current_report(_ALERTED)


async def test_a_caller_whose_bearer_was_rejected_reuses_one_already_replaced():
    fsmb = _Fsmb(_grant('fresh'), accepted={'fresh'})
    client = _stubbed(fsmb)
    first = await client._current_bearer()

    assert await client._current_bearer(rejected='revoked') == first
    assert len(fsmb.grant_requests) == 1


async def test_the_customer_key_is_a_single_path_segment():
    fsmb = _Fsmb(_grant('first'), accepted={'first'})

    await _stubbed(fsmb, customer_key='a/b').get_current_report(_ALERTED)

    expected = f'/v1/rosters/a%2Fb/members/{_ALERTED}/reports/current/data'
    assert fsmb.requests[-1].url.raw_path == expected.encode()


async def test_a_report_time_without_a_zone_is_utc():
    fsmb = _Fsmb(_grant('first'), accepted={'first'})

    report = await _stubbed(fsmb).get_current_report(_ALERTED)

    assert isinstance(report, FsmbReport)
    assert report.as_of_date_time_utc == datetime(2023, 1, 18, 19, 13, 7, tzinfo=UTC)


async def test_null_where_the_document_allows_only_absence_is_rejected():
    fsmb = _Fsmb(_grant('first'), accepted={'first'}, report={**_REPORT, 'medicalEducation': None})

    with pytest.raises(FsmbError, match='rejects: medicalEducation.'):
        await _stubbed(fsmb).get_current_report(_ALERTED)


async def test_a_string_over_its_documented_length_is_rejected():
    legal = {'lastName': 'x' * 51, 'reportDate': '2022-07-25T00:00:00'}
    fsmb = _Fsmb(_grant('first'), accepted={'first'}, report={**_REPORT, 'names': {'legal': legal}})

    with pytest.raises(FsmbError, match='names.legal.lastName'):
        await _stubbed(fsmb).get_current_report(_ALERTED)


async def test_a_connection_failure_raises_and_is_logged(caplog):
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError('refused', request=request)

    with pytest.raises(FsmbError, match='ConnectError'):
        await _stubbed(unreachable).get_current_report(_ALERTED)

    assert caplog.records[-1].__dict__['outcome'] == 'failed'


async def test_a_report_with_an_unknown_field_raises_without_its_values():
    fsmb = _Fsmb(_grant('first'), accepted={'first'}, report={**_REPORT, 'ssn': '123-45-6789'})

    with pytest.raises(FsmbError) as raised:
        await _stubbed(fsmb).get_current_report(_ALERTED)

    assert str(raised.value) == 'FSMB sent a FsmbReport the client rejects: ssn.'
    assert raised.value.__cause__ is None and raised.value.__suppress_context__


async def test_a_malformed_grant_raises():
    def no_bearer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'expires_in': 3600})

    with pytest.raises(FsmbError, match='_Grant the client rejects: access_token'):
        await _stubbed(no_bearer).get_current_report(_ALERTED)
