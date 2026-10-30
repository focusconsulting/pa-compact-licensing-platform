"""Write the API's OpenAPI document to ``openapi.json``, which the client's types and the Prism mock read.

The document also holds the statuses the client labels, before any route returns them.

Run with ``just openapi``; ``tests/test_openapi.py`` fails while the committed document differs from the code.
"""

import copy
import json
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from licensing_api.__main__ import app
from licensing_api.repo.participation_application import ApplicationStatus
from licensing_api.repo.privilege_request import PrivilegeRequestStatus
from licensing_api.repo.status import LicenseComputedStatus, PrivilegeComputedStatus

DOCUMENT = Path(__file__).parents[1] / 'openapi.json'
# A route that returns one of these emits the same schema under the same name.
STATUS_ENUMS = (
    ApplicationStatus,
    PrivilegeRequestStatus,
    PrivilegeComputedStatus,
    LicenseComputedStatus,
)


def document() -> dict[str, Any]:
    """``app.openapi()`` with the ``null`` example values FastAPI drops put back, and the status enums.

    The ``null`` values keep every field in Prism's mocks.
    """
    openapi = copy.deepcopy(app.openapi())
    for enum in STATUS_ENUMS:
        openapi['components']['schemas'].setdefault(enum.__name__, TypeAdapter(enum).json_schema())
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
