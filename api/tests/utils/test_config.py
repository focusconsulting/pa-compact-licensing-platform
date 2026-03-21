import os

from licensing_api.utils.config import AppConfig


class TestAppConfig:
    def test_default_values(self) -> None:
        config = AppConfig()
        assert config.environment == "local"
        assert config.logging_level == "INFO"
        assert config.session_timeout_in_minutes == 20
        assert config.request_timeout_in_seconds == 120
        assert config.use_dev_logging is True
        assert config.secure_session_cookie is False
        assert config.disable_csrf_tokens is False

    def test_is_local(self) -> None:
        config = AppConfig(environment="local")
        assert config.is_local is True

        config = AppConfig(environment="test")
        assert config.is_local is True

        config = AppConfig(environment="prod")
        assert config.is_local is False

    def test_is_protected_environment(self) -> None:
        config = AppConfig(environment="prod")
        assert config.is_protected_environment is True

        config = AppConfig(environment="staging")
        assert config.is_protected_environment is True

        config = AppConfig(environment="local")
        assert config.is_protected_environment is False

    def test_from_env_vars(self, monkeypatch: object) -> None:
        os.environ["ENVIRONMENT"] = "staging"
        os.environ["LOGGING_LEVEL"] = "DEBUG"
        os.environ["SESSION_TIMEOUT_IN_MINUTES"] = "30"
        try:
            config = AppConfig()
            assert config.environment == "staging"
            assert config.logging_level == "DEBUG"
            assert config.session_timeout_in_minutes == 30
        finally:
            del os.environ["ENVIRONMENT"]
            del os.environ["LOGGING_LEVEL"]
            del os.environ["SESSION_TIMEOUT_IN_MINUTES"]

    def test_db_config_defaults(self) -> None:
        config = AppConfig()
        assert config.db_config.pgport == "5432"
        assert config.db_config.postgres_schema == "public"
        assert config.db_config.hide_sql_parameter_logs is True
        assert config.db_config.statement_timeout == 3600000
        assert config.db_config.ssl_mode == "prefer"

    def test_session_config_defaults(self) -> None:
        saved = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("SESSION_CONFIG__")}
        try:
            config = AppConfig()
            assert config.session_config.redis_url == "redis://127.0.0.1"
            assert config.session_config.redis_port == "6379"
            assert config.session_config.use_iam_auth is False
        finally:
            os.environ.update(saved)
