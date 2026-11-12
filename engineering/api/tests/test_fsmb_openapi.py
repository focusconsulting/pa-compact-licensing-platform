"""The report models against FSMB's OpenAPI document, vendored in fsmb_openapi.json.

`just fsmb-openapi` refreshes the document; a failure here then says what FSMB changed.
"""

import json
from pathlib import Path
from types import NoneType
from typing import Any, get_args

import pytest
from pydantic import BaseModel

from licensing_api import fsmb

_SPEC = json.loads((Path(__file__).parent / 'fsmb_openapi.json').read_text())
_SCHEMAS: dict[str, Any] = _SPEC['components']['schemas']
_PATH = '/v1/rosters/{customerKey}/members/{fid}/reports/current/data'


def _reachable(name: str, found: list[str]) -> list[str]:
    if name not in found:
        found.append(name)
        for prop in _SCHEMAS[name].get('properties', {}).values():
            for ref in _refs(prop):
                _reachable(ref, found)
    return found


def _refs(prop: dict) -> list[str]:
    if '$ref' in prop:
        return [prop['$ref'].rsplit('/', 1)[-1]]
    nested = [*prop.get('oneOf', []), *([prop['items']] if 'items' in prop else [])]
    return [ref for p in nested for ref in _refs(p)]


_OBJECTS = [n for n in _reachable('Report', []) if 'properties' in _SCHEMAS[n]]


def _model(schema: str) -> type[BaseModel]:
    return getattr(fsmb, f'Fsmb{schema}')


def _spec_shape(prop: dict) -> tuple:
    if 'oneOf' in prop:
        return _spec_shape(next(p for p in prop['oneOf'] if p.get('type') != 'null'))
    if '$ref' in prop:
        return ('ref', prop['$ref'].rsplit('/', 1)[-1])
    types = set(prop['type'] if isinstance(prop['type'], list) else [prop['type']]) - {'null'}
    if 'integer' in types:
        return ('integer',)
    if types == {'array'}:
        return ('array', _spec_shape(prop['items']), prop.get('maxItems'))
    if types == {'string'}:
        lengths = (prop.get('minLength'), prop.get('maxLength'), prop.get('pattern'))
        return ('string', prop.get('format'), *lengths)
    return (types.pop(),)


def _model_shape(prop: dict) -> tuple:
    if 'anyOf' in prop:
        return _model_shape(next(p for p in prop['anyOf'] if p.get('type') != 'null'))
    if '$ref' in prop:
        return ('ref', prop['$ref'].rsplit('/', 1)[-1].removeprefix('Fsmb'))
    if prop['type'] == 'array':
        return ('array', _model_shape(prop['items']), prop.get('maxItems'))
    if prop['type'] == 'string':
        lengths = (prop.get('minLength'), prop.get('maxLength'), prop.get('pattern'))
        return ('string', prop.get('format'), *lengths)
    return (prop['type'],)


def _spec_nullable(prop: dict) -> bool:
    types = prop.get('type', [])
    return 'null' in types or any(p.get('type') == 'null' for p in prop.get('oneOf', []))


def test_every_report_schema_has_a_model():
    missing = [name for name in _OBJECTS if not hasattr(fsmb, f'Fsmb{name}')]

    assert len(_OBJECTS) == 23
    assert missing == []


@pytest.mark.parametrize('schema', _OBJECTS)
def test_a_model_has_exactly_the_documented_fields_and_required_fields(schema):
    model = _model(schema)
    spec = _SCHEMAS[schema]

    assert {f.alias for f in model.model_fields.values()} == set(spec['properties'])
    required = {f.alias for f in model.model_fields.values() if f.is_required()}
    assert required == set(spec.get('required', []))


@pytest.mark.parametrize('schema', _OBJECTS)
def test_a_model_takes_null_exactly_where_the_document_does(schema):
    model = _model(schema)
    spec = _SCHEMAS[schema]['properties']

    for field in model.model_fields.values():
        takes_null = NoneType in get_args(field.annotation) and fsmb._NOT_NULL not in field.metadata
        assert takes_null == _spec_nullable(spec[field.alias]), field.alias


@pytest.mark.parametrize('schema', _OBJECTS)
def test_a_model_has_the_documented_types_and_constraints(schema):
    model = _model(schema)
    spec = _SCHEMAS[schema]['properties']
    properties = model.model_json_schema(by_alias=True)['properties']

    for alias, prop in spec.items():
        assert _model_shape(properties[alias]) == _spec_shape(prop), alias


def test_board_action_status_has_the_documented_values():
    assert [s.value for s in fsmb.BoardActionStatus] == _SCHEMAS['BoardActionStatus']['enum']


def test_the_client_handles_every_documented_response():
    documented = set(_SPEC['paths'][_PATH]['get']['responses'])

    assert documented == {'200', '204', '400', '401', '404'}


_MOCK_REPORTS = sorted(
    (Path(__file__).parents[2] / 'mocks' / 'fsmb' / 'mappings').glob('report-*.json')
)


@pytest.mark.parametrize('stub', _MOCK_REPORTS, ids=[p.stem for p in _MOCK_REPORTS])
def test_every_report_the_mock_serves_follows_the_document(stub):
    response = json.loads(stub.read_text())['response']

    if response['status'] == 200:
        fsmb.FsmbReport.model_validate(response['jsonBody'])
