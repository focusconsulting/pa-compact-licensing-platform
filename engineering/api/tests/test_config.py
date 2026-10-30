import pytest
from pydantic import ValidationError

from licensing_api.config import Settings, get_settings, settings


def test_jwks_url_defaults_to_the_cognito_service_for_the_region():
    settings = Settings(
        cognito_endpoint_url=None, cognito_region='us-west-2', cognito_user_pool_id='us-west-2_pool'
    )

    assert settings.cognito_jwks_url == (
        'https://cognito-idp.us-west-2.amazonaws.com/us-west-2_pool/.well-known/jwks.json'
    )


def test_jwks_url_uses_the_configured_endpoint():
    settings = Settings(
        cognito_endpoint_url='http://localhost:9229/', cognito_user_pool_id='local_licensing'
    )

    assert (
        settings.cognito_jwks_url == 'http://localhost:9229/local_licensing/.well-known/jwks.json'
    )


@pytest.mark.parametrize('name', ['LOCAL_DEV', 'STAGING', 'PROD'])
def test_environment_accepts_each_deployed_environment_name(name: str):
    assert Settings(environment=name).environment == name


def test_environment_rejects_an_unknown_name():
    with pytest.raises(ValidationError):
        Settings(environment='DEV')  # pyright: ignore[reportArgumentType] -- the rejection under test


def test_get_settings_returns_the_process_settings():
    assert get_settings() is settings
