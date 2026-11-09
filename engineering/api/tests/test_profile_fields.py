"""The platform contract's profile field groups match the ``practitioners`` model (SCRUM-103)."""

import re
from pathlib import Path

from sqlmodel import SQLModel

import licensing_api.repo  # noqa: F401 -- registers every table model on SQLModel.metadata
from licensing_api.repo.practitioner import Practitioner

_CONTRACT = Path(__file__).parents[2] / 'docs/platform-contract.md'

_PROVENANCE = ('entered_by', 'verified_by_state', 'verified_at')

# Columns that belong to no group: keys, the SQL pointer, NPI (never stamped), and audit columns.
_UNGROUPED = {
    'id',
    'public_id',
    'user_id',
    'current_sql_state_code',
    'npi',
    'created_at',
    'created_by',
    'updated_at',
    'updated_by',
}

# Listed in the contract before their table exists. SCRUM-107 creates it; remove it then.
_PENDING_TABLES = {'practitioner_other_names'}


def _groups() -> dict[str, list[str]]:
    section = _CONTRACT.read_text().split('### Profile fields\n')[1].split('\n## ')[0]
    rows = (line.split('|')[1:-1] for line in section.splitlines() if line.startswith('| `'))
    return {
        re.findall(r'`([a-z_]+)`', cells[0])[0]: re.findall(r'`([a-z_0-9]+)`', cells[1])
        for cells in rows
    }


def _columns() -> set[str]:
    return set(Practitioner.__table__.columns.keys())  # type: ignore[attr-defined]


def test_every_group_has_its_provenance_columns():
    expected = {f'{group}_{suffix}' for group in _groups() for suffix in _PROVENANCE}
    assert expected <= _columns()


def test_every_data_set_column_is_in_exactly_one_group():
    listed = [name for fields in _groups().values() for name in fields if name in _columns()]
    provenance = {c for c in _columns() if c.endswith(_PROVENANCE)}
    assert sorted(listed) == sorted(_columns() - _UNGROUPED - provenance)


def test_every_other_listed_name_is_a_table():
    tables = set(SQLModel.metadata.tables) | _PENDING_TABLES
    others = {name for fields in _groups().values() for name in fields if name not in _columns()}
    assert others <= tables
