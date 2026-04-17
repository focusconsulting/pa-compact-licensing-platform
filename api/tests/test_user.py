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


async def test_me_backfills_public_id_on_first_login(client, auth_header):
    try:
        response = client.get('/api/me', headers=auth_header(_BACKFILL_EMAIL))

        assert response.status_code == 200
        body = response.json()
        assert body['user_id'] is not None
    finally:

        async def _reset():
            async with app.state.session_factory() as session:
                user = await get_user_by_email(session, _BACKFILL_EMAIL)
                if user:
                    user.public_id = None
                    await session.commit()

        client.portal.call(_reset)


def test_me_inactive_user_returns_403(client, auth_header):
    response = client.get('/api/me', headers=auth_header('inactive@example.com'))

    assert response.status_code == 403
    body = response.json()
    assert body['code'] == ErrorCode.UserInactive
    assert 'User is inactive' in body['details']
