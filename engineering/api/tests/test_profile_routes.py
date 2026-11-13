"""The PA's own profile: what the application's first step reads and saves (SCRUM-107, part 1)."""

from datetime import date, datetime, timezone

import pytest
from sqlmodel import col, select

from licensing_api.repo.domain_event import DomainEvent, EventType
from licensing_api.repo.history import PractitionerHistory, PractitionerOtherNameHistory
from licensing_api.repo.practitioner import Practitioner, PractitionerOtherName
from licensing_api.repo.user import User
from tests.factories import make_practitioner, make_user

_ME = '/api/me/profile'
_RESIDENCE = {
    'line1': '100 Sample Street',
    'city': 'Sample City',
    'region': 'KS',
    'postal_code': '66601',
    'country_code': 'US',
}


@pytest.fixture
def pa(client, route_db_session):
    async def _make():
        practitioner = await make_practitioner(
            route_db_session,
            legal_first_name='Jordan',
            legal_last_name='Sample',
            residence_verified_by_state='KS',
            residence_verified_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        user = await route_db_session.get(User, practitioner.user_id)
        return user.email, practitioner

    return client.portal.call(_make)


def _read(client, coroutine_function):
    return client.portal.call(coroutine_function)


def _practitioner(client, session, practitioner_id) -> Practitioner:
    async def _get():
        session.expunge_all()
        return await session.get(Practitioner, practitioner_id)

    return _read(client, _get)


def _events(client, session, practitioner_id) -> list[str]:
    async def _get():
        statement = select(DomainEvent.type).where(
            col(DomainEvent.aggregate_type) == 'practitioners',
            col(DomainEvent.aggregate_id) == practitioner_id,
        )
        return list((await session.scalars(statement)).all())

    return _read(client, _get)


def test_a_new_pa_s_profile_has_only_their_registered_name(client, auth_header, pa):
    email, _ = pa

    response = client.get(_ME, headers=auth_header(email))

    assert response.json()['data'] == {
        'legal_first_name': 'Jordan',
        'legal_last_name': 'Sample',
        'date_of_birth': '1990-01-01',
        'residence': None,
        'nccpa_certification_number': None,
        'other_names': [],
        'verified_fields': [],
    }


def test_saving_the_first_step_records_who_entered_each_group(
    client, auth_header, route_db_session, pa
):
    email, practitioner = pa

    response = client.patch(
        _ME,
        json={
            'date_of_birth': '1988-03-14',
            'residence': _RESIDENCE,
            'nccpa_certification_number': ' 1234567 ',
            'other_names': [{'first_name': 'Jordan', 'last_name': 'Smith'}],
        },
        headers=auth_header(email),
    )

    data = response.json()['data']
    assert data['residence'] == {**_RESIDENCE, 'line2': None}
    assert data['nccpa_certification_number'] == '1234567'
    assert data['other_names'] == [
        {'first_name': 'Jordan', 'middle_name': None, 'last_name': 'Smith', 'name_suffix': None}
    ]
    row = _practitioner(client, route_db_session, practitioner.id)
    assert row.date_of_birth == date(1988, 3, 14)
    entered = {row.identity_entered_by, row.residence_entered_by, row.certification_entered_by}
    assert entered == {practitioner.user_id}
    assert row.residence_verified_by_state == 'KS'
    assert _events(client, route_db_session, practitioner.id) == [
        EventType.PRACTITIONER_PROFILE_CHANGED
    ]


def test_a_group_left_alone_keeps_who_entered_it(client, auth_header, route_db_session, pa):
    email, practitioner = pa

    client.patch(_ME, json={'nccpa_certification_number': '1234567'}, headers=auth_header(email))

    row = _practitioner(client, route_db_session, practitioner.id)
    assert (row.certification_entered_by, row.residence_entered_by, row.identity_entered_by) == (
        practitioner.user_id,
        None,
        None,
    )


def test_saving_what_is_already_there_records_nothing(client, auth_header, route_db_session, pa):
    email, practitioner = pa
    body = {'residence': _RESIDENCE, 'other_names': [{'last_name': 'Smith'}]}
    client.patch(_ME, json=body, headers=auth_header(email))

    client.patch(_ME, json=body, headers=auth_header(email))

    assert len(_events(client, route_db_session, practitioner.id)) == 1


def test_a_name_no_longer_listed_is_removed_and_its_history_kept(
    client, auth_header, route_db_session, pa
):
    email, practitioner = pa
    client.patch(_ME, json={'other_names': [{'last_name': 'Smith'}]}, headers=auth_header(email))

    response = client.patch(
        _ME, json={'other_names': [{'last_name': 'Jones'}]}, headers=auth_header(email)
    )

    assert [n['last_name'] for n in response.json()['data']['other_names']] == ['Jones']

    async def _rows():
        names = (
            await route_db_session.scalars(
                select(PractitionerOtherName).where(
                    col(PractitionerOtherName.practitioner_id) == practitioner.id
                )
            )
        ).all()
        histories = (
            await route_db_session.scalars(
                select(PractitionerOtherNameHistory).where(
                    col(PractitionerOtherNameHistory.entity_id).in_([n.id for n in names])
                )
            )
        ).all()
        return names, histories

    names, histories = _read(client, _rows)
    assert {(n.last_name, n.removed_at is not None) for n in names} == {
        ('Smith', True),
        ('Jones', False),
    }
    assert len(histories) == 3


def test_only_a_name_change_still_records_a_profile_change(
    client, auth_header, route_db_session, pa
):
    email, practitioner = pa

    client.patch(_ME, json={'other_names': [{'last_name': 'Smith'}]}, headers=auth_header(email))

    async def _history():
        statement = select(PractitionerHistory).where(
            col(PractitionerHistory.entity_id) == practitioner.id
        )
        return (await route_db_session.scalars(statement)).all()

    [history] = _read(client, _history)
    assert set(history.updated) == {'identity_entered_by'}
    assert _events(client, route_db_session, practitioner.id) == [
        EventType.PRACTITIONER_PROFILE_CHANGED
    ]


def test_a_partial_address_entered_elsewhere_is_still_shown(client, auth_header, route_db_session):
    async def _make():
        practitioner = await make_practitioner(route_db_session, residence_line1='1 Main Street')
        return (await route_db_session.get(User, practitioner.user_id)).email

    email = _read(client, _make)

    residence = client.get(_ME, headers=auth_header(email)).json()['data']['residence']

    assert residence['line1'] == '1 Main Street'
    assert residence['city'] is None


@pytest.mark.parametrize(
    'body',
    [
        {'residence': {**_RESIDENCE, 'country_code': 'usa'}},
        {'residence': {**_RESIDENCE, 'city': '  '}},
        {'other_names': [{'first_name': 'Jordan'}]},
        {'legal_last_name': 'Changed'},
    ],
)
def test_a_profile_change_is_validated(client, auth_header, pa, body):
    email, _ = pa

    assert client.patch(_ME, json=body, headers=auth_header(email)).status_code == 422


def test_a_user_with_no_practitioner_record_has_no_profile(client, auth_header, route_db_session):
    email = _read(client, lambda: make_user(route_db_session, role='licensee')).email

    assert client.get(_ME, headers=auth_header(email)).status_code == 404


@pytest.fixture
def verified_pa(client, route_db_session):
    """A PA whose state has verified their identity and certification."""

    async def _make():
        verified = datetime(2026, 10, 20, tzinfo=timezone.utc)
        practitioner = await make_practitioner(
            route_db_session,
            date_of_birth=date(1988, 3, 14),
            nccpa_certification_number='1234567',
            identity_verified_by_state='KS',
            identity_verified_at=verified,
            certification_verified_by_state='KS',
            certification_verified_at=verified,
        )
        route_db_session.add(
            PractitionerOtherName(
                practitioner_id=practitioner.id,
                last_name='Smith',
                created_by=practitioner.created_by,
            )
        )
        await route_db_session.flush()
        return (await route_db_session.get(User, practitioner.user_id)).email, practitioner

    return client.portal.call(_make)


def test_the_profile_lists_what_the_state_verified(client, auth_header, verified_pa):
    email, _ = verified_pa

    response = client.get(_ME, headers=auth_header(email))

    assert response.json()['data']['verified_fields'] == ['nccpa_certification_number']


def test_only_the_state_changes_the_nccpa_number_it_verified(
    client, auth_header, route_db_session, verified_pa
):
    email, practitioner = verified_pa

    response = client.patch(
        _ME, json={'nccpa_certification_number': '7654321'}, headers=auth_header(email)
    )

    assert (response.status_code, response.json()) == (
        409,
        {'code': 'VERIFIED_BY_STATE', 'details': ['nccpa_certification_number']},
    )
    assert _events(client, route_db_session, practitioner.id) == []


def test_a_verified_pa_still_changes_their_date_of_birth_and_other_names(
    client, auth_header, verified_pa
):
    email, _ = verified_pa

    response = client.patch(
        _ME,
        json={'date_of_birth': '1988-03-15', 'other_names': [{'last_name': 'Jones'}]},
        headers=auth_header(email),
    )

    assert response.status_code == 200
    data = response.json()['data']
    assert (data['date_of_birth'], [n['last_name'] for n in data['other_names']]) == (
        '1988-03-15',
        ['Jones'],
    )


def test_sending_what_the_state_verified_unchanged_is_fine(
    client, auth_header, route_db_session, verified_pa
):
    email, practitioner = verified_pa

    response = client.patch(
        _ME,
        json={
            'date_of_birth': '1988-03-14',
            'nccpa_certification_number': '1234567',
            'other_names': [{'last_name': 'Smith'}],
            'residence': _RESIDENCE,
        },
        headers=auth_header(email),
    )

    assert response.status_code == 200
    assert _events(client, route_db_session, practitioner.id) == [
        EventType.PRACTITIONER_PROFILE_CHANGED
    ]
