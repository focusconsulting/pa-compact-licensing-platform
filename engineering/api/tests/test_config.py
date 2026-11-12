import ssl
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url
from yoyo.connections import parse_uri

from licensing_api.config import Settings, get_settings, settings
from licensing_api.serve import write_certificate


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


# Every character secrets.tf's random_password may generate that means something in a URL.
URL_SPECIAL_PASSWORD = 'a#b?c:d[e]{f}%g<h>i!j^k&l*m(n)o=p+q'


def test_db_urls_carry_a_password_with_url_special_characters():
    settings = Settings(
        db_user='licensing', db_password=URL_SPECIAL_PASSWORD, db_host='db', db_port=5432
    )

    async_url = make_url(settings.db_url)
    sync_url = parse_uri(settings.sync_db_url)

    assert (async_url.password, async_url.host, async_url.port) == (
        URL_SPECIAL_PASSWORD,
        'db',
        5432,
    )
    assert (sync_url.password, sync_url.hostname, sync_url.port) == (
        URL_SPECIAL_PASSWORD,
        'db',
        5432,
    )


def test_get_settings_returns_the_process_settings():
    assert get_settings() is settings


def test_db_connections_are_unverified_without_a_ca_file():
    settings = Settings(db_ca_file='')

    assert settings.db_connect_args == {}
    assert parse_uri(settings.sync_db_url).args == {}


def test_db_connections_verify_the_server_against_the_ca_file(tmp_path: Path):
    ca_file, _ = write_certificate(tmp_path / 'ca dir')
    settings = Settings(db_ca_file=str(ca_file), db_password=URL_SPECIAL_PASSWORD)

    context = settings.db_connect_args['ssl']
    sync_url = parse_uri(settings.sync_db_url)

    assert context.verify_mode is ssl.CERT_REQUIRED
    assert context.check_hostname
    assert len(context.get_ca_certs()) == 1
    assert sync_url.args == {'sslmode': 'verify-full', 'sslrootcert': str(ca_file)}
    assert sync_url.password == URL_SPECIAL_PASSWORD


def test_the_rds_bundle_the_image_ships_loads_as_a_trust_store():
    bundle = Path(__file__).parent.parent / 'certs' / 'rds-global-bundle.pem'

    assert Settings(db_ca_file=str(bundle)).db_connect_args['ssl'].get_ca_certs()
