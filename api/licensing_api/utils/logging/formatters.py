#
# Custom logging formatters.
#

import json
import logging
from typing import Any, Self

logger = logging.getLogger(__name__)

# Attributes of LogRecord to exclude from the JSON formatted lines. An exclusion list approach is
# used so that all "extra" attributes can be included in a line.
EXCLUDE_ATTRIBUTES = {
    "args",
    "exc_info",
    "filename",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "msg",
    "pathname",
    "processName",
    "relativeCreated",
}

MOST_COMPACT_JSON_SEPARATORS = (",", ":")


class JsonFormatter(logging.Formatter):  # noqa: B1
    """A logging formatter which formats each line as JSON."""

    def format(self: Self, record: logging.LogRecord) -> Any:
        super().format(record)

        output = {
            key: value
            for key, value in record.__dict__.items()
            if key not in EXCLUDE_ATTRIBUTES and value is not None
        }

        return json.dumps(output, separators=MOST_COMPACT_JSON_SEPARATORS)
