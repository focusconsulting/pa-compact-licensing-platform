from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """API configuration, read from environment variables, with defaults for local development."""

    db_host: str = 'localhost'
    db_port: int = 5432
    db_name: str = 'licensing'
    db_user: str = 'licensing'
    db_password: str = 'invalid'

    api_port: int = 8000
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'
    environment: Literal['LOCAL_DEV', 'DEV', 'STAGING', 'PROD'] = 'LOCAL_DEV'
    otel_enabled: bool = False
    otel_collector_endpoint: str = 'http://localhost:4317'

    cognito_user_pool_id: str = 'invalid'
    cognito_region: str = 'us-east-1'
    cognito_client_id: str = 'invalid'
    # The Cognito API base URL. Unset in AWS; the local stack points it at the Cognito mock.
    cognito_endpoint_url: str | None = None

    cors_origins: list[str] = ['http://localhost:3000']

    # Email over SMTP: maildev locally, SES's SMTP interface in AWS (STARTTLS on 587).
    smtp_host: str = 'localhost'
    smtp_port: int = 1025
    smtp_starttls: bool = False
    smtp_username: str = ''
    smtp_password: str = ''
    email_from_address: str = 'no-reply@licensing.localhost'
    # Where links in emails point: the client's origin.
    client_base_url: str = 'http://localhost:3000'
    # The Commission mailbox for operational notifications; empty sends none.
    commission_ops_email: str = ''

    @property
    def db_url(self) -> str:
        """The asyncpg URL the app's database engine connects with."""
        return f'postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}'

    @property
    def sync_db_url(self) -> str:
        """The plain ``postgresql://`` URL yoyo migrations connect with."""
        return f'postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}'

    @property
    def cognito_jwks_url(self) -> str:
        """The user pool's JWKS URL, under ``cognito_endpoint_url`` when it is set (the local Cognito mock)."""
        endpoint = (
            self.cognito_endpoint_url or f'https://cognito-idp.{self.cognito_region}.amazonaws.com'
        )
        return f'{endpoint.rstrip("/")}/{self.cognito_user_pool_id}/.well-known/jwks.json'


settings = Settings()


def get_settings() -> Settings:
    """The process's ``Settings``, as a dependency so tests can override it."""
    return settings
