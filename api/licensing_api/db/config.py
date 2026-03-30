import os
from dataclasses import dataclass

from licensing_api.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DbConfig:
    connection_string: str
    schema: str
    hide_sql_parameter_logs: bool = True
    # How long Postgres will run a SQL statement before erroring out with a timeout exception
    # This prevents exceedingly long queries from running forever
    #
    # The default here is set to 60 minutes and is specified in MS
    # 1000 * 60 * 60
    statement_timeout: int = 3600000


LOCAL_DEFAULT_CONNECTION_STRING = (
    "postgresql+psycopg://licensing:secret123@localhost:5432/licensing"
)


def get_config() -> DbConfig:
    connection = os.getenv("POSTGRES_CONNECTION_STRING", LOCAL_DEFAULT_CONNECTION_STRING)

    db_config = DbConfig(
        connection_string=connection,
        schema=os.getenv("DB_SCHEMA", "public"),
    )

    statement_timeout_override = os.getenv("DB_STATEMENT_TIMEOUT")
    if statement_timeout_override is not None and statement_timeout_override.isdigit():
        db_config.statement_timeout = int(statement_timeout_override)

    logger.info(
        "Constructed database configuration",
        extra={
            "connection": db_config.connection_string,
            "schema": db_config.schema,
            "hide_sql_parameter_logs": db_config.hide_sql_parameter_logs,
            "statement_timeout": db_config.statement_timeout,
        },
    )

    return db_config
