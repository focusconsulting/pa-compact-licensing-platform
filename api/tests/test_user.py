import uuid

from jose import jwt as jose_jwt

from licensing_api.auth import CurrentUser
from licensing_api.errors import ErrorCode

_TEST_CLIENT_ID = 'test-client-id'
_TEST_KID = 'test-key-1'


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


def test_me_unknown_signing_key_returns_401(client, _private_key):
    token = jose_jwt.encode(
        {
            'sub': str(uuid.uuid4()),
            'email': 'test@example.com',
            'token_use': 'id',
            'aud': _TEST_CLIENT_ID,
        },
        _private_key,
        algorithm='RS256',
        headers={'kid': 'unknown-kid'},
    )
    response = client.get('/api/me', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 401
    body = response.json()
    assert body['code'] == ErrorCode.InvalidToken
    assert 'Unknown signing key' in body['details']


def test_me_wrong_token_use_returns_401(client, _private_key):
    token = jose_jwt.encode(
        {
            'sub': str(uuid.uuid4()),
            'email': 'test@example.com',
            'token_use': 'access',
            'aud': _TEST_CLIENT_ID,
        },
        _private_key,
        algorithm='RS256',
        headers={'kid': _TEST_KID},
    )
    response = client.get('/api/me', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 401
    body = response.json()
    assert body['code'] == ErrorCode.InvalidToken
    assert 'Expected Cognito ID token' in body['details']
