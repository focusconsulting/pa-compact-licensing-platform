from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_host: str = 'localhost'
    db_port: int = 5432
    db_name: str = 'licensing'
    db_user: str = 'licensing'
    db_password: str = 'invalid'

    redis_url: str = 'redis://invalid'
    api_port: int = 8000
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'
    environment: Literal['LOCAL_DEV', 'DEV', 'STAGING', 'PROD'] = 'LOCAL_DEV'
    otel_enabled: bool = False
    otel_collector_endpoint: str = 'http://localhost:4317'

    cognito_user_pool_id: str = 'invalid'
    cognito_region: str = 'us-east-1'
    cognito_client_id: str = 'invalid'

    cors_origins: list[str] = ['http://localhost:3000']

    @property
    def db_url(self) -> str:
        return f'postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}'

    @property
    def sync_db_url(self) -> str:
        return f'postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}'

    @property
    def cognito_jwks_url(self) -> str:
        return f'https://cognito-idp.{self.cognito_region}.amazonaws.com/{self.cognito_user_pool_id}/.well-known/jwks.json'


settings = Settings()


def get_settings() -> Settings:
    return settings
