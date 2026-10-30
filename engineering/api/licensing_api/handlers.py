"""The handlers the Worker runs (FLOW-07).

Removing one dead-letters its undelivered rows (ADR-0012), so a handler is removed only
once it has none.
"""

from licensing_api.events import Handler

HANDLERS: tuple[Handler, ...] = ()
