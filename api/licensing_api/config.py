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

    @property
    def db_url(self) -> str:
        return f'postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}'


settings = Settings()
