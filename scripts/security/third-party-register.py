"""Write the third-party materials register (SOW §7.5) from CycloneDX SBOMs.

Usage: third-party-register.py OUTPUT.md NAME=SBOM.json [NAME=SBOM.json ...]

Each NAME is the deliverable the SBOM describes (the API image, the client).
A component whose package declares no licence is listed as "not declared"
rather than guessed, so the gap is visible to whoever reviews the register.
"""

import json
import sys
from pathlib import Path
from urllib.parse import unquote


def licence(component: dict) -> str:
    names = []
    for entry in component.get('licenses', []):
        if 'expression' in entry:
            names.append(entry['expression'])
        else:
            lic = entry.get('license', {})
            names.append(lic.get('id') or lic.get('name', ''))
    return ' / '.join(n for n in names if n) or 'not declared'


def ecosystem(component: dict) -> str:
    purl = component.get('purl', '')
    return purl[4 : purl.index('/')] if purl.startswith('pkg:') and '/' in purl else ''


def name(component: dict) -> str:
    group = component.get('group')
    return unquote(f'{group}/{component["name"]}' if group else component['name'])


def section(title: str, sbom: dict) -> list[str]:
    rows = sorted(
        {
            (name(c), c.get('version', ''), ecosystem(c), licence(c))
            for c in sbom.get('components', [])
            if c.get('type') == 'library'
        }
    )
    undeclared = sum(1 for row in rows if row[3] == 'not declared')
    lines = [
        f'## {title}',
        '',
        f'{len(rows)} components; {undeclared} declare no licence.',
        '',
        '| Component | Version | Ecosystem | Licence |',
        '|---|---|---|---|',
    ]
    lines += [f'| {n} | {v} | {e} | {lic} |' for n, v, e, lic in rows]
    return [*lines, '']


def main(output: str, sboms: list[str]) -> None:
    lines = [
        '# Third-party materials register',
        '',
        'Generated from the CycloneDX SBOMs of one build by',
        '`scripts/security/third-party-register.py`; do not edit by hand.',
        '',
    ]
    for arg in sboms:
        title, path = arg.split('=', 1)
        lines += section(title, json.loads(Path(path).read_text()))
    Path(output).write_text('\n'.join(lines))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
