"""Write the API's OpenAPI document to ``openapi.json``, which the client's types and the Prism mock read.

Run with ``just openapi``; ``tests/test_openapi.py`` fails while the committed document differs from the code.
"""

import copy
import json
from pathlib import Path
from typing import Any

from licensing_api.__main__ import app

DOCUMENT = Path(__file__).parents[1] / 'openapi.json'


def document() -> dict[str, Any]:
    """``app.openapi()`` with the ``null`` example values FastAPI drops put back, so Prism's mocks keep every field."""
    openapi = copy.deepcopy(app.openapi())
    for schema in openapi['components']['schemas'].values():
        for example in schema.get('examples', []):
            for name in schema.get('required', []):
                example.setdefault(name, None)
    return openapi


def main() -> None:
    """Write the document with sorted keys, so a regeneration changes only what the code changed."""
    DOCUMENT.write_text(json.dumps(document(), indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
