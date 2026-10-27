"""The handlers the Worker runs (FLOW-07).

Removing one dead-letters its undelivered rows (ADR-0012), so a handler is removed only
once it has none.
"""

from licensing_api.events import Handler
from licensing_api.notifications.applications import APPLICATION_HANDLERS
from licensing_api.notifications.discipline import DISCIPLINE_HANDLERS
from licensing_api.notifications.privileges import PRIVILEGE_HANDLERS

HANDLERS: tuple[Handler, ...] = (*APPLICATION_HANDLERS, *PRIVILEGE_HANDLERS, *DISCIPLINE_HANDLERS)
