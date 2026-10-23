"""Write the API's OpenAPI document to ``openapi.json``, which the client's types and mocks are generated from.

Run with ``just openapi``; ``tests/test_openapi.py`` fails while the committed document differs from the code.
"""

import json
from pathlib import Path

from licensing_api.__main__ import app

DOCUMENT = Path(__file__).parents[1] / 'openapi.json'


def main() -> None:
    """Write the document with sorted keys, so a regeneration changes only what the code changed."""
    DOCUMENT.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
