from licensing_api.auth import CurrentUser
from licensing_api.errors import ErrorCode


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


def test_me_inactive_user_returns_403(client, auth_header):
    response = client.get('/api/me', headers=auth_header('inactive@example.com'))

    assert response.status_code == 403
    body = response.json()
    assert body['code'] == ErrorCode.UserInactive
    assert 'User is inactive' in body['details']


def test_me_invalid_token_returns_401(client):
    # A structurally invalid JWT fails before JWKS is even consulted —
    # jose raises JWTError at header parsing, which becomes INVALID_TOKEN / 401.
    response = client.get('/api/me', headers={'Authorization': 'Bearer not.a.valid.jwt'})

    assert response.status_code == 401
    body = response.json()
    assert body['code'] == ErrorCode.InvalidToken
    assert len(body['details']) > 0
