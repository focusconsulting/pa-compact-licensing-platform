import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt as jose_jwt

from licensing_api.__main__ import app
from licensing_api.auth import CurrentUser, _get_jwks
from licensing_api.dependencies import get_db_session
from licensing_api.errors import ErrorCode
from licensing_api.repo.user import User

_TEST_CLIENT_ID = 'test-client-id'
_TEST_KID = 'test-key-1'


def _make_user(**kwargs) -> User:
    defaults = {
        'id': 1,
        'email': 'test@example.com',
        'public_id': uuid.uuid4(),
        'given_name': 'Test',
        'family_name': 'User',
        'role': 'viewer',
        'state_code': None,
        'is_active': True,
        'created_by': None,
    }
    defaults.update(kwargs)
    return User(**defaults)


@pytest.fixture(scope='module')
def _valid_token(_private_key) -> str:
    return jose_jwt.encode(
        {
            'sub': str(uuid.uuid4()),
            'email': 'test@example.com',
            'token_use': 'id',
            'aud': _TEST_CLIENT_ID,
        },
        _private_key,
        algorithm='RS256',
        headers={'kid': _TEST_KID},
    )


# ── _get_jwks (lines 39-42) ──────────────────────────────────────────────────


def test_get_jwks_fetches_url_and_returns_json():
    _get_jwks.cache_clear()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {'keys': [{'kid': 'abc'}]}
    with patch('licensing_api.auth.httpx.Client') as mock_cls:
        mock_cls.return_value.__enter__.return_value.get.return_value = mock_resp
        result = _get_jwks('https://example.com/.well-known/jwks.json')
    _get_jwks.cache_clear()
    mock_resp.raise_for_status.assert_called_once()
    assert result == {'keys': [{'kid': 'abc'}]}


# ── _verify_token jwt.decode JWTError (lines 65-66) ─────────────────────────


def test_me_wrong_signature_returns_401(client, _private_key):
    """Correct kid, signed by a different key → jwt.decode raises JWTError."""
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jose_jwt.encode(
        {
            'sub': str(uuid.uuid4()),
            'email': 'test@example.com',
            'token_use': 'id',
            'aud': _TEST_CLIENT_ID,
        },
        wrong_key,
        algorithm='RS256',
        headers={'kid': _TEST_KID},
    )
    response = client.get('/api/me', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 401
    body = response.json()
    assert body['code'] == ErrorCode.InvalidToken
    assert 'Token validation failed' in body['details']


# ── get_current_user DB paths (lines 85-96) ──────────────────────────────────


def test_me_user_found_by_email_returns_200(client, _valid_token):
    """public_id not in DB → found by email (public_id already set) → 200."""
    user = _make_user()
    with (
        patch(
            'licensing_api.auth.get_user_by_public_id', new_callable=AsyncMock, return_value=None
        ),
        patch('licensing_api.auth.get_user_by_email', new_callable=AsyncMock, return_value=user),
    ):
        response = client.get('/api/me', headers={'Authorization': f'Bearer {_valid_token}'})
    assert response.status_code == 200
    assert CurrentUser.model_validate(response.json()).email == 'test@example.com'


def test_me_user_email_found_with_null_public_id_updates_it(client, _valid_token):
    """public_id not in DB → found by email with public_id=None → sets public_id and commits."""
    user = _make_user(public_id=None)
    mock_session = AsyncMock()

    async def _override():
        yield mock_session

    app.dependency_overrides[get_db_session] = _override
    try:
        with (
            patch(
                'licensing_api.auth.get_user_by_public_id',
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                'licensing_api.auth.get_user_by_email', new_callable=AsyncMock, return_value=user
            ),
        ):
            response = client.get('/api/me', headers={'Authorization': f'Bearer {_valid_token}'})
    finally:
        del app.dependency_overrides[get_db_session]

    assert response.status_code == 200
    assert isinstance(user.public_id, uuid.UUID)
    mock_session.commit.assert_called_once()


def test_me_user_not_found_by_email_returns_403(client, _valid_token):
    """Not found by public_id or email → 403 UserNotFound."""
    with (
        patch(
            'licensing_api.auth.get_user_by_public_id', new_callable=AsyncMock, return_value=None
        ),
        patch('licensing_api.auth.get_user_by_email', new_callable=AsyncMock, return_value=None),
    ):
        response = client.get('/api/me', headers={'Authorization': f'Bearer {_valid_token}'})
    assert response.status_code == 403
    assert response.json()['code'] == ErrorCode.UserNotFound


def test_me_inactive_user_found_by_email_returns_403(client, _valid_token):
    """Found by email but inactive → 403 UserInactive."""
    user = _make_user(is_active=False)
    with (
        patch(
            'licensing_api.auth.get_user_by_public_id', new_callable=AsyncMock, return_value=None
        ),
        patch('licensing_api.auth.get_user_by_email', new_callable=AsyncMock, return_value=user),
    ):
        response = client.get('/api/me', headers={'Authorization': f'Bearer {_valid_token}'})
    assert response.status_code == 403
    assert response.json()['code'] == ErrorCode.UserInactive
