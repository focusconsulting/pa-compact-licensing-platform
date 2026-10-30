"""JSON logging with sensitive keys masked (ADR-0001), shared by the API, the Worker, and jobs."""

import json
import logging
import logging.config
import re
from datetime import datetime, timezone
from typing import Any, cast

from licensing_api.config import settings

_SENSITIVE_PATTERN = re.compile(r'password|token|secret|cognito|ssn', re.IGNORECASE)
_MASK = '****'
_LOG_RECORD_KEYS = frozenset(logging.LogRecord('', 0, '', 0, '', (), None).__dict__.keys())


def _mask_sensitive(obj: object) -> object:
    if hasattr(obj, 'model_dump'):
        return _mask_sensitive(cast(Any, obj).model_dump())
    if isinstance(obj, dict):
        return {
            k: _MASK if _SENSITIVE_PATTERN.search(k) else _mask_sensitive(v) for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_mask_sensitive(item) for item in obj]
    return obj


class JsonFormatter(logging.Formatter):
    """Render each log record as one line of JSON, masking values under sensitive keys."""

    def format(self, record: logging.LogRecord) -> str:
        """The record as JSON: timestamp, level, logger, message, any ``extra`` fields, and the exception."""
        log_entry: dict[str, object] = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec='milliseconds')
            .replace('+00:00', 'Z'),  # noqa: UP017
            'level': record.levelname,
            'logger': record.name,
        }

        message = record.getMessage()
        if message:
            log_entry['message'] = message

        for key, val in record.__dict__.items():
            if key not in _LOG_RECORD_KEYS and not key.startswith('_'):
                log_entry[key] = val
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info).splitlines()
        return json.dumps(_mask_sensitive(log_entry))


LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': JsonFormatter,
        },
    },
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        'uvicorn': {'handlers': [], 'level': settings.log_level.upper(), 'propagate': False},
    },
    'root': {
        'handlers': ['default'],
        'level': settings.log_level.upper(),
    },
}


def configure_logging() -> None:
    """Send every log record to stdout as JSON. Each process calls this once at startup."""
    logging.config.dictConfig(LOG_CONFIG)
