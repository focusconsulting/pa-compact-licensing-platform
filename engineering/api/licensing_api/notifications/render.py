"""Email templates: each is a ``<name>.txt`` and a ``<name>.html`` in ``templates/`` (ADR-0014).

The text file defines the ``subject`` and ``body`` blocks; the HTML file defines ``body``.
Both extend a base layout that, outside PROD, says the email comes from a test system.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from licensing_api.config import Settings

TEMPLATES_DIR = Path(__file__).parent / 'templates'
# Layouts the templates extend, never sent on their own.
LAYOUTS = frozenset({'base'})


@dataclass(frozen=True)
class RenderedEmail:
    """An email ready to send."""

    subject: str
    text: str
    html: str


def template_environment(directories: Sequence[Path] = (TEMPLATES_DIR,)) -> Environment:
    """Load templates from ``directories``, first match wins. HTML is autoescaped; a missing value raises rather than rendering blank."""
    return Environment(
        loader=FileSystemLoader(directories),
        autoescape=select_autoescape(['html']),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )


def template_names(directory: Path = TEMPLATES_DIR) -> list[str]:
    """Every template that can be sent: a name with a ``.txt`` file, not a layout."""
    return sorted(path.stem for path in directory.glob('*.txt') if path.stem not in LAYOUTS)


def render(
    environment: Environment, template: str, context: Mapping[str, Any], settings: Settings
) -> RenderedEmail:
    """Render ``template`` with ``context`` and the values every layout uses.

    Raises ``jinja2.TemplateError`` when the template is missing or ``context`` lacks a value it uses.
    """
    values = {
        **context,
        'client_base_url': settings.client_base_url.rstrip('/'),
        'environment': settings.environment,
    }
    text_template = environment.get_template(f'{template}.txt')
    subject = ''.join(text_template.blocks['subject'](text_template.new_context(values))).strip()
    if settings.environment != 'PROD':
        subject = f'[{settings.environment}] {subject}'
    return RenderedEmail(
        subject=subject,
        text=text_template.render(values),
        html=environment.get_template(f'{template}.html').render(values),
    )
