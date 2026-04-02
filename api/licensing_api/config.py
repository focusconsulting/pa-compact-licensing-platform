from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_url: str = 'postgresql://invalid'
    redis_url: str = 'redis://invalid'
    api_port: int = 8000
    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'
    environment: Literal['LOCAL_DEV', 'DEV', 'STAGING', 'PROD'] = 'LOCAL_DEV'


settings = Settings()
