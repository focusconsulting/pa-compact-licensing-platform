"""FLOW-06's participation application diagram and APPLICATION_TRANSITIONS say the same thing."""

import re
from pathlib import Path

from licensing_api.repo.participation_application import (
    APPLICATION_TRANSITIONS,
    ApplicationStatus,
)

_FLOW_06 = Path(__file__).parents[3] / 'product/context/flows/06-state-machines.md'


def _diagram_edges() -> set[tuple[str, str]]:
    section = _FLOW_06.read_text().split('## Participation application')[1].split('\n## ')[0]
    diagram = section.split('```mermaid')[1].split('```')[0]
    return {
        (source, target)
        for source, target in re.findall(r'^\s*(\S+) --> (\S+?):?(?:\s|$)', diagram, re.MULTILINE)
        if '[*]' not in (source, target)
    }


def test_flow_06_has_exactly_the_coded_transitions():
    coded = {
        (source.value, target.value)
        for source, targets in APPLICATION_TRANSITIONS.items()
        for target in targets
    }

    assert _diagram_edges() == coded


def test_every_status_is_reachable_in_flow_06():
    named = {status for edge in _diagram_edges() for status in edge}

    assert named == {status.value for status in ApplicationStatus}
