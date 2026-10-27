import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
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
from licensing_api.logging_config import LOG_CONFIG, configure_logging
from licensing_api.migrations import run_migrations
from licensing_api.request_logger import (
    RequestIdMiddleware,
    RequestLoggingMiddleware,
    UnhandledExceptionMiddleware,
)
from licensing_api.routes import api


def _configure_otel(app: FastAPI) -> None:  # pragma: no cover
    """Configure OpenTelemetry SDK to export traces and metrics to the ADOT sidecar.

    Imports are lazy so local dev and tests don't pay the import cost when
    otel_enabled=False (the default).
    """
    from opentelemetry import metrics as otel_metrics
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
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

    # Trace every request; after the providers above, so it uses them
    FastAPIInstrumentor.instrument_app(app)

    logger.info('OpenTelemetry configured', extra={'endpoint': settings.otel_collector_endpoint})


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Run migrations, then hold the database engine for the app's lifetime and dispose of it on shutdown.

    Migrations run in a thread because yoyo is synchronous.
    """
    logger.info('Starting up', extra={'settings': settings})
    await asyncio.to_thread(run_migrations)

    engine = create_async_engine(settings.db_url, pool_pre_ping=True)
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.db_engine = engine

    yield
    await engine.dispose()


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
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(UnhandledExceptionMiddleware)
# Outermost, so the ID is set before the request is logged and is on every response, including a 500.
app.add_middleware(RequestIdMiddleware)

app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
app.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]

app.include_router(api)

# Only deployed tasks export telemetry (to the ADOT sidecar); tests and local runs leave it off.
if settings.otel_enabled:  # pragma: no cover
    _configure_otel(app)

if __name__ == '__main__':
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=settings.api_port,
        log_level=settings.log_level.lower(),
        log_config=LOG_CONFIG,
    )
