import uuid

import pytest

from licensing_api.__main__ import app
from licensing_api.errors import ErrorCode
from licensing_api.repo.user import get_user_by_email
from licensing_api.routes.user import CurrentUser
from tests.factories import make_user


def _email() -> str:
    # Unique, so tests never collide with each other or with `just seed` users.
    return f'{uuid.uuid4().hex}@example.com'


def test_me_returns_active_user(client, auth_header, route_db_session):
    email = _email()
    client.portal.call(
        lambda: make_user(
            route_db_session, email=email, given_name='Gustavo', family_name='Torrico', role='admin'
        )
    )

    response = client.get('/api/me', headers=auth_header(email))

    assert response.status_code == 200
    user = CurrentUser.model_validate(response.json()['data'])
    assert user.email == email
    assert user.given_name == 'Gustavo'
    assert user.family_name == 'Torrico'
    assert user.role == 'admin'
    assert user.is_active is True


def test_me_unknown_email_returns_403(client, auth_header):
    response = client.get('/api/me', headers=auth_header(_email()))

    assert response.status_code == 403
    body = response.json()
    assert body['code'] == ErrorCode.UserNotFound
    assert 'User not found' in body['details']


def test_me_backfills_public_id_on_first_login(client, auth_header, route_db_session):
    email = _email()
    client.portal.call(lambda: make_user(route_db_session, email=email))

    response = client.get('/api/me', headers=auth_header(email))

    assert response.status_code == 200
    assert response.json()['data']['user_id'] is not None


def test_route_writes_are_rolled_back(client, auth_header, route_db_session):
    email = _email()
    client.portal.call(lambda: make_user(route_db_session, email=email))
    client.get('/api/me', headers=auth_header(email))

    async def _public_id_seen_by(session):
        user = await get_user_by_email(session, email)
        return None if user is None else user.public_id

    async def _public_id_seen_outside():
        async with app.state.session_factory() as session:
            return await _public_id_seen_by(session)

    # The route committed inside the test's transaction: visible there, not outside it.
    assert client.portal.call(_public_id_seen_by, route_db_session) is not None
    assert client.portal.call(_public_id_seen_outside) is None


def test_me_inactive_user_returns_403(client, auth_header, route_db_session):
    email = _email()
    client.portal.call(lambda: make_user(route_db_session, email=email, is_active=False))

    response = client.get('/api/me', headers=auth_header(email))

    assert response.status_code == 403
    body = response.json()
    assert body['code'] == ErrorCode.UserInactive
    assert 'User is inactive' in body['details']


@pytest.mark.parametrize(
    ('overrides', 'expected'),
    [
        ({'role': 'licensee'}, ['manage_own_record']),
        (
            {
                'role': 'state_staff',
                'state_code': 'KS',
                'permissions': {
                    'KS': ['write', 'read_private', 'not_a_permission'],
                    'MO': ['admin'],
                },
            },
            ['read_general', 'read_private', 'write'],
        ),
        ({'role': 'compact_admin'}, ['read_general', 'compact_admin', 'read_private']),
    ],
)
def test_me_returns_permissions_held_in_own_state(
    client, auth_header, route_db_session, overrides, expected
):
    email = _email()
    client.portal.call(lambda: make_user(route_db_session, email=email, **overrides))

    response = client.get('/api/me', headers=auth_header(email))

    assert response.status_code == 200
    assert response.json()['data']['permissions'] == expected
