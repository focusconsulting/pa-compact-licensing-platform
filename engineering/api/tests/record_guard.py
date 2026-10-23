"""Fails a route test whose transaction changes a record without an event (Principle VI, FLOW-07)."""

from __future__ import annotations

from sqlalchemy import Insert, event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import ORMExecuteState, Session


class RecordGuard:
    """Watches one session; ``violations`` names each commit that wrote history and no event.

    A history row is how every write shows it changed a record, so a commit with
    one and no ``domain_events`` row is a change no handler will ever see.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.violations: list[str] = []
        self._history_tables: set[str] = set()
        self._emitted = False
        sync = session.sync_session
        event.listen(sync, 'do_orm_execute', self._on_execute)
        event.listen(sync, 'before_commit', self._on_commit)
        event.listen(sync, 'after_rollback', self._reset)

    def _on_execute(self, state: ORMExecuteState) -> None:
        statement = state.statement
        if not isinstance(statement, Insert):
            return
        table = statement.table.name
        if table.endswith('_history'):
            self._history_tables.add(table)
        elif table == 'domain_events':
            self._emitted = True

    def _on_commit(self, session: Session) -> None:
        if self._history_tables and not self._emitted:
            self.violations.append(
                f'Committed {", ".join(sorted(self._history_tables))} with no domain_events row'
            )
        self._reset(session)

    def _reset(self, _session: Session) -> None:
        self._history_tables.clear()
        self._emitted = False
