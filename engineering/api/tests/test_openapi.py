"""The committed OpenAPI document matches the code, and every body a route returns has an example to mock."""

import json
from pathlib import Path

from licensing_api.__main__ import app

_DOCUMENT = Path(__file__).parents[1] / 'openapi.json'
_SCHEMAS = app.openapi()['components']['schemas']
# The envelope wrappers are built by the mock generator from the example of what they hold.
_WRAPPERS = ('Data_', 'Paged_')


def test_the_committed_document_matches_the_code():
    assert json.loads(_DOCUMENT.read_text()) == app.openapi(), 'run `just openapi`'


def _models(schema: dict) -> set[str]:
    """The models a response body holds: the schema it names, or what an envelope wraps."""
    ref = schema.get('$ref') or schema.get('items', {}).get('$ref')
    if ref is None:
        return set()
    name = ref.rsplit('/', 1)[1]
    if not name.startswith(_WRAPPERS):
        return {name}
    return _models(_SCHEMAS[name]['properties']['data'])


def _success_models() -> set[str]:
    found = set()
    for operations in app.openapi()['paths'].values():
        for operation in operations.values():
            for status, response in operation['responses'].items():
                if status.startswith('2') and 'content' in response:
                    found |= _models(response['content']['application/json']['schema'])
    return found


def test_every_success_body_has_an_example():
    assert _success_models()
    missing = sorted(name for name in _success_models() if 'examples' not in _SCHEMAS[name])
    assert missing == []


def test_a_validation_error_is_documented_as_the_error_response():
    for operations in app.openapi()['paths'].values():
        for operation in operations.values():
            schema = operation['responses']['422']['content']['application/json']['schema']
            assert schema == {'$ref': '#/components/schemas/ErrorResponse'}
