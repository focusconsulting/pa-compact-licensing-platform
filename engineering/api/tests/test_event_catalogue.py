"""Every event type has a consumer and a test (Principle VI, FLOW-07)."""

from pathlib import Path

from licensing_api.handlers import HANDLERS
from licensing_api.repo.domain_event import EventType

# FLOW-07 consumers that are not email, with the backlog item that builds them.
_CONSUMED_ELSEWHERE = {
    EventType.PRACTITIONER_PROFILE_CHANGED: 'U-03 propagates the change to every state the PA is in',
    EventType.PRACTITIONER_EMAIL_CHANGE_REQUESTED: 'U-03 sends the verification code',
}


def test_every_event_type_has_a_handler_or_a_named_owner():
    handled = {event_type for declared in HANDLERS for event_type in declared.event_types}

    assert set(EventType) - handled == set(_CONSUMED_ELSEWHERE)


def test_every_handled_event_type_is_named_in_a_test():
    here = Path(__file__)
    source = '\n'.join(path.read_text() for path in here.parent.glob('test_*.py') if path != here)

    untested = [
        event_type.name
        for event_type in EventType
        if event_type not in _CONSUMED_ELSEWHERE and f'EventType.{event_type.name}' not in source
    ]

    assert untested == []
