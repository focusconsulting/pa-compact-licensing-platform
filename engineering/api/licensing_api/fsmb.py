"""FSMB's Physician Data Center (PDC) API: a roster member's current PDC report, by FID.

FSMB authenticates with OAuth2 client credentials (docs/fsmb.md). The bearer is cached per client,
fetched again a minute before FSMB says it expires, and fetched again once when FSMB answers 401
to it. The report models follow FSMB's PDC report definitions
(https://github.com/fsmb/pdc-api/tree/main/docs/definitions) and reject fields they don't name.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import UTC, date, datetime
from enum import Enum, StrEnum
from typing import Annotated, Literal
from urllib.parse import quote

import httpx
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel

from licensing_api.config import Settings

logger = logging.getLogger(__name__)

SCOPE = 'pdc.member_read'
_FID = re.compile(r'\d{9}')
_EXPIRY_MARGIN_SECONDS = 60


class FsmbError(Exception):
    """FSMB failed, refused the credentials, or sent a body the client does not accept."""


class ReportNotReady(Enum):
    """FSMB has the member but no current report to give yet (``204``); ask again later."""

    REPORT_NOT_READY = 'report_not_ready'


REPORT_NOT_READY = ReportNotReady.REPORT_NOT_READY


def _calendar_date(value: object) -> object:
    # FSMB sends calendar dates as midnight date-times ("2010-07-01T00:00:00"). They are dates
    # (Principle XIII), so the time is dropped, and only when it is midnight.
    if isinstance(value, str) and 'T' in value:
        moment = datetime.fromisoformat(value)
        if moment.time() != datetime.min.time():
            raise ValueError('expected a calendar date, got a time of day')
        return moment.date()
    return value


def _as_utc(value: datetime) -> datetime:
    # The field is named ...Utc; FSMB's sample carries a Z, but a bare time means UTC too.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


FsmbDate = Annotated[date, BeforeValidator(_calendar_date)]
FsmbInstant = Annotated[datetime, AfterValidator(_as_utc)]
TwoDigits = Annotated[str, Field(pattern=r'^\d{2}$')]
Year = Annotated[str, Field(pattern=r'^\d{4}$')]


class BoardActionStatus(StrEnum):
    """Whether FSMB holds board actions against the physician."""

    UNKNOWN = 'Unknown'
    CLEARED = 'Cleared'
    ALERTED = 'Alerted'


class _FsmbBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra='forbid', frozen=True)


class FsmbName(_FsmbBody):
    """A name FSMB holds, and the date it was reported."""

    first_name: str | None = None
    middle_name: str | None = None
    last_name: str | None
    suffix: str | None = None
    report_date: FsmbDate


class FsmbNames(_FsmbBody):
    """The legal name and any other names."""

    legal: FsmbName
    other: list[FsmbName] | None = None


class FsmbPartialDate(_FsmbBody):
    """A date FSMB may hold only in part; ``full_date`` is set when every part is known."""

    month: TwoDigits | None = None
    day: TwoDigits | None = None
    year: Year | None = None
    full_date: FsmbDate | None = Field(default=None, alias='date')


class FsmbBirthDate(FsmbPartialDate):
    """The birth date, possibly in part, and the date it was reported."""

    report_date: FsmbDate


class FsmbMedicalSchool(_FsmbBody):
    """The medical school, with its CIBIS code."""

    name: str | None
    alternate_names: list[str] | None = None
    cibis_code: str | None
    school_type_code: str | None
    school_type_description: str | None
    city: str | None = None
    state_code: str | None = None
    state_description: str | None = None
    country_code: str | None = None
    country_description: str | None = None
    is_verified: bool
    report_date: FsmbDate


class FsmbGraduationDate(_FsmbBody):
    """The graduation year."""

    year: Year | None
    is_verified: bool
    report_date: FsmbDate


class FsmbMedicalDegree(_FsmbBody):
    """The degree, such as ``MD`` or ``DO``."""

    code: str | None
    description: str | None
    is_verified: bool
    report_date: FsmbDate


class FsmbMedicalEducation(_FsmbBody):
    """School, graduation, and degree; each may be missing."""

    school: FsmbMedicalSchool | None = None
    graduation_date: FsmbGraduationDate | None = None
    degree: FsmbMedicalDegree | None = None


class FsmbLicense(_FsmbBody):
    """A license a board reported; ``issuer_name`` is the board's state name."""

    report_date: FsmbDate
    license_type: str | None = None
    issuer_name: str | None
    issuer_description: str | None
    status: str | None = None
    license_number: str | None = None
    issue_date: FsmbDate | None = None
    expiration_date: FsmbDate | None = None


class FsmbNpi(_FsmbBody):
    """A National Provider Identifier."""

    npi_number: str | None
    entity_type: str | None
    report_date: FsmbDate


class FsmbAbmsCertification(_FsmbBody):
    """An American Board of Medical Specialties certification."""

    report_date: FsmbDate
    board_name: str | None
    certificate_name: str | None
    meets_moc_requirements: str | None
    is_certified: bool
    certificate_status: str | None = None
    certificate_type: str | None
    certificate_duration: str | None
    occurrence_type: str | None
    effective_date: FsmbPartialDate | None = None
    expiration_date: FsmbPartialDate | None = None
    reverification_date: FsmbDate | None = None
    moc_pathway_id: str | None = None
    moc_pathway_name: str | None = None
    occupation_status: str | None = None
    occupation_status_notify_year: Year | None = None


class FsmbAbms(_FsmbBody):
    """ABMS certifications."""

    certifications: list[FsmbAbmsCertification] | None = None


class FsmbAoaCertification(_FsmbBody):
    """An American Osteopathic Association certification."""

    aoa_id: str | None
    report_date: FsmbDate
    board_name: str | None
    certification_name: str | None
    certification_status: str | None = None
    certification_type: str | None
    is_occ_participating: bool
    is_occ_required: bool
    certification_issue_date: FsmbDate | None = None
    certification_end_date: FsmbDate | None = None
    recertification_issue_date: FsmbDate | None = None
    recertification_expire_date: FsmbDate | None = None


class FsmbAoa(_FsmbBody):
    """AOA certifications."""

    certifications: list[FsmbAoaCertification] | None = None


class FsmbDeaCertification(_FsmbBody):
    """A DEA controlled-substance registration."""

    report_date: FsmbDate
    dea_number: str | None
    expiration_date: FsmbDate | None = None
    drug_schedules: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None


class FsmbDea(_FsmbBody):
    """DEA registrations."""

    certifications: list[FsmbDeaCertification] | None = None


class FsmbCode(_FsmbBody):
    """A coded value: a board order's action form, or a stayed action."""

    code: str | None
    description: str | None


class FsmbBoardOrderBasis(FsmbCode):
    """Why a board issued an order."""

    category_code: str | None = None


class FsmbBoardOrderEntity(_FsmbBody):
    """The board that issued an order."""

    code: str | None
    name: str | None
    description: str | None


class FsmbBoardOrderAction(_FsmbBody):
    """One action an order takes, such as a suspension, with its term."""

    action_code: str | None
    action_description: str | None
    is_prejudicial: bool
    is_indefinite: bool
    effective_date: FsmbDate | None = None
    expiration_date: FsmbDate | None = None
    term_years: int | None = None
    term_months: int | None = None
    term_days: int | None = None
    action_stayed: FsmbCode | None = None
    comments: str | None = None


class FsmbBoardOrder(_FsmbBody):
    """A disciplinary order a board issued against the physician."""

    order_id: int
    usmle_id: str | None = None
    issue_date: FsmbDate
    effective_date: FsmbDate | None = None
    appeal_date: FsmbDate | None = None
    disciplinary_entity: FsmbBoardOrderEntity
    action_form: FsmbCode | None = None
    actions: list[FsmbBoardOrderAction] | None
    bases: list[FsmbBoardOrderBasis] | None = None


class FsmbReport(_FsmbBody):
    """A physician's current PDC report: identity, education, licenses, certifications, and orders."""

    fid: Annotated[str, Field(pattern=r'^\d{9}$')]
    report_id: int
    as_of_date_time_utc: FsmbInstant
    generated_by_user: str | None = None
    board_action_status: BoardActionStatus
    names: FsmbNames
    birth_date: FsmbBirthDate | None = None
    medical_education: FsmbMedicalEducation | None = None
    licenses: list[FsmbLicense] | None = None
    npi: list[FsmbNpi] | None = None
    abms: FsmbAbms | None = None
    aoa: FsmbAoa | None = None
    dea: FsmbDea | None = None
    board_orders: list[FsmbBoardOrder] | None = None


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

    async def get_current_report(
        self, fid: str
    ) -> FsmbReport | Literal[ReportNotReady.REPORT_NOT_READY] | None:
        """The member's current report; ``REPORT_NOT_READY`` while FSMB has none to give (204), or
        ``None`` when the roster has no such member or the member has no report (404)."""
        if not _FID.fullmatch(fid):
            raise ValueError('An FID is nine digits.')
        path = f'{self._roster_path}/{fid}/reports/current/data'
        bearer = await self._current_bearer()
        response = await self._send('get_current_report', 'GET', path, bearer=bearer)
        if response.status_code == 401:
            bearer = await self._current_bearer(rejected=bearer)
            response = await self._send('get_current_report', 'GET', path, bearer=bearer)
        if response.status_code == 204:
            return REPORT_NOT_READY
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise FsmbError(f'FSMB answered {response.status_code} to a report request.')
        return _parse(FsmbReport, response)

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

    async def _send(
        self,
        operation: str,
        method: str,
        path: str,
        *,
        bearer: str | None = None,
        data: dict[str, str] | None = None,
    ) -> httpx.Response:
        headers = {'Authorization': f'Bearer {bearer}'} if bearer else None
        log: dict[str, object] = {'operation': operation}
        started = time.monotonic()
        try:
            response = await self._http.request(method, path, headers=headers, data=data)
        except httpx.HTTPError as error:
            log['duration_ms'] = round((time.monotonic() - started) * 1000)
            logger.warning(
                'FSMB call failed',
                extra={**log, 'outcome': 'failed', 'error': type(error).__name__},
            )
            raise FsmbError(f'FSMB {operation} call failed: {type(error).__name__}.') from error
        log['duration_ms'] = round((time.monotonic() - started) * 1000)
        log['status_code'] = response.status_code
        if response.status_code == 204:
            logger.info('FSMB call', extra={**log, 'outcome': 'not_ready'})
        elif response.is_success:
            logger.info('FSMB call', extra={**log, 'outcome': 'ok'})
        elif response.status_code == 404:
            logger.info('FSMB call', extra={**log, 'outcome': 'missing'})
        else:
            logger.warning('FSMB call', extra={**log, 'outcome': 'failed'})
        return response


def _parse[M: BaseModel](model: type[M], response: httpx.Response) -> M:
    try:
        return model.model_validate_json(response.content)
    except ValidationError as error:
        # Name the fields, not their values, and drop the cause: a ValidationError carries the
        # input, which here is a physician's identity and disciplinary record or a bearer.
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
