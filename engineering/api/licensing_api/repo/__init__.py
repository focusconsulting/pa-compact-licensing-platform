"""Table models. Importing them all here keeps SQLAlchemy's metadata complete, so foreign keys between tables resolve whichever model is used first."""

from licensing_api.repo.adverse_action import AdverseAction, AdverseActionNpdbCategory
from licensing_api.repo.audit_log import AuditLogEntry
from licensing_api.repo.compact_settings import CompactSettings
from licensing_api.repo.document import Document
from licensing_api.repo.domain_event import DomainEvent, DomainEventDelivery
from licensing_api.repo.history import (
    AdverseActionHistory,
    ParticipationApplicationHistory,
    PractitionerHistory,
    PrivilegeHistory,
    PrivilegeRequestHistory,
    QualifyingLicenseHistory,
    SiiReportHistory,
)
from licensing_api.repo.notification import Notification
from licensing_api.repo.participation_application import ParticipationApplication
from licensing_api.repo.practitioner import Practitioner, PractitionerSsn
from licensing_api.repo.privilege import Privilege
from licensing_api.repo.privilege_request import PrivilegeRequest
from licensing_api.repo.qualifying_license import QualifyingLicense
from licensing_api.repo.reference import (
    RefAdverseActionType,
    RefDenialReason,
    RefNpdbCategory,
    RefSex,
)
from licensing_api.repo.sii_report import SiiReport
from licensing_api.repo.state import State
from licensing_api.repo.status import CompactEligibility, PrivilegeStatus, QualifyingLicenseStatus
from licensing_api.repo.user import User

__all__ = [
    'AdverseAction',
    'AdverseActionHistory',
    'AdverseActionNpdbCategory',
    'AuditLogEntry',
    'CompactEligibility',
    'CompactSettings',
    'Document',
    'DomainEvent',
    'DomainEventDelivery',
    'Notification',
    'ParticipationApplication',
    'ParticipationApplicationHistory',
    'Practitioner',
    'PractitionerHistory',
    'PractitionerSsn',
    'Privilege',
    'PrivilegeHistory',
    'PrivilegeRequest',
    'PrivilegeRequestHistory',
    'PrivilegeStatus',
    'QualifyingLicense',
    'QualifyingLicenseHistory',
    'QualifyingLicenseStatus',
    'RefAdverseActionType',
    'RefDenialReason',
    'RefNpdbCategory',
    'RefSex',
    'SiiReport',
    'SiiReportHistory',
    'State',
    'User',
]
