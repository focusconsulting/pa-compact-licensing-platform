"""Which documents a caller may see: the owner's record decides (Rule 4 §4.5, backlog D9).

Each function returns a condition on ``Document`` for a route's query, so a document outside
the caller's scope is never loaded and answers ``404`` (constitution Principle II).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement, and_, exists, or_, select, true
from sqlmodel import col

from licensing_api.repo.adverse_action import AdverseAction
from licensing_api.repo.document import Document, DocumentOwnerType
from licensing_api.repo.participation_application import ParticipationApplication
from licensing_api.repo.privilege import Privilege
from licensing_api.repo.privilege_request import PrivilegeRequest
from licensing_api.repo.qualifying_license import QualifyingLicense
from licensing_api.repo.sii_report import SiiReport
from licensing_api.repo.user import User


def visible_to_practitioner(practitioner_id: int | None, user_id: int) -> ColumnElement[bool]:
    """A PA's own record: their practitioner, applications, and privilege requests, and what they
    uploaded that is not attached yet. Never adverse-action or SII documents (ML §8.C)."""
    unattached = and_(col(Document.owner_type).is_(None), col(Document.created_by) == user_id)
    if practitioner_id is None:
        return unattached
    return or_(
        unattached,
        and_(
            col(Document.owner_type) == DocumentOwnerType.PRACTITIONER,
            col(Document.owner_id) == practitioner_id,
        ),
        _owned_by(
            DocumentOwnerType.PARTICIPATION_APPLICATION,
            ParticipationApplication,
            col(ParticipationApplication.practitioner_id) == practitioner_id,
        ),
        _owned_by(
            DocumentOwnerType.PRIVILEGE_REQUEST,
            PrivilegeRequest,
            col(PrivilegeRequest.practitioner_id) == practitioner_id,
        ),
    )


def visible_to_state(state_code: str) -> ColumnElement[bool]:
    """One state's documents: its own cases and uploads, and the documents of every PA it holds.

    An application belongs to its state of qualifying license and a privilege request to its
    remote state; a practitioner's, adverse action's, or SII report's documents are seen by the
    reporting state and every state where the PA holds a license or privilege, the states that
    are told about them (FLOW-07). Unattached uploads belong to the uploader's state.
    """
    state_code = state_code.upper()
    uploaded_here = exists(
        select(1).where(
            col(User.id) == col(Document.created_by), col(User.state_code) == state_code
        )
    )
    return or_(
        and_(
            or_(
                col(Document.owner_type).is_(None),
                col(Document.owner_type) == DocumentOwnerType.INGESTION_BATCH,
            ),
            uploaded_here,
        ),
        and_(
            col(Document.owner_type) == DocumentOwnerType.STATE,
            col(Document.owner_key) == state_code,
        ),
        and_(
            col(Document.owner_type) == DocumentOwnerType.PRACTITIONER,
            _holds(col(Document.owner_id), state_code),
        ),
        _owned_by(
            DocumentOwnerType.PARTICIPATION_APPLICATION,
            ParticipationApplication,
            col(ParticipationApplication.sql_state_code) == state_code,
        ),
        _owned_by(
            DocumentOwnerType.PRIVILEGE_REQUEST,
            PrivilegeRequest,
            col(PrivilegeRequest.remote_state_code) == state_code,
        ),
        _owned_by(
            DocumentOwnerType.ADVERSE_ACTION,
            AdverseAction,
            or_(
                col(AdverseAction.reporting_state_code) == state_code,
                _holds(col(AdverseAction.practitioner_id), state_code),
            ),
        ),
        _owned_by(
            DocumentOwnerType.SII_REPORT,
            SiiReport,
            or_(
                col(SiiReport.reporting_state_code) == state_code,
                _holds(col(SiiReport.practitioner_id), state_code),
            ),
        ),
    )


def visible_to_commission() -> ColumnElement[bool]:
    """Every document: the Commission reads every state's records."""
    return true()


def _owned_by(
    owner_type: DocumentOwnerType, model: Any, condition: ColumnElement[bool]
) -> ColumnElement[bool]:
    return and_(
        col(Document.owner_type) == owner_type,
        exists(select(1).where(col(model.id) == col(Document.owner_id), condition)),
    )


def _holds(practitioner_id: Any, state_code: str) -> ColumnElement[bool]:
    """Whether the PA holds a qualifying license or a privilege in the state, as
    ``notifications.recipients.states_holding`` counts it."""
    return or_(
        exists(
            select(1).where(
                col(QualifyingLicense.practitioner_id) == practitioner_id,
                col(QualifyingLicense.state_code) == state_code,
            )
        ),
        exists(
            select(1).where(
                col(Privilege.practitioner_id) == practitioner_id,
                col(Privilege.remote_state_code) == state_code,
            )
        ),
    )
