"""Published configuration the application wizard reads: the current attestations and the states."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from licensing_api.dependencies import get_db_session
from licensing_api.permissions import public
from licensing_api.repo.attestation import AttestationAppliesTo, current_attestations
from licensing_api.repo.state import State
from licensing_api.responses import Data, example

router = APIRouter()


class AttestationOut(BaseModel):
    """The current version of an attestation. Accept it by ``code`` and ``version``."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra=example(
            code='nccpa_current',
            version=1,
            applies_to=AttestationAppliesTo.PARTICIPATION,
            text='I hold a current certification from the National Commission on Certification of '
            'Physician Assistants (NCCPA).',
        ),
    )

    code: str
    version: int
    applies_to: AttestationAppliesTo
    text: str


class StateOut(BaseModel):
    """A state, and whether it takes applications: only a live member does."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra=example(code='KS', name='Kansas', is_member=True, is_live=True),
    )

    code: str
    name: str
    is_member: bool
    is_live: bool


@router.get(
    '/attestations',
    name='List current attestations',
    description='The current version of each attestation that applies in every state, in the order to show them.',
    dependencies=[public()],
)
async def list_attestations(
    applies_to: AttestationAppliesTo,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[list[AttestationOut]]:
    """Public: the texts are what every applicant reads."""
    attestations = (await session.scalars(current_attestations(applies_to))).all()
    return Data(data=[AttestationOut.model_validate(a) for a in attestations])


@router.get(
    '/states',
    name='List states',
    description='Every US jurisdiction, by name, with its membership and whether it is live.',
    dependencies=[public()],
)
async def list_states(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Data[list[StateOut]]:
    """Public: membership and go-live are published configuration (Q-03)."""
    states = (await session.scalars(select(State).order_by(col(State.name)))).all()
    return Data(data=[StateOut.model_validate(s) for s in states])
