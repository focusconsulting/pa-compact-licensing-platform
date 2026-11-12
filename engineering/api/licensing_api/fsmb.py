"""FSMB's Physician Data Center (PDC) API: a roster member's board-action status by FID.

FSMB authenticates with OAuth2 client credentials (docs/fsmb.md). The bearer is cached per client,
fetched again a minute before FSMB says it expires, and fetched again once when FSMB answers 401
to it.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import date, datetime
from enum import StrEnum
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel

from licensing_api.config import Settings

logger = logging.getLogger(__name__)

SCOPE = 'pdc.member_read'
_FID = re.compile(r'\d{9}')
_EXPIRY_MARGIN_SECONDS = 60


class FsmbError(Exception):
    """FSMB failed, refused the credentials, or sent a body the client does not accept."""


class BoardActionStatus(StrEnum):
    """Whether FSMB holds board actions against the member; ``Unknown`` until a report succeeds."""

    UNKNOWN = 'Unknown'
    CLEARED = 'Cleared'
    ALERTED = 'Alerted'


class ReportStatus(StrEnum):
    """Where FSMB is in generating the member's PDC report."""

    PENDING = 'Pending'
    SUCCEEDED = 'Succeeded'
    FAILED = 'Failed'


class _FsmbBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra='forbid', frozen=True)


class FsmbReportSummary(_FsmbBody):
    """The member's current PDC report; FSMB sends no report date until the report is generated."""

    report_id: int
    report_date_utc: datetime | None = None
    report_generated_by: str | None = None
    report_status: ReportStatus
    is_complete: bool
    board_action_status: BoardActionStatus


class FsmbMember(_FsmbBody):
    """A member of the Commission's FSMB roster, as FSMB holds them."""

    fid: str = Field(pattern=r'^\d{9}$')
    full_name: str | None
    birth_date: date | None = None
    board_action_status: BoardActionStatus
    current_report: FsmbReportSummary | None = None


class _Grant(BaseModel):
    """FSMB's ``/connect/token`` response."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    bearer: str = Field(alias='access_token')
    expires_in: int
    token_type: str
    scope: str


class FsmbClient:
    """The connection pool and cached bearer for one process; share one instance."""

    def __init__(
        self, http: httpx.AsyncClient, *, client_id: str, client_secret: str, customer_key: str
    ) -> None:
        self._http = http
        self._credentials = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': SCOPE,
        }
        self._roster_path = f'/v1/rosters/{quote(customer_key, safe="")}/members'
        self._bearer_expires_at = 0.0
        self._bearer: str | None = None
        self._bearer_lock = asyncio.Lock()

    async def get_member(self, fid: str) -> FsmbMember | None:
        """The roster member with this FID, or ``None`` when the roster has no such member."""
        if not _FID.fullmatch(fid):
            raise ValueError('An FID is nine digits.')
        path = f'{self._roster_path}/{fid}'
        bearer = await self._current_bearer()
        response = await self._send('get_member', 'GET', path, headers=_authorization(bearer))
        if response.status_code == 401:
            bearer = await self._current_bearer(rejected=bearer)
            response = await self._send('get_member', 'GET', path, headers=_authorization(bearer))
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise FsmbError(f'FSMB answered {response.status_code} to a member lookup.')
        return _parse(FsmbMember, response)

    async def aclose(self) -> None:
        """Close the connection pool."""
        await self._http.aclose()

    async def _current_bearer(self, *, rejected: str | None = None) -> str:
        # The lock makes concurrent callers share one grant request; a caller whose bearer was
        # rejected gets the one another caller has already fetched in its place.
        async with self._bearer_lock:
            if (
                self._bearer is not None
                and self._bearer != rejected
                and time.monotonic() < self._bearer_expires_at
            ):
                return self._bearer
            response = await self._send('grant', 'POST', '/connect/token', data=self._credentials)
            if response.status_code != 200:
                raise FsmbError(f'FSMB refused the client credentials ({response.status_code}).')
            grant = _parse(_Grant, response)
            self._bearer_expires_at = time.monotonic() + grant.expires_in - _EXPIRY_MARGIN_SECONDS
            self._bearer = grant.bearer
            return self._bearer

    async def _send(self, operation: str, method: str, path: str, **kwargs) -> httpx.Response:
        log: dict[str, object] = {'operation': operation}
        started = time.monotonic()
        try:
            response = await self._http.request(method, path, **kwargs)
        except httpx.HTTPError as error:
            log['duration_ms'] = round((time.monotonic() - started) * 1000)
            logger.warning(
                'FSMB call failed',
                extra={**log, 'outcome': 'failed', 'error': type(error).__name__},
            )
            raise FsmbError(f'FSMB {operation} call failed: {type(error).__name__}.') from error
        log['duration_ms'] = round((time.monotonic() - started) * 1000)
        log['status_code'] = response.status_code
        if response.is_success:
            logger.info('FSMB call', extra={**log, 'outcome': 'ok'})
        elif response.status_code == 404:
            logger.info('FSMB call', extra={**log, 'outcome': 'missing'})
        else:
            logger.warning('FSMB call', extra={**log, 'outcome': 'failed'})
        return response


def _authorization(bearer: str) -> dict[str, str]:
    return {'Authorization': f'Bearer {bearer}'}


def _parse[M: BaseModel](model: type[M], response: httpx.Response) -> M:
    try:
        return model.model_validate_json(response.content)
    except ValidationError as error:
        # Name the fields, not their values, and drop the cause: a ValidationError carries the
        # input, which here is a practitioner's name and birth date or a bearer credential.
        fields = ', '.join('.'.join(str(part) for part in e['loc']) for e in error.errors())
        raise FsmbError(f'FSMB sent a {model.__name__} the client rejects: {fields}.') from None


def create_fsmb_client(settings: Settings) -> FsmbClient:
    """The FSMB client for these settings; a failed connection is retried twice, an answer never."""
    http = httpx.AsyncClient(
        base_url=settings.fsmb_api_url,
        headers={'Accept': 'application/json'},
        timeout=10,
        transport=httpx.AsyncHTTPTransport(retries=2),
    )
    return FsmbClient(
        http,
        client_id=settings.fsmb_client_id,
        client_secret=settings.fsmb_client_secret,
        customer_key=settings.fsmb_customer_key,
    )
