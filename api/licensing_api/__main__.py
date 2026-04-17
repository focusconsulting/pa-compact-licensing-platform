import asyncio
import json
import logging
import re
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, cast

import redis.asyncio as aioredis
import uvicorn
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from licensing_api.config import settings
from licensing_api.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    validation_error_handler,
)
from licensing_api.migrations import run_migrations
from licensing_api.routes import health, user

_SENSITIVE_PATTERN = re.compile(r'password|token|secret|cognito', re.IGNORECASE)
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


def _configure_otel() -> None:  # pragma: no cover
    """Configure OpenTelemetry SDK to export traces and metrics to the ADOT sidecar.

    Imports are lazy so local dev and tests don't pay the import cost when
    otel_enabled=False (the default).
    """
    from opentelemetry import metrics as otel_metrics
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            'service.name': 'licensing-api',
            'deployment.environment': settings.environment.lower(),
        }
    )

    # Traces → ADOT sidecar → X-Ray
    trace_exporter = OTLPSpanExporter(endpoint=settings.otel_collector_endpoint, insecure=True)
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(tracer_provider)

    # Metrics → ADOT sidecar → CloudWatch EMF (namespace: LicensingAPI)
    metric_exporter = OTLPMetricExporter(endpoint=settings.otel_collector_endpoint, insecure=True)
    reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=60_000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    otel_metrics.set_meter_provider(meter_provider)

    # Auto-instrument asyncpg (DB query tracing)
    AsyncPGInstrumentor().instrument()

    logger.info('OpenTelemetry configured', extra={'endpoint': settings.otel_collector_endpoint})


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


_handler = logging.StreamHandler(stream=sys.stdout)
_handler.setFormatter(JsonFormatter())
logging.basicConfig(level=settings.log_level, handlers=[_handler], force=True)

_LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'json': {'()': JsonFormatter}},
    'handlers': {
        'default': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'stream': 'ext://sys.stdout',
        }
    },
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

    engine = create_async_engine(settings.db_url, pool_pre_ping=True)
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.db_engine = engine

    app.state.redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    yield
    await engine.dispose()
    await app.state.redis.aclose()


if settings.otel_enabled:
    _configure_otel()

app = FastAPI(
    title='PA Compact Licensing API',
    description='APIs supporting the PA Compact Commission Data System',
    docs_url='/docs',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]

api_router = APIRouter(prefix='/api')
# If we decide to exclude /health routes from /api, that is make them private,
# include the health.router directly to app. Then update the paths in
# infrastructure/iac/components/app/terraform/ecs.tf
api_router.include_router(health.router)
api_router.include_router(user.router)
app.include_router(api_router)

if settings.otel_enabled:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)

if __name__ == '__main__':
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        log_config=_LOG_CONFIG,
    )
