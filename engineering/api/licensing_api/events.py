"""Handler declarations: what the Worker runs for each event (D2, FLOW-07)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from licensing_api.context import ChangeContext
from licensing_api.repo.base import DOTTED_NAME
from licensing_api.repo.domain_event import DomainEvent, EventType

HandlerFn = Callable[[AsyncSession, ChangeContext, DomainEvent], Awaitable[None]]


@dataclass(frozen=True)
class Handler:
    """One consumer of one or more event types.

    ``name`` keys its delivery rows, so it must not change while they exist; it is
    never derived from the import path, which a rename would change.
    """

    name: str
    event_types: frozenset[EventType]
    run: HandlerFn


def handler(name: str, *event_types: EventType) -> Callable[[HandlerFn], Handler]:
    """Declare a handler. Registers nothing: the Worker builds a ``HandlerRegistry`` from a constant tuple."""
    if not DOTTED_NAME.fullmatch(name):
        raise ValueError(
            f'Handler name {name!r} must be "<owning module>.<what it does>" in lower snake case'
        )
    if not event_types:
        raise ValueError(f'Handler {name!r} must handle at least one event type')

    def declare(run: HandlerFn) -> Handler:
        return Handler(name=name, event_types=frozenset(event_types), run=run)

    return declare


class HandlerRegistry:
    """The handlers the Worker runs, fixed when it is built."""

    def __init__(self, handlers: Iterable[Handler]) -> None:
        by_name: dict[str, Handler] = {}
        for declared in handlers:
            if declared.name in by_name:
                raise ValueError(f'Two handlers are named {declared.name!r}')
            by_name[declared.name] = declared
        self._handlers = tuple(by_name.values())

    def for_event(self, event_type: str) -> tuple[Handler, ...]:
        """The handlers that consume ``event_type``, in the order they were registered.

        Takes the stored string, so an event whose type left ``EventType`` matches no handler.
        """
        return tuple(h for h in self._handlers if event_type in h.event_types)

    def named(self, name: str) -> Handler | None:
        """The handler registered as ``name``, or None once it has been removed."""
        return next((h for h in self._handlers if h.name == name), None)
