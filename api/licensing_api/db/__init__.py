import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import psycopg
import sqlalchemy
import sqlalchemy.pool as pool
from sqlalchemy import URL
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker

import licensing_api.db.handle_error  # noqa: F401
from licensing_api.db.config import DbConfig, get_config
from licensing_api.utils.logging import get_logger

logger = get_logger(__name__)


def get_connection_url(config: DbConfig) -> URL | str:
    # TODO should we use IAM auth?

    return config.connection_string


def init(config: DbConfig | None = None) -> scoped_session:
    logger.info("connecting to postgres db")
    db_config: DbConfig = config if config is not None else get_config()
    connection_url = get_connection_url(db_config)
    engine = sqlalchemy.create_engine(
        connection_url,
        execution_options={
            "isolation_level": "AUTOCOMMIT",
            "search_path": db_config.schema,
            "statement_timeout": db_config.statement_timeout,
        },
    )

    # Explicitly commit sessions — usually with session_scope. Also disable expiry on commit,
    # as we don't need to be strict on consistency within our routes. Once we've retrieved data
    # from the database, we shouldn't make any extra requests to the db when grabbing existing
    # attributes.
    session_factory = scoped_session(
        sessionmaker(autocommit=False, expire_on_commit=False, bind=engine)
    )

    engine.dispose()

    return session_factory


def verify_ssl(connection_info: Any) -> None:
    """Verify that the database connection is encrypted and log a warning if not.

    TODO: raise a RuntimeError if not."""
    if connection_info.ssl_in_use:
        logger.info(
            "database connection is using SSL: %s",
            ", ".join(
                name + " " + connection_info.ssl_attribute(name)
                for name in connection_info.ssl_attribute_names
            ),
        )
    else:
        logger.warning("database connection is not using SSL")


def create_engine(config: DbConfig | None = None) -> Engine:
    db_config: DbConfig = config if config is not None else get_config()

    conn_pool = pool.QueuePool(
        psycopg.connect(**get_connection_parameters(db_config)),  # type: ignore[arg-type]
        max_overflow=10,
        pool_size=20,
        timeout=3,
    )

    # The URL only needs to specify the dialect, since the connection pool
    # handles the actual connections.
    #
    # (a SQLAlchemy Engine represents a Dialect+Pool)
    return sqlalchemy.create_engine(
        "postgresql+psycopg://",
        pool=conn_pool,
        hide_parameters=db_config.hide_sql_parameter_logs,
        json_serializer=lambda o: json.dumps(o),
    )


def get_connection_parameters(db_config: DbConfig) -> dict[str, Any]:
    connect_args: dict[str, Any] = {}
    environment = os.getenv("ENVIRONMENT")
    if not environment:
        raise Exception("ENVIRONMENT is not set")

    if environment != "local":
        connect_args["sslmode"] = "require"

    from urllib.parse import urlparse

    result = urlparse(db_config.connection_string)
    username = result.username
    password = result.password
    database = result.path[1:]
    host = result.hostname
    port = result.port

    return dict(
        host=host,
        dbname=database,
        user=username,
        password=password,
        port=port,
        options=(
            f"-c search_path={db_config.schema} -c statement_timeout={db_config.statement_timeout}"
        ),
        connect_timeout=3,
        **connect_args,
    )


@contextmanager
def session_scope(session: Session, close: bool = False) -> Generator[Session]:
    """Provide a transactional scope around a series of operations.

    See https://docs.sqlalchemy.org/en/13/orm/session_basics.html#when-do-i-construct-a-session-when-do-i-commit-it-and-when-do-i-close-it
    """

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        if close:
            session.close()
