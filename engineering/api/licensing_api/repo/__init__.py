"""Table models. Importing them all here keeps SQLAlchemy's metadata complete, so foreign keys between tables resolve whichever model is used first."""

from licensing_api.repo.audit_log import AuditLogEntry
from licensing_api.repo.compact_settings import CompactSettings
from licensing_api.repo.domain_event import DomainEvent, DomainEventDelivery
from licensing_api.repo.notification import Notification
from licensing_api.repo.reference import (
    RefAdverseActionType,
    RefDenialReason,
    RefNpdbCategory,
    RefSex,
)
from licensing_api.repo.state import State
from licensing_api.repo.user import User

__all__ = [
    'AuditLogEntry',
    'CompactSettings',
    'DomainEvent',
    'DomainEventDelivery',
    'Notification',
    'RefAdverseActionType',
    'RefDenialReason',
    'RefNpdbCategory',
    'RefSex',
    'State',
    'User',
]
