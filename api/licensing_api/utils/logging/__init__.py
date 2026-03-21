#
# Utility functions for configuring and interfacing with logging.
#

import atexit
import logging.config  # noqa: B1
import os
import platform
import pwd
import resource
import sys
import time
from logging import CRITICAL, DEBUG, ERROR, INFO, WARNING  # noqa: B1 F401
from typing import Any, cast

from . import formatters, network

start_time = time.monotonic()

LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": formatters.JsonFormatter},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": "WARN"},
    "loggers": {
        "alembic": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "werkzeug": {"handlers": ["console"], "level": "WARN", "propagate": False},
    },
}


def init(program_name: str, develop: bool = False) -> None:
    """Initialize the logging system."""
    if develop:
        LOGGING["handlers"]["console"]["formatter"] = "develop"
    logging.config.dictConfig(LOGGING)
    logger.info(
        "start %s: %s %s %s, hostname %s, pid %i, user %i(%s)",
        program_name,
        platform.python_implementation(),
        platform.python_version(),
        platform.system(),
        platform.node(),
        os.getpid(),
        os.getuid(),
        pwd.getpwuid(os.getuid()).pw_name,
        extra={
            "hostname": platform.node(),
            "cpu_count": os.cpu_count(),
            # If mypy is run on a mac, it will throw a module has no attribute error, even though
            # we never actually access it with the conditional.
            #
            # However, we can't just silence this error, because on linux (e.g. CI/CD) that will
            # throw an unused “type: ignore” comment error. Casting to Any instead ensures this
            # passes regardless of where mypy is being run
            "cpu_usable": (
                len(cast(Any, os).sched_getaffinity(0))
                if "sched_getaffinity" in dir(os)
                else "unknown"
            ),
        },
    )
    logger.info("invoked as: %s", " ".join(original_argv))

    override_logging_levels()

    atexit.register(exit_handler, program_name)

    network.init()


def override_logging_levels() -> None:
    """Override default logging levels using settings in LOGGING_LEVEL environment variable.

    The format is "name1=level,name2=level". For example:

      LOGGING_LEVEL="sqlalchemy=INFO"
    """
    for override in os.environ.get("LOGGING_LEVEL", "").split(","):
        if "=" not in override:
            continue
        logger_name, _separator, logging_level = override.partition("=")
        set_logging_level(logger_name, logging_level)


def set_logging_level(logger_name: str, logging_level: str) -> None:
    """Set the logging level for the given logger."""
    logger.info("set level for %s to %s", logger_name, logging_level)
    logging.getLogger(logger_name).setLevel(logging_level)


def exit_handler(program_name: str) -> None:
    """Log a message at program exit."""
    t = time.monotonic() - start_time
    ru = resource.getrusage(resource.RUSAGE_SELF)
    logger.info(
        "exit %s: pid %i, real %.3fs, user %.2fs, system %.2fs, peak rss %iK",
        program_name,
        os.getpid(),
        t,
        ru.ru_utime,
        ru.ru_stime,
        ru.ru_maxrss,
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


logger = get_logger(__name__)
original_argv = tuple(sys.argv)
