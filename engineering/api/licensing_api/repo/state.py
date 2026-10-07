from __future__ import annotations

from datetime import date
from enum import StrEnum

from sqlmodel import Field

from licensing_api.repo.base import AuditColumns


class ProofRequirement(StrEnum):
    """What a remote state requires for one proof before it issues a privilege (Rule 3 §3.4(c)(3)-(6))."""

    NONE = 'none'
    ATTESTATION = 'attestation'
    PROOF_UPLOAD = 'proof_upload'


class State(AuditColumns, table=True):
    """A US jurisdiction. Every jurisdiction exists; membership and go-live are configuration (Q-03).

    A state can be live only while it is a member (``chk_states_live_requires_member``).
    """

    # SQLModel defines __tablename__ as a declared_attr method; assigning a string is its documented way to name a table.
    __tablename__ = 'states'  # type: ignore[assignment]

    code: str = Field(primary_key=True, max_length=2)
    name: str = Field(unique=True)
    is_member: bool = False
    member_effective_on: date | None = None
    is_live: bool = False
    practice_requirements_url: str | None = None
    jurisprudence_requirement: str = ProofRequirement.NONE
    supervision_agreement_requirement: str = ProofRequirement.NONE
    prescriptive_authority_requirement: str = ProofRequirement.NONE
    other_compliance_requirement: str = ProofRequirement.NONE
