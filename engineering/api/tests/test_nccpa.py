"""The NCCPA client: against nccpa-mock for NCCPA's answers, and a stub transport for the bearer's lifecycle."""

import json
import logging
from collections.abc import AsyncGenerator, Callable
from datetime import datetime

import httpx
import pytest

from licensing_api.config import Settings
from licensing_api.nccpa import (
    CertificationStatus,
    NccpaCertificationStatusResponse,
    NccpaClient,
    NccpaError,
    create_nccpa_client,
)
from tests.conftest import TEST_SETTINGS

_CERTIFIED = 1234560
_LAPSED = 1234569
_NO_DATES = 1000020
_REVOKED = 1000029
_MAINTENANCE = 1000033
_TOO_MANY = 1000044
_UNKNOWN = 1234567


@pytest.fixture
async def nccpa() -> AsyncGenerator[NccpaClient]:
    client = create_nccpa_client(TEST_SETTINGS)
    yield client
    await client.aclose()


async def _status(nccpa: NccpaClient, pa_id: int) -> NccpaCertificationStatusResponse:
    status = await nccpa.get_certification_status(pa_id)
    assert isinstance(status, NccpaCertificationStatusResponse)
    return status


async def test_a_pa_id_ending_0_is_certified(nccpa):
    status = await _status(nccpa, _CERTIFIED)

    assert status.pa_id == _CERTIFIED
    assert (status.first_name, status.last_name) == ('Casey', 'Certified')
    assert status.certification_status is CertificationStatus.CERTIFIED
    assert status.certification_date == datetime(2010, 6, 1)
    assert status.expiration_date == datetime(2028, 12, 31)


async def test_a_pa_id_ending_9_is_lapsed(nccpa):
    status = await _status(nccpa, _LAPSED)

    assert status.certification_status is CertificationStatus.NOT_CERTIFIED
    assert status.expiration_date == datetime(2024, 12, 31)


async def test_a_revoked_certification_is_its_own_status(nccpa):
    status = await _status(nccpa, _REVOKED)

    assert status.certification_status is CertificationStatus.REVOKED


async def test_a_certified_pa_may_have_no_dates(nccpa):
    status = await _status(nccpa, _NO_DATES)

    assert status.certification_status is CertificationStatus.CERTIFIED
    assert (status.certification_date, status.expiration_date) == (None, None)


async def test_a_pa_nccpa_does_not_know_is_none(nccpa):
    assert await nccpa.get_certification_status(_UNKNOWN) is None


@pytest.mark.parametrize(('pa_id', 'status_code'), [(_MAINTENANCE, 503), (_TOO_MANY, 429)])
async def test_maintenance_and_rate_limits_raise(nccpa, pa_id, status_code):
    with pytest.raises(NccpaError, match=str(status_code)):
        await nccpa.get_certification_status(pa_id)


@pytest.mark.parametrize('pa_id', [0, -1, 2**31])
async def test_a_pa_id_outside_int32_is_refused_before_calling(pa_id):
    def fail(request: httpx.Request) -> httpx.Response:
        raise AssertionError('NCCPA was called')

    with pytest.raises(ValueError, match='positive 32-bit integer'):
        await _stubbed(fail).get_certification_status(pa_id)


async def test_refused_credentials_raise():
    settings = Settings(nccpa_api_url=TEST_SETTINGS.nccpa_api_url, nccpa_client_id='someone-else')
    client = create_nccpa_client(settings)
    try:
        with pytest.raises(NccpaError, match='refused the client credentials'):
            await client.get_certification_status(_CERTIFIED)
    finally:
        await client.aclose()


async def test_calls_are_logged_without_the_pa(nccpa, caplog):
    caplog.set_level(logging.INFO, logger='licensing_api.nccpa')

    await nccpa.get_certification_status(_CERTIFIED)
    await nccpa.get_certification_status(_UNKNOWN)

    calls = [(r.__dict__['operation'], r.__dict__['outcome']) for r in caplog.records]
    assert calls == [
        ('grant', 'ok'),
        ('get_certification_status', 'ok'),
        ('get_certification_status', 'missing'),
    ]
    assert all(isinstance(r.__dict__['duration_ms'], int) for r in caplog.records)
    assert str(_CERTIFIED) not in caplog.text and 'Casey' not in caplog.text


# Stub transport: the bearer's lifecycle and malformed bodies, which nccpa-mock does not produce.

_STATUS = {
    'paId': _CERTIFIED,
    'firstName': 'Casey',
    'lastName': 'Certified',
    'certificationStatus': 'Certified',
    'expirationDate': '2028-12-31T00:00:00',
    'certificationDate': '2010-06-01T00:00:00',
}


def _grant(bearer: str, expires_in: int = 3599) -> httpx.Response:
    return httpx.Response(
        200, json={'access_token': bearer, 'token_type': 'bearer', 'expires_in': expires_in}
    )


class _Nccpa:
    """Issues bearers in turn, accepts only those in ``accepted``, and answers with ``status``."""

    def __init__(
        self, *grants: httpx.Response, accepted: set[str], status: dict | None = None
    ) -> None:
        self.grants = list(grants)
        self.accepted = accepted
        self.status = status or _STATUS
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == '/oauth/token':
            return self.grants.pop(0)
        if request.headers['Authorization'].removeprefix('Bearer ') in self.accepted:
            return httpx.Response(200, json=self.status)
        return httpx.Response(401)

    @property
    def grant_requests(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path == '/oauth/token']


def _stubbed(handler: Callable[[httpx.Request], httpx.Response]) -> NccpaClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url='https://nccpa.test')
    return NccpaClient(http, client_id='id', client_secret='secret')


async def test_the_grant_sends_the_client_credentials_in_the_form():
    nccpa = _Nccpa(_grant('first'), accepted={'first'})

    await _stubbed(nccpa).get_certification_status(_CERTIFIED)

    (grant,) = nccpa.grant_requests
    assert dict(httpx.QueryParams(grant.content.decode())) == {
        'grant_type': 'client_credentials',
        'client_id': 'id',
        'client_secret': 'secret',
    }
    assert 'Authorization' not in grant.headers


async def test_the_lookup_posts_the_pa_id_as_a_string_with_the_bearer():
    nccpa = _Nccpa(_grant('first'), accepted={'first'})

    await _stubbed(nccpa).get_certification_status(_CERTIFIED)

    lookup = nccpa.requests[-1]
    assert (lookup.method, lookup.url.path) == ('POST', '/CertificationStatus')
    assert lookup.headers['Content-Type'] == 'application/json'
    assert lookup.headers['Authorization'] == 'Bearer first'
    assert json.loads(lookup.content) == {'id': str(_CERTIFIED)}


async def test_a_grant_with_nccpas_issued_and_expires_fields_is_accepted():
    times = {
        '.issued': 'Wed, 21 Dec 2016 19:15:25 GMT',
        '.expires': 'Wed, 21 Dec 2016 20:15:25 GMT',
    }
    grant = httpx.Response(
        200, json={'access_token': 'first', 'token_type': 'bearer', 'expires_in': 3599, **times}
    )
    nccpa = _Nccpa(grant, accepted={'first'})

    assert isinstance(
        await _stubbed(nccpa).get_certification_status(_CERTIFIED), NccpaCertificationStatusResponse
    )


async def test_one_bearer_serves_calls_until_it_nears_expiry():
    nccpa = _Nccpa(_grant('first'), accepted={'first'})
    client = _stubbed(nccpa)

    await client.get_certification_status(_CERTIFIED)
    await client.get_certification_status(_CERTIFIED)

    assert len(nccpa.grant_requests) == 1


async def test_a_bearer_within_a_minute_of_expiry_is_replaced():
    nccpa = _Nccpa(_grant('first', expires_in=60), _grant('second'), accepted={'first', 'second'})
    client = _stubbed(nccpa)

    await client.get_certification_status(_CERTIFIED)
    await client.get_certification_status(_CERTIFIED)

    assert len(nccpa.grant_requests) == 2
    assert nccpa.requests[-1].headers['Authorization'] == 'Bearer second'


async def test_a_rejected_bearer_is_replaced_and_the_call_retried_once():
    nccpa = _Nccpa(_grant('revoked'), _grant('fresh'), accepted={'fresh'})

    status = await _stubbed(nccpa).get_certification_status(_CERTIFIED)

    assert isinstance(status, NccpaCertificationStatusResponse)
    assert [r.url.path for r in nccpa.requests] == [
        '/oauth/token',
        '/CertificationStatus',
        '/oauth/token',
        '/CertificationStatus',
    ]


async def test_a_second_rejection_raises():
    nccpa = _Nccpa(_grant('revoked'), _grant('also-revoked'), accepted=set())

    with pytest.raises(NccpaError, match='401'):
        await _stubbed(nccpa).get_certification_status(_CERTIFIED)


async def test_a_caller_whose_bearer_was_rejected_reuses_one_already_replaced():
    nccpa = _Nccpa(_grant('fresh'), accepted={'fresh'})
    client = _stubbed(nccpa)
    first = await client._current_bearer()

    assert await client._current_bearer(rejected='revoked') == first
    assert len(nccpa.grant_requests) == 1


async def test_null_where_the_document_allows_only_absence_is_rejected():
    nccpa = _Nccpa(_grant('first'), accepted={'first'}, status={**_STATUS, 'paId': None})

    with pytest.raises(NccpaError, match=r'rejects: paId \(value_error\)\.'):
        await _stubbed(nccpa).get_certification_status(_CERTIFIED)


async def test_a_status_the_document_does_not_list_is_rejected():
    status = {**_STATUS, 'certificationStatus': 'Certified - Pending'}
    nccpa = _Nccpa(_grant('first'), accepted={'first'}, status=status)

    with pytest.raises(NccpaError, match=r'certificationStatus \(enum\)'):
        await _stubbed(nccpa).get_certification_status(_CERTIFIED)


async def test_a_connection_failure_raises_and_is_logged(caplog):
    def unreachable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError('refused', request=request)

    with pytest.raises(NccpaError, match='ConnectError'):
        await _stubbed(unreachable).get_certification_status(_CERTIFIED)

    assert caplog.records[-1].__dict__['outcome'] == 'failed'


async def test_a_rejected_response_names_each_field_and_why_but_no_values(caplog):
    status = {**_STATUS, 'ssn': '123-45-6789', 'paId': 'not-a-number'}
    nccpa = _Nccpa(_grant('first'), accepted={'first'}, status=status)

    with pytest.raises(NccpaError) as raised:
        await _stubbed(nccpa).get_certification_status(_CERTIFIED)

    rejected = ['paId (int_parsing)', 'ssn (extra_forbidden)']
    model = 'NccpaCertificationStatusResponse'
    assert str(raised.value) == f'NCCPA sent a {model} the client rejects: {", ".join(rejected)}.'
    assert raised.value.__cause__ is None and raised.value.__suppress_context__
    (log,) = [r for r in caplog.records if r.getMessage() == 'NCCPA body rejected']
    assert (log.__dict__['model'], log.__dict__['rejected_fields']) == (model, rejected)
    assert '123-45-6789' not in caplog.text and 'Casey' not in caplog.text


async def test_a_malformed_grant_raises():
    def no_bearer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'expires_in': 3599})

    with pytest.raises(NccpaError, match='_Grant the client rejects: access_token'):
        await _stubbed(no_bearer).get_certification_status(_CERTIFIED)
