"""A PA's participation applications: the wizard's draft, attestations, submit, and withdraw (FLOW-01 Phase 1).

A draft is the PA's working copy. History starts when the SQL receives the application:
submit and resubmit each record the whole application as sent (platform contract).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.context import ChangeContext, change_context
from licensing_api.days import reference_time_zone
from licensing_api.dependencies import get_db_session
from licensing_api.errors import AppError, ErrorCode
from licensing_api.information_request import requested_at, resubmit_by
from licensing_api.permissions import Permission, require
from licensing_api.repo.application_transition import InvalidTransitionError, move
from licensing_api.repo.attestation import (
    Attestation,
    AttestationAppliesTo,
    ParticipationApplicationAttestation,
    accept,
    out_of_date_codes,
)
from licensing_api.repo.base import utc_now
from licensing_api.repo.document import Document, DocumentOwnerType
from licensing_api.repo.document_owner import attach
from licensing_api.repo.domain_event import EventType
from licensing_api.repo.participation_application import (
    OPEN_APPLICATION_STATUSES,
    ApplicationKind,
    ApplicationStatus,
    ParticipationApplication,
)
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.state import State
from licensing_api.repo.user import User
from licensing_api.responses import Data, example
from licensing_api.routes.document import DocumentOut

me = APIRouter(prefix='/applications')

ApplicationId = Annotated[UUID, Path(description="The application's ID")]
StateCode = Annotated[str, Field(pattern=r'^[A-Z]{2}$', description='Two-letter state code')]

# The PA changes their answers only while the SQL is not looking at them.
_EDITABLE = frozenset({ApplicationStatus.DRAFT, ApplicationStatus.INFO_REQUESTED})

_EXAMPLE_ID = UUID('3d7e2a91-6b0c-4f58-a2e4-9c1b8f0d5e36')
_EXAMPLE_AT = datetime.fromisoformat('2026-11-12T15:04:05Z')


class AcceptedAttestation(BaseModel):
    """The version of an attestation the PA last accepted on this application."""

    model_config = ConfigDict(
        json_schema_extra=example(code='nccpa_current', version=1, accepted_at=_EXAMPLE_AT)
    )

    code: str
    version: int
    accepted_at: datetime


class ApplicationOut(BaseModel):
    """A participation application as its PA sees it.

    ``request_note`` is the SQL's latest request for information, and ``response_note`` the PA's reply.
    While the application waits on information, ``requested_at`` says when the SQL asked and
    ``resubmit_by`` the last day it must have the answer (Rule 3 §3.7(a)(1)).
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra=example(
            id=_EXAMPLE_ID,
            kind=ApplicationKind.INITIAL,
            status=ApplicationStatus.DRAFT,
            sql_state_code='KS',
            claimed_license_number='PA-12345',
            claimed_license_expires_on=date(2027, 12, 31),
            opened_at=None,
            request_note=None,
            response_note=None,
            requested_at=None,
            resubmit_by=None,
            withdrawn_at=None,
            sworn_at=None,
            attestations=[],
            documents=[],
        ),
    )

    id: UUID = Field(validation_alias='public_id')
    kind: ApplicationKind
    status: ApplicationStatus
    sql_state_code: str
    claimed_license_number: str | None
    claimed_license_expires_on: date | None
    opened_at: datetime | None
    request_note: str | None
    response_note: str | None
    requested_at: datetime | None
    resubmit_by: date | None
    withdrawn_at: datetime | None
    sworn_at: datetime | None
    attestations: list[AcceptedAttestation]
    documents: list[DocumentOut]


class ApplicationCreate(BaseModel):
    """The state the PA designates as their state of qualifying license (Rule 3 §3.4(a)(2))."""

    model_config = ConfigDict(extra='forbid', json_schema_extra=example(sql_state_code='KS'))

    sql_state_code: StateCode


class ApplicationUpdate(BaseModel):
    """The fields a wizard step saves. Omitted fields keep their value.

    ``sql_state_code`` changes only in a draft, and ``response_note`` only while waiting on information.
    """

    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra=example(
            claimed_license_number='PA-12345', claimed_license_expires_on=date(2027, 12, 31)
        ),
    )

    sql_state_code: StateCode | None = None
    claimed_license_number: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)] | None
    ) = None
    claimed_license_expires_on: date | None = None
    response_note: (
        Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)] | None
    ) = None


class AttestationAccept(BaseModel):
    """The attestation, and the version of its text, the PA accepted."""

    model_config = ConfigDict(
        extra='forbid', json_schema_extra=example(code='nccpa_current', version=1)
    )

    code: str
    version: int = Field(ge=1)


class ApplicationSubmit(BaseModel):
    """The sworn statement (Q-06), and the PA's unattached uploads to send with the application."""

    model_config = ConfigDict(
        extra='forbid',
        json_schema_extra=example(sworn=True, sworn_name='Pat Morgan', document_ids=[]),
    )

    sworn: Literal[True]
    sworn_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
    ]
    document_ids: list[UUID] = Field(default_factory=list, max_length=20)


@me.get(
    '', name='List my applications', description='Your participation applications, newest first.'
)
async def list_my_applications(
    caller: Annotated[User, require(Permission.MANAGE_OWN_RECORD)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[list[ApplicationOut]]:
    """Every application the PA has made, including decided and withdrawn ones."""
    practitioner_id = await _practitioner_id(session, caller)
    statement = (
        select(ParticipationApplication)
        .where(col(ParticipationApplication.practitioner_id) == practitioner_id)
        .order_by(
            col(ParticipationApplication.created_at).desc(), col(ParticipationApplication.id).desc()
        )
    )
    applications = (await session.scalars(statement)).all()
    return Data(data=[await _out(session, a) for a in applications])


@me.post(
    '',
    status_code=201,
    name='Start my application',
    description=(
        'Starts a draft with the state of qualifying license, which must be live. A PA has one open '
        'application at a time: `409 APPLICATION_OPEN` while another is a draft, submitted, or waiting on '
        'information. An eligible PA gets `409 ALREADY_ELIGIBLE`: changing the state of qualifying license '
        'is not in v1 (Rule 3 §3.6).'
    ),
)
async def start_my_application(
    body: ApplicationCreate,
    caller: Annotated[User, require(Permission.MANAGE_OWN_RECORD)],
    ctx: Annotated[ChangeContext, Depends(change_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[ApplicationOut]:
    """A draft writes no history and no event: the SQL has not received it (Rule 3 §3.7(a))."""
    practitioner_id = await _practitioner_id(session, caller)
    statuses = {a.status for a in await _applications_of(session, practitioner_id)}
    if statuses & OPEN_APPLICATION_STATUSES:
        raise AppError(
            409, ErrorCode.ApplicationOpen, ['Continue the application you already started']
        )
    if ApplicationStatus.ELIGIBLE in statuses:
        # Approving a new state would end the PA's privileges (Rule 3 §3.6(d)), which v1 doesn't do.
        raise AppError(409, ErrorCode.AlreadyEligible, ['Contact PA Compact to change your state'])
    await _require_live(session, body.sql_state_code)
    application = ParticipationApplication(
        practitioner_id=practitioner_id,
        kind=ApplicationKind.INITIAL,
        sql_state_code=body.sql_state_code,
        created_by=ctx.user_id,
    )
    session.add(application)
    await session.commit()
    return Data(data=await _out(session, application))


@me.get('/{application_id}', name='Get my application', description='One of your applications.')
async def get_my_application(
    application_id: ApplicationId,
    caller: Annotated[User, require(Permission.MANAGE_OWN_RECORD)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[ApplicationOut]:
    """The wizard reads this to land on the first step left to do."""
    application = await _find(session, caller, application_id)
    return Data(data=await _out(session, application))


@me.patch(
    '/{application_id}',
    name='Save my application',
    description=(
        "Saves a wizard step's answers while the application is a draft or waiting on information. "
        '`409 INVALID_TRANSITION` otherwise, when changing the state after submitting, or when replying '
        'to a request the SQL has not made.'
    ),
)
async def save_my_application(
    application_id: ApplicationId,
    body: ApplicationUpdate,
    caller: Annotated[User, require(Permission.MANAGE_OWN_RECORD)],
    ctx: Annotated[ChangeContext, Depends(change_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[ApplicationOut]:
    """No history: the next submit or resubmit records the application as sent."""
    application = await _find(session, caller, application_id, for_update=True)
    _require_editable(application)
    changes = body.model_dump(exclude_unset=True)
    if 'sql_state_code' in changes:
        if application.status != ApplicationStatus.DRAFT:
            raise AppError(
                409,
                ErrorCode.InvalidTransition,
                ['The state cannot change once the SQL has the application'],
            )
        await _require_live(session, changes['sql_state_code'])
    if 'response_note' in changes:
        if application.status != ApplicationStatus.INFO_REQUESTED:
            raise AppError(
                409, ErrorCode.InvalidTransition, ['Only a request for information takes a reply']
            )
        changes['response_note'] = changes['response_note'] or None
    for name, value in changes.items():
        setattr(application, name, value)
    application.updated_by = ctx.user_id
    await session.commit()
    return Data(data=await _out(session, application))


@me.post(
    '/{application_id}/attestations',
    status_code=201,
    name='Accept an attestation',
    description=(
        'Records that you accepted this version of an attestation. `409 ATTESTATIONS_OUT_OF_DATE` when a newer '
        'version exists: read it and accept that one. After a request for information, accept each one '
        'again to resubmit.'
    ),
)
async def accept_attestation(
    application_id: ApplicationId,
    body: AttestationAccept,
    caller: Annotated[User, require(Permission.MANAGE_OWN_RECORD)],
    ctx: Annotated[ChangeContext, Depends(change_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[ApplicationOut]:
    """Acceptances are append-only rows; accepting the same version again changes nothing."""
    application = await _find(session, caller, application_id, for_update=True)
    _require_editable(application)
    attestation = await session.get(Attestation, (body.code, body.version))
    if attestation is None or attestation.applies_to != AttestationAppliesTo.PARTICIPATION:
        raise AppError(404, ErrorCode.NotFound, ['No such attestation'])
    latest = await session.scalar(
        select(Attestation.version)
        .where(col(Attestation.code) == body.code, col(Attestation.retired_at).is_(None))
        .order_by(col(Attestation.version).desc())
        .limit(1)
    )
    if latest != body.version:
        raise AppError(409, ErrorCode.AttestationsOutOfDate, [body.code])
    await accept(
        session, ctx, _id(application), attestation, since=await _since(session, application)
    )
    await session.commit()
    return Data(data=await _out(session, application))


@me.post(
    '/{application_id}/submit',
    name='Submit my application',
    description=(
        'Sends a draft to the state of qualifying license, or resubmits one waiting on information, in one '
        'transaction. Refused with `409 INVALID_TRANSITION`, `409 STATE_NOT_LIVE`, or '
        '`409 ATTESTATIONS_OUT_OF_DATE` (the codes to accept are in `details`; a resubmission needs each '
        'accepted since the request), and `404` for a document that is not your unattached upload.'
    ),
)
async def submit_my_application(
    application_id: ApplicationId,
    body: ApplicationSubmit,
    request: Request,
    caller: Annotated[User, require(Permission.MANAGE_OWN_RECORD)],
    ctx: Annotated[ChangeContext, Depends(change_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[ApplicationOut]:
    """Resubmitting keeps ``opened_at``: the 60-day clock runs from first receipt (Rule 3 §3.7(a))."""
    application = await _find(session, caller, application_id, for_update=True)
    resubmitting = application.status == ApplicationStatus.INFO_REQUESTED
    if not resubmitting and application.status != ApplicationStatus.DRAFT:
        raise AppError(
            409,
            ErrorCode.InvalidTransition,
            [f'An application that is {application.status} cannot be submitted'],
        )
    await _require_live(session, application.sql_state_code)
    stale = await out_of_date_codes(
        session, _id(application), since=await _since(session, application)
    )
    if stale:
        raise AppError(409, ErrorCode.AttestationsOutOfDate, list(stale))
    documents = await _unattached_uploads(session, caller, body.document_ids)
    now = utc_now()
    fields = {
        'sworn_name': body.sworn_name,
        'sworn_at': now,
        'sworn_ip': request.client.host if request.client else None,
    }
    if not resubmitting:
        fields['opened_at'] = now
    event = EventType.APPLICATION_RESUBMITTED if resubmitting else EventType.APPLICATION_SUBMITTED
    await move(session, ctx, application, ApplicationStatus.SUBMITTED, event, **fields)
    for document in documents:
        await attach(
            session,
            ctx,
            document,
            owner_type=DocumentOwnerType.PARTICIPATION_APPLICATION,
            owner_id=_id(application),
        )
    await session.commit()
    return Data(data=await _out(session, application))


@me.post(
    '/{application_id}/withdraw',
    name='Withdraw my application',
    description=(
        'Withdraws an application the SQL has received and not decided (Rule 3 §3.7). A draft is never '
        'withdrawn: `409 INVALID_TRANSITION`.'
    ),
)
async def withdraw_my_application(
    application_id: ApplicationId,
    caller: Annotated[User, require(Permission.MANAGE_OWN_RECORD)],
    ctx: Annotated[ChangeContext, Depends(change_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[ApplicationOut]:
    """To apply again, the PA starts a new application."""
    application = await _find(session, caller, application_id, for_update=True)
    try:
        await move(
            session,
            ctx,
            application,
            ApplicationStatus.WITHDRAWN,
            EventType.APPLICATION_WITHDRAWN,
            withdrawn_at=utc_now(),
        )
    except InvalidTransitionError as error:
        raise AppError(409, ErrorCode.InvalidTransition, [str(error)]) from error
    await session.commit()
    return Data(data=await _out(session, application))


def _id(application: ParticipationApplication) -> int:
    return application.id  # type: ignore[return-value]  # every application here was loaded or flushed


async def _practitioner_id(session: AsyncSession, caller: User) -> int:
    statement = select(col(Practitioner.id)).where(col(Practitioner.user_id) == caller.id)
    practitioner_id = (await session.scalars(statement)).one_or_none()
    if practitioner_id is None:
        raise AppError(404, ErrorCode.NotFound, ['You have no practitioner record'])
    return practitioner_id


async def _applications_of(
    session: AsyncSession, practitioner_id: int
) -> list[ParticipationApplication]:
    statement = select(ParticipationApplication).where(
        col(ParticipationApplication.practitioner_id) == practitioner_id
    )
    return list((await session.scalars(statement)).all())


async def _find(
    session: AsyncSession, caller: User, application_id: UUID, *, for_update: bool = False
) -> ParticipationApplication:
    statement = select(ParticipationApplication).where(
        col(ParticipationApplication.public_id) == application_id,
        col(ParticipationApplication.practitioner_id) == await _practitioner_id(session, caller),
    )
    if for_update:
        statement = statement.with_for_update()
    application = (await session.scalars(statement)).one_or_none()
    if application is None:
        raise AppError(404, ErrorCode.NotFound, ['No such application'])
    return application


async def _since(session: AsyncSession, application: ParticipationApplication) -> datetime | None:
    """Acceptances before the SQL's latest request don't count toward resubmitting."""
    if application.status != ApplicationStatus.INFO_REQUESTED:
        return None
    return await requested_at(session, _id(application))


def _require_editable(application: ParticipationApplication) -> None:
    if application.status not in _EDITABLE:
        raise AppError(
            409,
            ErrorCode.InvalidTransition,
            [f'An application that is {application.status} cannot be changed'],
        )


async def _require_live(session: AsyncSession, state_code: str) -> None:
    state = await session.get(State, state_code)
    if state is None or not (state.is_member and state.is_live):
        raise AppError(409, ErrorCode.StateNotLive, [f'{state_code} is not accepting applications'])


async def _unattached_uploads(
    session: AsyncSession, caller: User, document_ids: list[UUID]
) -> list[Document]:
    if not document_ids:
        return []
    statement = select(Document).where(
        col(Document.public_id).in_(document_ids),
        col(Document.created_by) == caller.id,
        col(Document.owner_type).is_(None),
        col(Document.uploaded_in_state).is_(None),
    )
    documents = list((await session.scalars(statement)).all())
    if len(documents) != len(set(document_ids)):
        raise AppError(404, ErrorCode.NotFound, ['No such document'])
    return documents


async def _out(session: AsyncSession, application: ParticipationApplication) -> ApplicationOut:
    accepted = (
        await session.scalars(
            select(ParticipationApplicationAttestation)
            .where(
                col(ParticipationApplicationAttestation.participation_application_id)
                == application.id
            )
            .order_by(
                col(ParticipationApplicationAttestation.attestation_code),
                col(ParticipationApplicationAttestation.attestation_version),
            )
        )
    ).all()
    latest = {row.attestation_code: row for row in accepted}
    documents = (
        await session.scalars(
            select(Document)
            .where(
                col(Document.owner_type) == DocumentOwnerType.PARTICIPATION_APPLICATION,
                col(Document.owner_id) == application.id,
            )
            .order_by(col(Document.created_at), col(Document.id))
        )
    ).all()
    waiting = application.status == ApplicationStatus.INFO_REQUESTED
    return ApplicationOut.model_validate(
        {
            **application.model_dump(),
            'requested_at': await _since(session, application),
            'resubmit_by': resubmit_by(application.opened_at, await reference_time_zone(session))
            if waiting and application.opened_at
            else None,
            'attestations': [
                AcceptedAttestation(
                    code=row.attestation_code,
                    version=row.attestation_version,
                    accepted_at=row.accepted_at,
                )
                for row in latest.values()
            ],
            'documents': [DocumentOut.model_validate(d) for d in documents],
        }
    )
