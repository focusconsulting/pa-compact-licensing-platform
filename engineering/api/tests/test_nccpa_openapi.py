"""The NCCPA model and request against NCCPA's OpenAPI document, vendored in nccpa_openapi.json.

`just nccpa-openapi` refreshes the document; a failure here then says what NCCPA changed. Where real
responses differ from the document, the model follows them and DEVIATIONS records why.
"""

import json
import re
from pathlib import Path
from types import NoneType
from typing import Any, get_args

import pytest

from licensing_api import nccpa

_SPEC = json.loads((Path(__file__).parent / 'nccpa_openapi.json').read_text())
_SCHEMAS: dict[str, Any] = _SPEC['components']['schemas']
_OPERATION = _SPEC['paths'][nccpa.STATUS_PATH]['post']
_RESPONSE = _SCHEMAS['CertificationStatusResponse']
_MODEL = nccpa.NccpaCertificationStatusResponse

# property -> the evidence that real NCCPA responses differ from the document there, such as
# "sandbox, PA ID n, 2027-01-10: lastName was absent". Each entry frees only that property.
DEVIATIONS: dict[str, str] = {}

_FIELDS = {f.alias: f for f in _MODEL.model_fields.values() if f.alias not in DEVIATIONS}


def _spec_shape(prop: dict) -> tuple:
    return (prop['type'], prop.get('format'))


def _model_shape(prop: dict) -> tuple:
    prop = next(p for p in prop.get('anyOf', [prop]) if p.get('type') != 'null')
    if '$ref' in prop:
        return ('enum',)
    if (prop.get('minimum'), prop.get('maximum')) == (-(2**31), 2**31 - 1):
        return (prop['type'], 'int32')
    return (prop['type'], prop.get('format'))


def test_the_lookup_sends_only_the_documented_id():
    request = _SCHEMAS['PaSearchModel']

    assert request['properties'].keys() == {'id'} and request['required'] == ['id']
    assert request['additionalProperties'] is False
    assert request['properties']['id']['type'] == 'string'
    assert 'application/json' in _OPERATION['requestBody']['content']


def test_the_response_is_the_documented_schema():
    content = _OPERATION['responses']['200']['content']['application/json']['schema']

    assert content['$ref'].rsplit('/', 1)[-1] == 'CertificationStatusResponse'
    assert _RESPONSE['additionalProperties'] is False
    assert _MODEL.model_config.get('extra') == 'forbid'


def test_the_model_has_exactly_the_documented_fields_and_none_required():
    documented = set(_RESPONSE['properties']) - DEVIATIONS.keys()

    assert set(_FIELDS) == documented
    assert [a for a, f in _FIELDS.items() if f.is_required()] == _RESPONSE.get('required', [])


def test_the_model_takes_null_exactly_where_the_document_does():
    for alias, field in _FIELDS.items():
        takes_null = (
            NoneType in get_args(field.annotation) and nccpa._NOT_NULL not in field.metadata
        )
        assert takes_null == _RESPONSE['properties'][alias].get('nullable', False), alias


def test_the_model_has_the_documented_types():
    properties = _MODEL.model_json_schema(by_alias=True)['properties']

    for alias in _FIELDS:
        spec = _RESPONSE['properties'][alias]
        expected = ('enum',) if alias == 'certificationStatus' else _spec_shape(spec)
        assert _model_shape(properties[alias]) == expected, alias


def test_certification_status_has_the_values_the_document_describes():
    # The schema types it as a plain string; the 200 description lists the values in quotes.
    described = re.findall(r'"([^"]+)"', _OPERATION['responses']['200']['description'])

    assert _RESPONSE['properties']['certificationStatus']['type'] == 'string'
    assert [s.value for s in nccpa.CertificationStatus] == described


def test_the_documented_responses_are_the_ones_the_client_expects():
    # 401 and 404 are not documented: NCCPA's security page describes the 401, and 404 for an unknown
    # PA is an assumption to confirm with NCCPA (docs/nccpa.md).
    assert set(_OPERATION['responses']) == {'200', '429', '503'}


_MOCK_STUBS = sorted(
    (Path(__file__).parents[2] / 'mocks' / 'nccpa' / 'mappings').glob('status-*.json')
)


def _rendered(response: dict) -> dict:
    if 'jsonBody' in response:
        return response['jsonBody']
    # A templated stub echoes the requested PA ID into paId.
    return json.loads(re.sub(r'\{\{jsonPath request\.body [^}]+\}\}', '1234560', response['body']))


@pytest.mark.parametrize('stub', _MOCK_STUBS, ids=[p.stem for p in _MOCK_STUBS])
def test_every_status_the_mock_serves_follows_the_document(stub):
    response = json.loads(stub.read_text())['response']

    if response['status'] == 200:
        _MODEL.model_validate(_rendered(response))
