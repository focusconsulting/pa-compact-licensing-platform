"""GET /api/public/privilege-holders: anyone confirms a PA's compact privileges, and learns nothing else."""

import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any

import pytest

from licensing_api import days
from licensing_api.repo.adverse_action import AdverseActionTarget
from licensing_api.repo.participation_application import ParticipationApplication
from licensing_api.repo.practitioner import Practitioner
from licensing_api.repo.privilege import AdministratorStatus, DeactivationReason, Privilege
from licensing_api.repo.qualifying_license import QualifyingLicense
from licensing_api.routes.public_verification import (
    PrivilegeHolder,
    PrivilegeHolderSummary,
    PublicPrivilege,
    StateRef,
)
from scripts.export_openapi import document
from tests.factories import (
    make_adverse_action,
    make_eligible_application,
    make_practitioner,
    make_privilege,
    make_submitted_request,
)

_URL = '/api/public/privilege-holders'
_KANSAS = {'code': 'KS', 'name': 'Kansas'}
_OKLAHOMA = {'code': 'OK', 'name': 'Oklahoma'}
_DEACTIVATED: dict[str, Any] = {
    'administrator_status': AdministratorStatus.INACTIVE,
    'deactivation_reason': DeactivationReason.QUALIFYING_LICENSE_ADVERSE_ACTION,
    'deactivated_at': datetime(2026, 8, 1, tzinfo=timezone.utc),
    'deactivation_note': 'Markernote from the state',
}


def _surname() -> str:
    """A last name no other test or seed row has, so a search finds only this test's rows."""
    return f'Verify{uuid.uuid4().hex[:10]}'


def _number(state: str = 'OK') -> str:
    return f'PA-{state}-{uuid.uuid4().int % 10**9:09d}'


async def _privilege(
    session, application: ParticipationApplication, state: str = 'OK', **overrides: Any
) -> Privilege:
    snapshot = overrides.get('expires_on', date(2027, 12, 31))
    request = await make_submitted_request(
        session, application, remote_state_code=state, ql_expires_on_snapshot=snapshot
    )
    return await make_privilege(session, request, privilege_number=_number(state), **overrides)


async def _holder(
    session, *, first: str = 'Avery', last: str | None = None, **privilege: Any
) -> tuple[Practitioner, ParticipationApplication, Privilege]:
    """A practitioner whose state of qualifying license is Kansas, holding one Oklahoma privilege."""
    practitioner = await make_practitioner(
        session,
        legal_first_name=first,
        legal_last_name=last or _surname(),
        current_sql_state_code='KS',
    )
    application = await make_eligible_application(session, practitioner)
    return practitioner, application, await _privilege(session, application, **privilege)


def _search(client, **params: Any) -> list[dict[str, Any]]:
    response = client.get(_URL, params=params)
    assert response.status_code == 200, response.text
    return response.json()['data']


def _detail(client, practitioner: Practitioner) -> dict[str, Any]:
    response = client.get(f'{_URL}/{practitioner.public_id}')
    assert response.status_code == 200, response.text
    return response.json()['data']


def _only_privilege(client, practitioner: Practitioner) -> dict[str, Any]:
    (privilege,) = _detail(client, practitioner)['privileges']
    return privilege


def test_anyone_finds_a_holder_by_name_without_signing_in(client, route_db_session):
    practitioner, _, _ = client.portal.call(_holder, route_db_session)

    response = client.get(
        _URL, params={'first_name': 'Avery', 'last_name': practitioner.legal_last_name}
    )

    assert response.status_code == 200
    assert response.json() == {
        'data': [
            {
                'id': str(practitioner.public_id),
                'first_name': 'Avery',
                'last_name': practitioner.legal_last_name,
                'name_suffix': None,
                'state_of_qualifying_license': _KANSAS,
                'privilege_states': [_OKLAHOMA],
            }
        ],
        'page': {'number': 1, 'size': 25, 'total': 1},
    }


def test_a_holders_page_lists_each_privilege_with_its_status_and_dates(client, route_db_session):
    practitioner, _, privilege = client.portal.call(_holder, route_db_session)

    assert _detail(client, practitioner) == {
        'id': str(practitioner.public_id),
        'first_name': 'Avery',
        'last_name': practitioner.legal_last_name,
        'name_suffix': None,
        'state_of_qualifying_license': _KANSAS,
        'privileges': [
            {
                'state': _OKLAHOMA,
                'number': privilege.privilege_number,
                'status': 'active',
                'issued_on': '2026-06-02',
                'expires_on': '2027-12-31',
            }
        ],
    }


@pytest.mark.parametrize(
    ('model', 'fields'),
    [
        (StateRef, {'code', 'name'}),
        (PublicPrivilege, {'state', 'number', 'status', 'issued_on', 'expires_on'}),
        (
            PrivilegeHolderSummary,
            {
                'id',
                'first_name',
                'last_name',
                'name_suffix',
                'state_of_qualifying_license',
                'privilege_states',
            },
        ),
        (
            PrivilegeHolder,
            {
                'id',
                'first_name',
                'last_name',
                'name_suffix',
                'state_of_qualifying_license',
                'privileges',
            },
        ),
    ],
    ids=lambda value: getattr(value, '__name__', ''),
)
def test_a_public_model_holds_exactly_the_allow_list(model, fields):
    """Adding a field here means changing FLOW-08 (product/context/flows/08-public-verification.md) first."""
    assert set(model.model_fields) == fields
    assert model.model_config['extra'] == 'forbid'


def _reachable(schema: Any, schemas: dict[str, Any], found: set[str]) -> set[str]:
    """Every component schema a schema names, through properties, lists, and unions."""
    if isinstance(schema, dict):
        if '$ref' in schema:
            name = schema['$ref'].rsplit('/', 1)[1]
            if name not in found:
                found.add(name)
                _reachable(schemas[name], schemas, found)
        for value in schema.values():
            _reachable(value, schemas, found)
    elif isinstance(schema, list):
        for value in schema:
            _reachable(value, schemas, found)
    return found


def test_the_documented_public_responses_hold_only_allow_list_models():
    openapi = document()
    schemas = openapi['components']['schemas']
    bodies = [
        response['content']['application/json']['schema']
        for path, operations in openapi['paths'].items()
        if path.startswith('/api/public/privilege-holders')
        for operation in operations.values()
        for status, response in operation['responses'].items()
        if status.startswith('2')
    ]

    names = _reachable(bodies, schemas, set())

    allow_list = {'StateRef', 'PublicPrivilege', 'PrivilegeHolderSummary', 'PrivilegeHolder'}
    assert {n for n in names if not n.startswith(('Data_', 'Paged_'))} == allow_list | {
        'Page',
        'PublicPrivilegeStatus',
    }
    assert all(schemas[name]['additionalProperties'] is False for name in allow_list)
    assert schemas['PublicPrivilegeStatus']['enum'] == ['active', 'expired', 'inactive']


async def _holder_with_private_data(session) -> tuple[Practitioner, list[str]]:
    """A holder with every private field set to a value a response must never contain."""
    practitioner = await make_practitioner(
        session,
        legal_first_name='Avery',
        legal_middle_name='Markermiddle',
        legal_last_name=_surname(),
        current_sql_state_code='KS',
        date_of_birth=date(1961, 2, 3),
        npi='1961020399',
        phone='555-0142-777',
        correspondence_email='marker-private@example.com',
        residence_line1='77 Marker Street',
        residence_city='Markerville',
        pa_program_name='Marker University',
        nccpa_certification_number='MARKER-NCCPA',
    )
    application = await make_eligible_application(session, practitioner)
    privilege = await _privilege(session, application, **_DEACTIVATED)
    license = await session.get(QualifyingLicense, application.qualifying_license_id)
    await make_adverse_action(
        session,
        privilege,
        against=AdverseActionTarget.QUALIFYING_LICENSE,
        privilege_id=None,
        qualifying_license_id=license.id,
        reporting_state_code='KS',
        summary='Markersummary of the order',
    )
    return practitioner, [
        'Markermiddle',
        '1961-02-03',
        '1961020399',
        '555-0142-777',
        'marker-private@example.com',
        '77 Marker Street',
        'Markerville',
        'Marker University',
        'MARKER-NCCPA',
        'Markernote',
        'Markersummary',
        license.license_number,
        'suspension',
        'reason',
        'adverse',
        *DeactivationReason,
    ]


def test_no_private_field_reaches_a_public_response(client, route_db_session):
    practitioner, private = client.portal.call(_holder_with_private_data, route_db_session)

    search = client.get(
        _URL, params={'first_name': 'Avery', 'last_name': practitioner.legal_last_name}
    )
    detail = client.get(f'{_URL}/{practitioner.public_id}')

    assert search.status_code == detail.status_code == 200
    assert [value for value in private if value in search.text + detail.text] == []


def test_a_privilege_deactivated_by_a_non_public_action_is_inactive_with_no_reason(
    client, route_db_session
):
    practitioner, _ = client.portal.call(_holder_with_private_data, route_db_session)

    privilege = _only_privilege(client, practitioner)

    assert privilege['status'] == 'inactive'
    assert set(privilege) == {'state', 'number', 'status', 'issued_on', 'expires_on'}


async def _expiring(session, days_from_today: int) -> Practitioner:
    today = await days.compact_today(session)
    practitioner, _, _ = await _holder(session, expires_on=days.add_days(today, days_from_today))
    return practitioner


@pytest.mark.parametrize(('days_from_today', 'status'), [(0, 'active'), (-1, 'expired')])
def test_a_privilege_is_active_through_its_expiry_date_and_expired_the_day_after(
    client, route_db_session, days_from_today, status
):
    practitioner = client.portal.call(_expiring, route_db_session, days_from_today)

    assert _only_privilege(client, practitioner)['status'] == status


async def _encumbered(session, *, is_public: bool) -> Practitioner:
    practitioner, _, privilege = await _holder(session)
    await make_adverse_action(session, privilege, is_public=is_public)
    return practitioner


def test_an_encumbered_privilege_is_inactive_whether_or_not_its_action_is_public(
    client, route_db_session
):
    sealed = client.portal.call(lambda: _encumbered(route_db_session, is_public=False))
    public = client.portal.call(lambda: _encumbered(route_db_session, is_public=True))

    shown = [_only_privilege(client, practitioner) for practitioner in (sealed, public)]

    assert [privilege['status'] for privilege in shown] == ['inactive', 'inactive']
    assert shown[0] | {'number': None} == shown[1] | {'number': None}


async def _issued_at(session, instant: datetime) -> Practitioner:
    practitioner, _, _ = await _holder(session, issued_at=instant)
    return practitioner


@pytest.mark.parametrize(
    ('issued_at', 'issued_on'),
    [
        # 23:30 and 00:30 in New York, the reference time zone (ADR-0006); both are 3 June in UTC.
        (datetime(2026, 6, 3, 3, 30, tzinfo=timezone.utc), '2026-06-02'),
        (datetime(2026, 6, 3, 4, 30, tzinfo=timezone.utc), '2026-06-03'),
    ],
)
def test_the_issue_date_is_the_day_in_the_reference_time_zone(
    client, route_db_session, issued_at, issued_on
):
    practitioner = client.portal.call(_issued_at, route_db_session, issued_at)

    assert _only_privilege(client, practitioner)['issued_on'] == issued_on


def test_names_match_in_full_ignoring_case_and_surrounding_spaces(client, route_db_session):
    practitioner, _, _ = client.portal.call(_holder, route_db_session)
    last = practitioner.legal_last_name

    assert len(_search(client, first_name=' aVeRy ', last_name=f' {last.upper()} ')) == 1
    assert _search(client, first_name='Aver', last_name=last) == []
    assert _search(client, first_name='Avery', last_name=last[:-1]) == []


async def _without_a_privilege(session) -> Practitioner:
    practitioner = await make_practitioner(
        session, legal_first_name='Avery', legal_last_name=_surname(), current_sql_state_code='KS'
    )
    await make_eligible_application(session, practitioner)
    return practitioner


def test_a_pa_with_no_privilege_is_never_found(client, route_db_session):
    practitioner = client.portal.call(_without_a_privilege, route_db_session)

    assert _search(client, first_name='Avery', last_name=practitioner.legal_last_name) == []
    unknown = client.get(f'{_URL}/{uuid.uuid4()}')
    without = client.get(f'{_URL}/{practitioner.public_id}')
    assert unknown.status_code == without.status_code == 404
    assert (
        unknown.json()
        == without.json()
        == {
            'code': 'NOT_FOUND',
            'details': ['No such privilege holder'],
        }
    )


async def _without_a_state_of_qualifying_license(session) -> Privilege:
    practitioner = await make_practitioner(session, legal_last_name=_surname())
    application = await make_eligible_application(session, practitioner)
    return await _privilege(session, application)


def test_a_record_with_no_state_of_qualifying_license_is_not_published(client, route_db_session):
    privilege = client.portal.call(_without_a_state_of_qualifying_license, route_db_session)

    assert _search(client, privilege_number=privilege.privilege_number) == []


async def _namesakes(session) -> str:
    last = _surname()
    await _holder(session, last=last)
    await _holder(session, last=last)
    return last


def test_pas_who_share_a_name_all_appear_in_one_order_across_pages(client, route_db_session):
    last = client.portal.call(_namesakes, route_db_session)
    name = {'first_name': 'Avery', 'last_name': last}

    both = [holder['id'] for holder in _search(client, **name)]
    paged = [_search(client, **name, page=page, page_size=1)[0]['id'] for page in (1, 2)]

    assert len(set(both)) == 2
    assert paged == both


def test_a_privilege_number_finds_its_holder_in_either_case(client, route_db_session):
    practitioner, _, privilege = client.portal.call(_holder, route_db_session)

    for number in (privilege.privilege_number, privilege.privilege_number.lower()):
        assert [holder['id'] for holder in _search(client, privilege_number=number)] == [
            str(practitioner.public_id)
        ]
    assert _search(client, privilege_number='PA-OK-000000000') == []


async def _holder_in_three(session) -> Practitioner:
    """Oklahoma twice, as after an expiry and a new application, and Missouri once."""
    practitioner, application, _ = await _holder(session, expires_on=date(2026, 1, 31))
    await _privilege(session, application, 'OK')
    await _privilege(session, application, 'MO')
    return practitioner


def test_a_holders_states_are_listed_once_each_by_name(client, route_db_session):
    practitioner = client.portal.call(_holder_in_three, route_db_session)

    (found,) = _search(client, first_name='Avery', last_name=practitioner.legal_last_name)

    assert found['privilege_states'] == [{'code': 'MO', 'name': 'Missouri'}, _OKLAHOMA]
    assert [p['state']['code'] for p in _detail(client, practitioner)['privileges']] == [
        'MO',
        'OK',
        'OK',
    ]


@pytest.mark.parametrize(
    'params',
    [
        {},
        {'last_name': 'Morgan'},
        {'first_name': 'Pat'},
        {'first_name': '  ', 'last_name': 'Morgan'},
        {'first_name': 'Pat', 'last_name': 'Morgan', 'privilege_number': 'PA-OK-000123'},
        {'last_name': 'Morgan', 'privilege_number': 'PA-OK-000123'},
        {'first_name': 'Pat', 'last_name': 'Morgan', 'state': 'OK'},
        {'first_name': 'P' * 101, 'last_name': 'Morgan'},
        {'privilege_number': 'OK-000123'},
        {'privilege_number': 'PA-OK-123'},
    ],
    ids=lambda params: ','.join(params) or 'nothing',
)
def test_a_search_that_is_not_both_names_or_one_number_is_refused(client, params):
    response = client.get(_URL, params=params)

    assert response.status_code == 422
    assert response.json()['code'] == 'VALIDATION_ERROR'


def test_a_malformed_holder_id_is_refused(client):
    response = client.get(f'{_URL}/not-an-id')

    assert response.status_code == 422
    assert response.json()['code'] == 'VALIDATION_ERROR'


def test_a_search_logs_its_mode_and_count_and_never_its_terms(client, route_db_session, caplog):
    practitioner, _, _ = client.portal.call(_holder, route_db_session)
    last = practitioner.legal_last_name

    with caplog.at_level(logging.INFO, logger='licensing_api.routes.public_verification'):
        _search(client, first_name='Avery', last_name=last)

    (record,) = [r for r in caplog.records if r.name == 'licensing_api.routes.public_verification']
    assert (record.mode, record.results) == ('name', 1)
    assert last not in str(record.__dict__)
