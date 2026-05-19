import uuid
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt as jose_jwt

from licensing_api.auth import _get_jwks, _verify_token
from licensing_api.errors import AppError, ErrorCode

_TEST_CLIENT_ID = 'test-client-id'
_TEST_KID = 'test-key-1'


def _settings():
    s = MagicMock()
    s.cognito_client_id = _TEST_CLIENT_ID
    return s


# ── _get_jwks ────────────────────────────────────────────────────────────────


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


# ── _verify_token ────────────────────────────────────────────────────────────


def test_verify_token_invalid_format_raises_401():
    """Malformed JWT string → JWTError at header parse → AppError 401 InvalidToken."""
    with pytest.raises(AppError) as exc:
        _verify_token('not.a.valid.jwt', _settings())
    assert exc.value.status_code == 401
    assert exc.value.code == ErrorCode.InvalidToken
    assert 'Invalid token format' in exc.value.details


def test_verify_token_unknown_signing_key_raises_401(jwks, _private_key):
    """Token kid not in JWKS → AppError 401 InvalidToken."""
    token = jose_jwt.encode(
        {'sub': str(uuid.uuid4()), 'email': 'x@x.com', 'token_use': 'id', 'aud': _TEST_CLIENT_ID},
        _private_key,
        algorithm='RS256',
        headers={'kid': 'unknown-kid'},
    )
    with patch('licensing_api.auth._get_jwks', return_value=jwks):
        with pytest.raises(AppError) as exc:
            _verify_token(token, _settings())
    assert exc.value.status_code == 401
    assert exc.value.code == ErrorCode.InvalidToken
    assert 'Unknown signing key' in exc.value.details


def test_verify_token_wrong_signature_raises_401(jwks):
    """Correct kid, signed by a different key → jwt.decode raises JWTError."""
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jose_jwt.encode(
        {'sub': str(uuid.uuid4()), 'email': 'x@x.com', 'token_use': 'id', 'aud': _TEST_CLIENT_ID},
        wrong_key,
        algorithm='RS256',
        headers={'kid': _TEST_KID},
    )
    with patch('licensing_api.auth._get_jwks', return_value=jwks):
        with pytest.raises(AppError) as exc:
            _verify_token(token, _settings())
    assert exc.value.status_code == 401
    assert exc.value.code == ErrorCode.InvalidToken
    assert 'Token validation failed' in exc.value.details


def test_verify_token_wrong_token_use_raises_401(jwks, _private_key):
    """access token instead of id token → AppError 401 InvalidToken."""
    token = jose_jwt.encode(
        {
            'sub': str(uuid.uuid4()),
            'email': 'x@x.com',
            'token_use': 'access',
            'aud': _TEST_CLIENT_ID,
        },
        _private_key,
        algorithm='RS256',
        headers={'kid': _TEST_KID},
    )
    with patch('licensing_api.auth._get_jwks', return_value=jwks):
        with pytest.raises(AppError) as exc:
            _verify_token(token, _settings())
    assert exc.value.status_code == 401
    assert exc.value.code == ErrorCode.InvalidToken
    assert 'Expected Cognito ID token' in exc.value.details
