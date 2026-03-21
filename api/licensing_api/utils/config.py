from pydantic import BaseModel, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class DbConfig(BaseModel):
    connection_string: PostgresDsn | None = None
    # connection_string: Optional[PostgresDsn] = MultiHostUrl(
    #     "postgresql+psycopg://licensing:secret123@localhost:5432/licensing"
    # )
    # DB_CONFIG__PGHOST
    pghost: str | None = None
    pgdatabase: str | None = None
    pgport: str = "5432"
    pguser: str | None = None
    pgpassword: str | None = None
    postgres_schema: str = "public"
    hide_sql_parameter_logs: bool = True
    # How long Postgres will run a SQL statement before erroring out with a timeout exception
    # This prevents exceedingly long queries from running forever
    #
    # The default here is set to 60 minutes and is specified in MS
    # 1000 * 60 * 60
    statement_timeout: int = 3600000
    ssl_mode: str = "prefer"
    iam_auth_enabled: bool = True


class SessionConfig(BaseModel):
    redis_url: str = "redis://127.0.0.1"
    redis_user: str = "app_user"
    redis_cluster_name: str = "licensing"
    redis_host: str | None = None
    redis_port: str = "6379"
    use_iam_auth: bool = False


class AppConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_nested_delimiter="__")

    logging_level: str = "INFO"
    environment: str = "local"
    app_secret_key: str = "UPDATE ME"
    session_timeout_in_minutes: int = 20
    request_timeout_in_seconds: int = 120
    use_dev_logging: bool = True
    secure_session_cookie: bool = False
    disable_csrf_tokens: bool = False
    db_config: DbConfig = DbConfig()
    session_config: SessionConfig = SessionConfig()

    @property
    def is_local(self) -> bool:
        return self.environment == "local" or self.environment == "test"

    @property
    def is_protected_environment(self) -> bool:

        return self.environment == "prod" or self.environment == "staging"


def get_app_config() -> AppConfig:
    return AppConfig()
