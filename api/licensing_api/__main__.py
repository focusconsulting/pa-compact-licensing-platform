import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, cast

import asyncpg
import uvicorn
from fastapi import FastAPI

from licensing_api.config import settings
from licensing_api.migrations import run_migrations
from licensing_api.routes.health import router

_SENSITIVE_PATTERN = re.compile(r'password|token|secret', re.IGNORECASE)
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
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, object] = {
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec='milliseconds')
            .replace('+00:00', 'Z'),  # noqa: UP017
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        for key, val in record.__dict__.items():
            if key not in _LOG_RECORD_KEYS and not key.startswith('_'):
                log_entry[key] = val
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        return json.dumps(_mask_sensitive(log_entry))


_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter())
logging.basicConfig(level=settings.log_level, handlers=[_handler], force=True)

_LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'json': {'()': JsonFormatter}},
    'handlers': {'default': {'class': 'logging.StreamHandler', 'formatter': 'json'}},
    'loggers': {
        'uvicorn': {'handlers': ['default'], 'propagate': False},
        'uvicorn.error': {'handlers': ['default'], 'propagate': False},
        'uvicorn.access': {'handlers': ['default'], 'propagate': False},
    },
}

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    logger.info('Starting up', extra={'settings': settings})
    await asyncio.to_thread(run_migrations)
    app.state.db_pool = await asyncpg.create_pool(settings.db_url)
    yield
    await app.state.db_pool.close()


app = FastAPI(
    title='PA Compact Licensing API',
    description='APIs supporting the PA Compact Commission Data System',
    docs_url='/docs',
    lifespan=lifespan,
)

app.include_router(router)

if __name__ == '__main__':
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        log_config=_LOG_CONFIG,
    )
