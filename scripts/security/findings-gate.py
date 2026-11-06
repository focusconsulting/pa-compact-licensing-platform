"""Fail when a scan report holds a medium, high, or critical finding.

Usage: findings-gate.py sarif REPORT [REPORT ...]
       findings-gate.py zap RULES.tsv REPORT [REPORT ...]

SARIF (CodeQL): a result is medium or worse when its rule's
security-severity is 4.0 or more, GitHub's own boundary. ZAP baseline JSON:
when its riskcode is 2 (medium) or 3 (high), unless the ZAP rules file marks
its plugin IGNORE (ZAP still writes ignored alerts to the JSON). Each
accepted finding has an entry in the false-positive register
(engineering/docs/security/false-positives.md).
"""

import json
import sys
from pathlib import Path

MEDIUM_SECURITY_SEVERITY = 4.0
MEDIUM_RISKCODE = 2


def sarif_findings(report: dict) -> list[str]:
    found = []
    for run in report.get('runs', []):
        rules = {r['id']: r for r in run['tool']['driver'].get('rules', [])}
        for extension in run['tool'].get('extensions', []):
            rules.update({r['id']: r for r in extension.get('rules', [])})
        for result in run.get('results', []):
            props = rules.get(result['ruleId'], {}).get('properties', {})
            severity = float(props.get('security-severity', 0))
            if severity >= MEDIUM_SECURITY_SEVERITY:
                where = result['locations'][0]['physicalLocation']
                line = where.get('region', {}).get('startLine', '?')
                found.append(
                    f'{severity:.1f} {result["ruleId"]} {where["artifactLocation"]["uri"]}:{line}'
                )
    return found


def ignored_plugins(rules: str) -> set[str]:
    rows = (line.split('\t') for line in Path(rules).read_text().splitlines())
    return {row[0] for row in rows if len(row) > 1 and row[1] == 'IGNORE'}


def zap_findings(report: dict, ignored: set[str]) -> list[str]:
    return [
        f'{alert["riskdesc"]} {alert["pluginid"]} {alert["name"]} ({site["@name"]})'
        for site in report.get('site', [])
        for alert in site.get('alerts', [])
        if int(alert['riskcode']) >= MEDIUM_RISKCODE and alert['pluginid'] not in ignored
    ]


def main(kind: str, args: list[str]) -> int:
    if kind == 'zap':
        ignored = ignored_plugins(args[0])
        found = [
            f for p in args[1:] for f in zap_findings(json.loads(Path(p).read_text()), ignored)
        ]
    else:
        found = [f for p in args for f in sarif_findings(json.loads(Path(p).read_text()))]
    for finding in found:
        print(finding)
    print(f'{len(found)} medium or worse finding(s)')
    return 1 if found else 0


if __name__ == '__main__':
    if sys.argv[1:2] not in (['sarif'], ['zap']) or len(sys.argv) < (
        3 if sys.argv[1] == 'sarif' else 4
    ):
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2:]))
