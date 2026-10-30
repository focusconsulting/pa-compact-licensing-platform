"""Snapshot files: rendered output a reviewer reads in the diff. ``UPDATE_SNAPSHOTS=1 just test`` rewrites them."""

import os
from pathlib import Path

SNAPSHOTS_DIR = Path(__file__).parent / 'snapshots'


def assert_matches_snapshot(name: str, actual: str) -> None:
    path = SNAPSHOTS_DIR / name
    if os.environ.get('UPDATE_SNAPSHOTS') == '1':
        path.write_text(actual)
        return
    assert path.exists(), f'No snapshot {name}; run with UPDATE_SNAPSHOTS=1 to write it'
    assert actual == path.read_text(), (
        f'{name} differs; run with UPDATE_SNAPSHOTS=1 if the change is intended'
    )
