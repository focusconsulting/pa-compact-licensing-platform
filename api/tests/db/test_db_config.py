import os

from licensing_api.db.config import LOCAL_DEFAULT_CONNECTION_STRING, DbConfig, get_config


class TestDbConfig:
    def test_default_values(self) -> None:
        config = DbConfig(connection_string="postgresql://localhost/test", schema="public")
        assert config.hide_sql_parameter_logs is True
        assert config.statement_timeout == 3600000

    def test_custom_values(self) -> None:
        config = DbConfig(
            connection_string="postgresql://localhost/test",
            schema="app",
            hide_sql_parameter_logs=False,
            statement_timeout=60000,
        )
        assert config.schema == "app"
        assert config.hide_sql_parameter_logs is False
        assert config.statement_timeout == 60000


class TestGetConfig:
    def test_falls_back_to_default_without_env(self) -> None:
        env_backup = os.environ.pop("POSTGRES_CONNECTION_STRING", None)
        try:
            config = get_config()
            assert config.connection_string == LOCAL_DEFAULT_CONNECTION_STRING
        finally:
            if env_backup:
                os.environ["POSTGRES_CONNECTION_STRING"] = env_backup

    def test_reads_from_env(self) -> None:
        os.environ["POSTGRES_CONNECTION_STRING"] = "postgresql://localhost/test"
        os.environ["DB_SCHEMA"] = "myschema"
        try:
            config = get_config()
            assert config.connection_string == "postgresql://localhost/test"
            assert config.schema == "myschema"
        finally:
            del os.environ["POSTGRES_CONNECTION_STRING"]
            os.environ.pop("DB_SCHEMA", None)

    def test_statement_timeout_override(self) -> None:
        os.environ["POSTGRES_CONNECTION_STRING"] = "postgresql://localhost/test"
        os.environ["DB_STATEMENT_TIMEOUT"] = "5000"
        try:
            config = get_config()
            assert config.statement_timeout == 5000
        finally:
            del os.environ["POSTGRES_CONNECTION_STRING"]
            del os.environ["DB_STATEMENT_TIMEOUT"]

    def test_invalid_statement_timeout_ignored(self) -> None:
        os.environ["POSTGRES_CONNECTION_STRING"] = "postgresql://localhost/test"
        os.environ["DB_STATEMENT_TIMEOUT"] = "not_a_number"
        try:
            config = get_config()
            assert config.statement_timeout == 3600000
        finally:
            del os.environ["POSTGRES_CONNECTION_STRING"]
            del os.environ["DB_STATEMENT_TIMEOUT"]
