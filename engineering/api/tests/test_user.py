from licensing_api.__main__ import app
from licensing_api.errors import ErrorCode
from licensing_api.repo.user import get_user_by_email
from licensing_api.routes.user import CurrentUser

_BACKFILL_EMAIL = 'backfill@example.com'


def test_me_returns_active_user(client, auth_header):
    response = client.get('/api/me', headers=auth_header('gustavo.torrico@focusconsulting.io'))

    assert response.status_code == 200
    user = CurrentUser.model_validate(response.json())
    assert user.email == 'gustavo.torrico@focusconsulting.io'
    assert user.given_name == 'Gustavo'
    assert user.family_name == 'Torrico'
    assert user.role == 'admin'
    assert user.is_active is True


def test_me_unknown_email_returns_403(client, auth_header):
    response = client.get('/api/me', headers=auth_header('nobody@example.com'))

    assert response.status_code == 403
    body = response.json()
    assert body['code'] == ErrorCode.UserNotFound
    assert 'User not found' in body['details']


def test_me_backfills_public_id_on_first_login(client, auth_header, route_db_session):
    response = client.get('/api/me', headers=auth_header(_BACKFILL_EMAIL))

    assert response.status_code == 200
    assert response.json()['user_id'] is not None


def test_route_writes_are_rolled_back(client, auth_header, route_db_session):
    client.get('/api/me', headers=auth_header(_BACKFILL_EMAIL))

    async def _public_id_seen_by(session):
        user = await get_user_by_email(session, _BACKFILL_EMAIL)
        assert user is not None
        return user.public_id

    async def _public_id_seen_outside():
        async with app.state.session_factory() as session:
            return await _public_id_seen_by(session)

    # The route committed inside the test's transaction: visible there, not outside it.
    assert client.portal.call(_public_id_seen_by, route_db_session) is not None
    assert client.portal.call(_public_id_seen_outside) is None


def test_me_inactive_user_returns_403(client, auth_header):
    response = client.get('/api/me', headers=auth_header('inactive@example.com'))

    assert response.status_code == 403
    body = response.json()
    assert body['code'] == ErrorCode.UserInactive
    assert 'User is inactive' in body['details']
