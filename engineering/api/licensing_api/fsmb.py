"""FSMB's Physician Data Center (PDC) API: a roster member's current PDC report, by FID.

FSMB authenticates with OAuth2 client credentials (docs/fsmb.md). The bearer is cached per client,
fetched again a minute before FSMB says it expires, and fetched again once when FSMB answers 401
to it. The report models follow FSMB's OpenAPI document, which tests/fsmb_openapi.json vendors and
tests/test_fsmb_openapi.py holds them to: its fields, required fields, nullability, and string
constraints, and no field it does not name.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import Annotated, Literal
from urllib.parse import quote

import httpx
from pydantic import (
    AfterValidator,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
)
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


def _reject_null(value: object) -> object:
    if value is None:
        raise ValueError('FSMB may leave this field out, but not send null')
    return value


def _as_utc(value: datetime) -> datetime:
    # The field is named ...Utc; FSMB's sample carries a Z, but a bare time means UTC too.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


# Optional and not nullable in FSMB's OpenAPI document: absent is None, an explicit null is refused.
_NOT_NULL = BeforeValidator(_reject_null)
FsmbInstant = Annotated[datetime, AfterValidator(_as_utc)]


class BoardActionStatus(StrEnum):
    """Whether FSMB holds board actions against the physician."""

    UNKNOWN = 'Unknown'
    CLEARED = 'Cleared'
    ALERTED = 'Alerted'


class _FsmbBody(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, extra='forbid', frozen=True)


class FsmbReportBoardOrderBasis(_FsmbBody):
    """Why a board issued an order."""

    code: Annotated[str, StringConstraints(min_length=1, max_length=5)] | None
    description: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None
    category_code: Annotated[str, StringConstraints(max_length=5)] | None = None


class FsmbReportBoardOrderActionStayed(_FsmbBody):
    """How an action was stayed."""

    code: Annotated[str, StringConstraints(min_length=1, max_length=5)] | None
    description: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None


class FsmbReportBoardOrderAction(_FsmbBody):
    """One action an order takes, such as probation, with its term."""

    action_code: Annotated[str, StringConstraints(min_length=1, max_length=5)] | None
    action_description: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None
    is_prejudicial: Annotated[bool | None, _NOT_NULL] = None
    is_indefinite: Annotated[bool | None, _NOT_NULL] = None
    effective_date: datetime | None = None
    expiration_date: datetime | None = None
    term_years: int | None = None
    term_months: int | None = None
    term_days: int | None = None
    action_stayed: Annotated[FsmbReportBoardOrderActionStayed | None, _NOT_NULL] = None
    comments: Annotated[str, StringConstraints(max_length=1000)] | None = None


class FsmbReportBoardOrderActionForm(_FsmbBody):
    """The form of an order's action, such as a consent order."""

    code: Annotated[str, StringConstraints(min_length=1, max_length=5)] | None
    description: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None


class FsmbReportBoardOrderEntity(_FsmbBody):
    """The board that issued an order."""

    code: Annotated[str, StringConstraints(min_length=1, max_length=3)] | None
    name: Annotated[str, StringConstraints(min_length=1, max_length=25)] | None
    description: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None


class FsmbReportBoardOrder(_FsmbBody):
    """A disciplinary order a board issued against the physician."""

    order_id: Annotated[int | None, _NOT_NULL] = None
    usmle_id: str | None = None
    issue_date: Annotated[datetime | None, _NOT_NULL] = None
    effective_date: datetime | None = None
    appeal_date: datetime | None = None
    disciplinary_entity: FsmbReportBoardOrderEntity
    action_form: Annotated[FsmbReportBoardOrderActionForm | None, _NOT_NULL] = None
    actions: list[FsmbReportBoardOrderAction] | None
    bases: list[FsmbReportBoardOrderBasis] | None = None


class FsmbReportDeaCertification(_FsmbBody):
    """One DEA registration; ``drug_schedules`` is space-separated."""

    report_date: Annotated[datetime | None, _NOT_NULL] = None
    dea_number: Annotated[str, StringConstraints(min_length=1, max_length=9)] | None
    expiration_date: datetime | None = None
    drug_schedules: Annotated[str, StringConstraints(max_length=20)] | None = None
    city: Annotated[str, StringConstraints(max_length=50)] | None = None
    state: Annotated[str, StringConstraints(max_length=2)] | None = None
    zip_code: Annotated[str, StringConstraints(max_length=9)] | None = None


class FsmbReportDea(_FsmbBody):
    """DEA controlled-substance registrations."""

    certifications: list[FsmbReportDeaCertification] | None = None


class FsmbReportAoaCertification(_FsmbBody):
    """One AOA certification."""

    aoa_id: Annotated[str, StringConstraints(min_length=1, max_length=6)] | None
    report_date: Annotated[datetime | None, _NOT_NULL] = None
    board_name: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None
    certification_name: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None
    certification_status: Annotated[str, StringConstraints(max_length=20)] | None = None
    certification_type: Annotated[str, StringConstraints(min_length=1, max_length=50)] | None
    is_occ_participating: Annotated[bool | None, _NOT_NULL] = None
    is_occ_required: Annotated[bool | None, _NOT_NULL] = None
    certification_issue_date: datetime | None = None
    certification_end_date: datetime | None = None
    recertification_issue_date: datetime | None = None
    recertification_expire_date: datetime | None = None


class FsmbReportAoa(_FsmbBody):
    """American Osteopathic Association certifications."""

    certifications: list[FsmbReportAoaCertification] | None = None


class FsmbPartialDate(_FsmbBody):
    """A date FSMB may hold only in part; ``date`` is set only when every part is known."""

    month: Annotated[str, StringConstraints(pattern=r'\d{2}')] | None = None
    day: Annotated[str, StringConstraints(pattern=r'\d{2}')] | None = None
    year: Annotated[str, StringConstraints(pattern=r'\d{4}')] | None = None
    date: datetime | None = None


class FsmbReportAbmsCertification(_FsmbBody):
    """One ABMS certification."""

    report_date: Annotated[datetime | None, _NOT_NULL] = None
    board_name: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None
    certificate_name: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None
    meets_moc_requirements: Annotated[str, StringConstraints(min_length=1, max_length=20)] | None
    is_certified: Annotated[bool | None, _NOT_NULL] = None
    certificate_status: Annotated[str, StringConstraints(max_length=100)] | None = None
    certificate_type: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None
    certificate_duration: Annotated[str, StringConstraints(min_length=1, max_length=20)] | None
    occurrence_type: Annotated[str, StringConstraints(min_length=1, max_length=20)] | None
    effective_date: FsmbPartialDate | None = None
    expiration_date: FsmbPartialDate | None = None
    reverification_date: datetime | None = None
    moc_pathway_id: Annotated[str, StringConstraints(max_length=2)] | None = None
    moc_pathway_name: Annotated[str, StringConstraints(max_length=100)] | None = None
    occupation_status: Annotated[str, StringConstraints(max_length=2)] | None = None
    occupation_status_notify_year: Annotated[str, StringConstraints(pattern=r'\d{4}')] | None = None


class FsmbReportAbms(_FsmbBody):
    """American Board of Medical Specialties certifications."""

    certifications: list[FsmbReportAbmsCertification] | None = None


class FsmbReportNpi(_FsmbBody):
    """A National Provider Identifier."""

    npi_number: Annotated[str, StringConstraints(min_length=1, max_length=10)] | None
    entity_type: Annotated[str, StringConstraints(min_length=1, max_length=20)] | None
    report_date: Annotated[datetime | None, _NOT_NULL] = None


class FsmbReportLicense(_FsmbBody):
    """A license a board reported."""

    report_date: Annotated[datetime | None, _NOT_NULL] = None
    license_type: Annotated[str, StringConstraints(max_length=100)] | None = None
    issuer_name: Annotated[str, StringConstraints(min_length=1, max_length=5)] | None
    issuer_description: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None
    status: Annotated[str, StringConstraints(max_length=100)] | None = None
    license_number: Annotated[str, StringConstraints(max_length=20)] | None = None
    issue_date: datetime | None = None
    expiration_date: datetime | None = None


class FsmbReportMedicalDegree(_FsmbBody):
    """The degree, such as ``MD`` or ``DO``."""

    code: Annotated[str, StringConstraints(min_length=1, max_length=5)] | None
    description: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None
    is_verified: Annotated[bool | None, _NOT_NULL] = None
    report_date: Annotated[datetime | None, _NOT_NULL] = None


class FsmbReportGraduationDate(_FsmbBody):
    """The graduation year."""

    year: Annotated[str, StringConstraints(min_length=1)] | None
    is_verified: Annotated[bool | None, _NOT_NULL] = None
    report_date: Annotated[datetime | None, _NOT_NULL] = None


class FsmbReportMedicalSchool(_FsmbBody):
    """The medical school, identified by its CIBIS code."""

    name: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None
    alternate_names: Annotated[list[str], Field(max_length=100)] | None = None
    cibis_code: Annotated[str, StringConstraints(min_length=1, max_length=6)] | None
    school_type_code: Annotated[str, StringConstraints(min_length=1, max_length=5)] | None
    school_type_description: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None
    city: Annotated[str, StringConstraints(max_length=50)] | None = None
    state_code: Annotated[str, StringConstraints(max_length=3)] | None = None
    state_description: Annotated[str, StringConstraints(max_length=100)] | None = None
    country_code: Annotated[str, StringConstraints(max_length=2)] | None = None
    country_description: Annotated[str, StringConstraints(max_length=100)] | None = None
    is_verified: Annotated[bool | None, _NOT_NULL] = None
    report_date: Annotated[datetime | None, _NOT_NULL] = None


class FsmbReportMedicalEducation(_FsmbBody):
    """Medical school, graduation, and degree."""

    school: Annotated[FsmbReportMedicalSchool | None, _NOT_NULL] = None
    graduation_date: Annotated[FsmbReportGraduationDate | None, _NOT_NULL] = None
    degree: Annotated[FsmbReportMedicalDegree | None, _NOT_NULL] = None


class FsmbReportBirthDate(_FsmbBody):
    """The birth date, possibly in part; ``date`` is set only when every part is known."""

    month: Annotated[str, StringConstraints(pattern=r'\d{2}')] | None = None
    day: Annotated[str, StringConstraints(pattern=r'\d{2}')] | None = None
    year: Annotated[str, StringConstraints(pattern=r'\d{4}')] | None = None
    date: datetime | None = None
    report_date: Annotated[datetime | None, _NOT_NULL] = None


class FsmbReportName(_FsmbBody):
    """A name, and when FSMB received it."""

    first_name: Annotated[str, StringConstraints(max_length=50)] | None = None
    middle_name: Annotated[str, StringConstraints(max_length=50)] | None = None
    last_name: Annotated[str, StringConstraints(min_length=1, max_length=50)] | None
    suffix: Annotated[str, StringConstraints(max_length=4)] | None = None
    report_date: Annotated[datetime | None, _NOT_NULL] = None


class FsmbReportNames(_FsmbBody):
    """The legal name and any other names."""

    legal: FsmbReportName
    other: list[FsmbReportName] | None = None


class FsmbReport(_FsmbBody):
    """A physician's current PDC report: identity, education, licenses, certifications, and board orders."""

    fid: Annotated[str, StringConstraints(min_length=1)] | None
    report_id: Annotated[int | None, _NOT_NULL] = None
    as_of_date_time_utc: Annotated[FsmbInstant | None, _NOT_NULL] = None
    generated_by_user: str | None = None
    board_action_status: Annotated[BoardActionStatus | None, _NOT_NULL] = None
    names: FsmbReportNames
    birth_date: Annotated[FsmbReportBirthDate | None, _NOT_NULL] = None
    medical_education: Annotated[FsmbReportMedicalEducation | None, _NOT_NULL] = None
    licenses: list[FsmbReportLicense] | None = None
    npi: list[FsmbReportNpi] | None = None
    abms: Annotated[FsmbReportAbms | None, _NOT_NULL] = None
    aoa: Annotated[FsmbReportAoa | None, _NOT_NULL] = None
    dea: Annotated[FsmbReportDea | None, _NOT_NULL] = None
    board_orders: list[FsmbReportBoardOrder] | None = None


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
        # Name each field and why, never its value, and drop the cause: a ValidationError carries
        # the input, which here is a physician's identity and disciplinary record or a bearer.
        # Where real reports differ from FSMB's document, these lines say how (docs/fsmb.md).
        rejected = [
            f'{".".join(str(part) for part in e["loc"])} ({e["type"]})' for e in error.errors()
        ]
        logger.warning(
            'FSMB body rejected', extra={'model': model.__name__, 'rejected_fields': rejected}
        )
        raise FsmbError(
            f'FSMB sent a {model.__name__} the client rejects: {", ".join(rejected)}.'
        ) from None


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
