"""The committed OpenAPI document matches the code, and every body a route returns has an example to mock."""

import json
from pathlib import Path

from licensing_api.__main__ import app
from scripts.export_openapi import document

_DOCUMENT = Path(__file__).parents[1] / 'openapi.json'
_SCHEMAS = document()['components']['schemas']
# The envelope wrappers carry no example; Prism builds them from the examples of what they hold.
_WRAPPERS = ('Data_', 'Paged_')


def test_the_committed_document_matches_the_code():
    assert json.loads(_DOCUMENT.read_text()) == document(), 'run `just openapi`'


def _models(schema: dict) -> set[str]:
    """The models a response body holds: the schema it names, or what an envelope's properties name."""
    ref = schema.get('$ref') or schema.get('items', {}).get('$ref')
    if ref is None:
        return set()
    name = ref.rsplit('/', 1)[1]
    if not name.startswith(_WRAPPERS):
        return {name}
    return set().union(*(_models(prop) for prop in _SCHEMAS[name]['properties'].values()))


def _success_models() -> set[str]:
    found = set()
    for operations in app.openapi()['paths'].values():
        for operation in operations.values():
            for status, response in operation['responses'].items():
                if status.startswith('2') and 'content' in response:
                    found |= _models(response['content']['application/json']['schema'])
    return found


def test_every_success_body_has_an_example():
    assert {'CurrentUser', 'Page'} <= _success_models()
    missing = sorted(name for name in _success_models() if 'examples' not in _SCHEMAS[name])
    assert missing == []


def _nullable(prop: dict) -> bool:
    return any(option.get('type') == 'null' for option in prop.get('anyOf', []))


def test_an_example_is_null_only_where_its_field_is_nullable():
    """A required field an example leaves out comes back as null, which suits only a nullable field."""
    wrong = sorted(
        f'{name}.{field}'
        for name, schema in _SCHEMAS.items()
        for example in schema.get('examples', [])
        for field, value in example.items()
        if value is None and not _nullable(schema['properties'][field])
    )
    assert wrong == []


def test_a_validation_error_is_documented_as_the_error_response():
    for operations in app.openapi()['paths'].values():
        for operation in operations.values():
            schema = operation['responses']['422']['content']['application/json']['schema']
            assert schema == {'$ref': '#/components/schemas/ErrorResponse'}
