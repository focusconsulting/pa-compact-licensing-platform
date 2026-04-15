import base64
from collections.abc import Callable
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from licensing_api.__main__ import app
from licensing_api.config import Settings, get_settings

TEST_SETTINGS = Settings(
    cognito_client_id='test-client-id', cognito_user_pool_id='us-east-1_testpool'
)

_TEST_CLIENT_ID = 'test-client-id'
_TEST_KID = 'test-key-1'


def _int_to_base64url(n: int) -> str:
    length = (n.bit_length() + 7) // 8
    return base64.urlsafe_b64encode(n.to_bytes(length, 'big')).rstrip(b'=').decode()


@pytest.fixture(scope='module')
def _private_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope='module')
def jwks(_private_key):
    pub = _private_key.public_key().public_numbers()
    return {
        'keys': [
            {
                'kty': 'RSA',
                'use': 'sig',
                'alg': 'RS256',
                'kid': _TEST_KID,
                'n': _int_to_base64url(pub.n),
                'e': _int_to_base64url(pub.e),
            }
        ]
    }


@pytest.fixture(scope='module')
def client(jwks):
    # dependency_overrides replaces the stored function reference FastAPI holds
    # inside Depends(get_settings), which patch() on the module name cannot reach.
    app.dependency_overrides[get_settings] = lambda: TEST_SETTINGS
    with patch('licensing_api.auth._get_jwks', return_value=jwks):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope='module')
def auth_header(_private_key) -> Callable[[str], dict]:
    """Returns a helper that builds a signed Authorization Bearer header for the given email."""

    def _make(email: str) -> dict:
        token = jose_jwt.encode(
            {
                'sub': '00000000-0000-0000-0000-000000000001',
                'email': email,
                'token_use': 'id',
                'aud': _TEST_CLIENT_ID,
            },
            _private_key,
            algorithm='RS256',
            headers={'kid': _TEST_KID},
        )
        return {'Authorization': f'Bearer {token}'}

    return _make
