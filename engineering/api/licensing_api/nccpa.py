"""NCCPA's Board Certification Status API: a PA's current certification, by NCCPA PA ID.

NCCPA authenticates with OAuth2 client credentials (docs/nccpa.md). The bearer is cached per
client in memory only, fetched again a minute before NCCPA says it expires, and fetched again once
when NCCPA answers 401 to it. The response model follows NCCPA's OpenAPI document, which
tests/nccpa_openapi.json vendors and tests/test_nccpa_openapi.py holds it to.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from enum import StrEnum
from typing import Annotated

import httpx
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel

from licensing_api.config import Settings

logger = logging.getLogger(__name__)

TOKEN_PATH = '/oauth/token'
STATUS_PATH = '/CertificationStatus'
_INT32_MAX = 2**31 - 1
_INT32_MIN = -(2**31)
_EXPIRY_MARGIN_SECONDS = 60


class NccpaError(Exception):
    """NCCPA failed, refused the credentials, or sent a body the client does not accept."""


def _reject_null(value: object) -> object:
    if value is None:
        raise ValueError('NCCPA may leave this field out, but not send null')
    return value


# Optional and not nullable in NCCPA's OpenAPI document: absent is None, an explicit null is refused.
_NOT_NULL = BeforeValidator(_reject_null)
Int32 = Annotated[int, Field(ge=_INT32_MIN, le=_INT32_MAX)]


class CertificationStatus(StrEnum):
    """The values the document's 200 description lists; its schema says only ``string``."""

    CERTIFIED = 'Certified'
    NOT_CERTIFIED = 'Not Certified'
    REVOKED = 'Not Certified - Revoked'


class NccpaCertificationStatusResponse(BaseModel):
    """A PA's current board certification; NCCPA leaves both dates out for certain PAs."""

    model_config = ConfigDict(alias_generator=to_camel, extra='forbid', frozen=True)

    pa_id: Annotated[Int32 | None, _NOT_NULL] = None
    first_name: str | None = None
    last_name: str | None = None
    certification_status: CertificationStatus | None = None
    expiration_date: datetime | None = None
    certification_date: datetime | None = None


class _Grant(BaseModel):
    """NCCPA's ``/oauth/token`` response."""

    model_config = ConfigDict(extra='forbid', frozen=True)

    bearer: str = Field(alias='access_token')
    expires_in: int
    token_type: str
    issued: str | None = Field(default=None, alias='.issued')
    expires: str | None = Field(default=None, alias='.expires')


class NccpaClient:
    """The connection pool and cached bearer for one process; share one instance."""

    def __init__(self, http: httpx.AsyncClient, *, client_id: str, client_secret: str) -> None:
        self._http = http
        self._credentials = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
        }
        self._bearer_expires_at = 0.0
        self._bearer: str | None = None
        self._bearer_lock = asyncio.Lock()

    async def get_certification_status(self, pa_id: int) -> NccpaCertificationStatusResponse | None:
        """The PA's current certification, or ``None`` when NCCPA has no such PA (404)."""
        # The document's `id` also takes an SSN; the client sends only the PA ID, never an SSN.
        if not 0 < pa_id <= _INT32_MAX:
            raise ValueError('An NCCPA PA ID is a positive 32-bit integer.')
        body = {'id': str(pa_id)}
        bearer = await self._current_bearer()
        response = await self._send(
            'get_certification_status', STATUS_PATH, bearer=bearer, json=body
        )
        if response.status_code == 401:
            bearer = await self._current_bearer(rejected=bearer)
            response = await self._send(
                'get_certification_status', STATUS_PATH, bearer=bearer, json=body
            )
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise NccpaError(f'NCCPA answered {response.status_code} to a certification request.')
        return _parse(NccpaCertificationStatusResponse, response)

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
            response = await self._send('grant', TOKEN_PATH, data=self._credentials)
            if response.status_code != 200:
                raise NccpaError(f'NCCPA refused the client credentials ({response.status_code}).')
            grant = _parse(_Grant, response)
            self._bearer_expires_at = time.monotonic() + grant.expires_in - _EXPIRY_MARGIN_SECONDS
            self._bearer = grant.bearer
            return self._bearer

    async def _send(
        self,
        operation: str,
        path: str,
        *,
        bearer: str | None = None,
        data: dict[str, str] | None = None,
        json: dict[str, str] | None = None,
    ) -> httpx.Response:
        headers = {'Authorization': f'Bearer {bearer}'} if bearer else None
        log: dict[str, object] = {'operation': operation}
        started = time.monotonic()
        try:
            response = await self._http.post(path, headers=headers, data=data, json=json)
        except httpx.HTTPError as error:
            log['duration_ms'] = round((time.monotonic() - started) * 1000)
            logger.warning(
                'NCCPA call failed',
                extra={**log, 'outcome': 'failed', 'error': type(error).__name__},
            )
            raise NccpaError(f'NCCPA {operation} call failed: {type(error).__name__}.') from error
        log['duration_ms'] = round((time.monotonic() - started) * 1000)
        log['status_code'] = response.status_code
        if response.is_success:
            logger.info('NCCPA call', extra={**log, 'outcome': 'ok'})
        elif response.status_code == 404:
            logger.info('NCCPA call', extra={**log, 'outcome': 'missing'})
        else:
            logger.warning('NCCPA call', extra={**log, 'outcome': 'failed'})
        return response


def _parse[M: BaseModel](model: type[M], response: httpx.Response) -> M:
    try:
        return model.model_validate_json(response.content)
    except ValidationError as error:
        # Name each field and why, never its value, and drop the cause: a ValidationError carries
        # the input, which here is a PA's name and certification or a bearer.
        rejected = [
            f'{".".join(str(part) for part in e["loc"])} ({e["type"]})' for e in error.errors()
        ]
        logger.warning(
            'NCCPA body rejected', extra={'model': model.__name__, 'rejected_fields': rejected}
        )
        raise NccpaError(
            f'NCCPA sent a {model.__name__} the client rejects: {", ".join(rejected)}.'
        ) from None


def create_nccpa_client(settings: Settings) -> NccpaClient:
    """The NCCPA client for these settings; a failed connection is retried twice, an answer never."""
    http = httpx.AsyncClient(
        base_url=settings.nccpa_api_url,
        headers={'Accept': 'application/json'},
        timeout=10,
        transport=httpx.AsyncHTTPTransport(retries=2),
    )
    return NccpaClient(
        http, client_id=settings.nccpa_client_id, client_secret=settings.nccpa_client_secret
    )
