import asyncio
import json
import logging
import logging.config
import time
import traceback
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.database import init_db

# ── Logging configuration ──────────────────────────────────────────────────
# Emit every log line as a JSON object so output is machine-readable and
# grep-friendly while remaining human-readable in a terminal.

class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # If the message is already a JSON string (from the request logger),
        # embed it directly; otherwise wrap it.
        try:
            payload = json.loads(record.getMessage())
        except (ValueError, TypeError):
            payload = {"msg": record.getMessage()}

        payload.setdefault("level", record.levelname)
        payload.setdefault("logger", record.name)
        payload.setdefault("ts", self.formatTime(record, self.datefmt))

        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": _JsonFormatter, "datefmt": "%Y-%m-%dT%H:%M:%S"},
        # Plain text fallback for uvicorn's own access/error loggers
        "plain": {"format": "%(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "json",
        },
        "uvicorn_console": {
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "plain",
        },
    },
    "loggers": {
        # Application loggers — JSON output
        "app": {"handlers": ["console"], "level": "DEBUG", "propagate": False},
        "uvicorn": {"handlers": ["uvicorn_console"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"handlers": ["uvicorn_console"], "level": "INFO", "propagate": False},
        "uvicorn.access": {"handlers": ["uvicorn_console"], "level": "INFO", "propagate": False},
        "sqlalchemy.engine": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("app")
from app.routes import (
    auth, products, traceability, certificates, analytics, share, contact, taxonomy,
    search, batches, warehouses, shipments, collections, inventory, item_movements,
    codes, health, cargo, verify, compliance, rates, enrichment, continuous_enrichment,
    events, telemetry, developer_portal, gov_integration, arabic_i18n,
    recalls, suppliers, insurance, monitoring, retention, tiers, esg, startup,
)

# OpenTelemetry tracing — enabled only when opentelemetry packages are installed
_tracer = None
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(__name__)
    _otel_available = True
    logger.info({"msg": "OpenTelemetry SDK loaded", "exporter": "OTLP"})
except ImportError:
    _otel_available = False
    logger.info({"msg": "OpenTelemetry not available — tracing disabled"})


@asynccontextmanager
async def lifespan(app: FastAPI):
    from pathlib import Path
    from app.services.startup_service import run_startup_tasks

    logger.info({"msg": "FoodTrack starting up", "db": settings.DATABASE_URL.split("///")[0], "site": settings.SITE_URL})

    if _otel_available:
        FastAPIInstrumentor.instrument_app(app)

    # Ensure tables exist for SQLite dev environments (production uses Alembic only)
    try:
        await init_db()
        logger.info({"msg": "Database initialised"})
    except Exception as exc:
        logger.error({"msg": "Database init failed", "error": str(exc), "trace": traceback.format_exc()})
        raise

    # ── Launch background startup tasks (migrations + seeding) ──────────────
    # The server starts accepting requests immediately. Migrations and seeding
    # run behind it. Clients can poll GET /api/v1/startup/status for progress.
    backend_dir = Path(__file__).resolve().parent.parent
    asyncio.create_task(run_startup_tasks(backend_dir))
    logger.info({"msg": "Background startup tasks launched — server is live"})

    # Log every registered route at startup for easy verification
    route_list = [
        {"path": r.path, "methods": list(getattr(r, "methods", []))}
        for r in app.routes
        if hasattr(r, "path") and getattr(r, "methods", None)
    ]
    logger.info({"msg": "Routes registered", "count": len(route_list)})
    for r in route_list:
        logger.debug({"msg": "route", "path": r["path"], "methods": r["methods"]})
    yield
    logger.info({"msg": "FoodTrack shutting down"})


app = FastAPI(title="FoodTrack - Digital Trust Infrastructure", version="1.0.0", lifespan=lifespan)

# CORS: restrict allowed origins to SITE_URL in production.
# Supports comma-separated list via CORS_ORIGINS env var for multi-domain setups.
import os as _os
_raw_origins = _os.getenv("CORS_ORIGINS", settings.SITE_URL)
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next):
    """Per-request structured logging with correlation ID, timing, and exception capture."""
    from app.services.monitoring_service import record_request

    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    logger.info({
        "event": "request_start",
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "query": str(request.url.query) or None,
        "client": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    })

    start = time.time()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        logger.error({
            "event": "unhandled_exception",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "error": str(exc),
            "trace": traceback.format_exc(),
        })
        raise
    finally:
        duration_ms = int((time.time() - start) * 1000)
        record_request(duration_ms, status_code)
        level = logging.WARNING if status_code >= 400 else logging.INFO
        logger.log(level, json.dumps({
            "event": "request_end",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": status_code,
            "duration_ms": duration_ms,
            "client": request.client.host if request.client else None,
        }))


@app.middleware("http")
async def open_telemetry_tracing(request: Request, call_next):
    if _tracer:
        with _tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
            return response
    return await call_next(request)


@app.middleware("http")
async def accept_language_middleware(request: Request, call_next):
    from app.services.i18n_service import get_accept_language
    lang = get_accept_language(request.headers.get("accept-language"))
    request.state.language = lang
    return await call_next(request)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(traceability.router, prefix="/api/v1")
app.include_router(certificates.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(share.router, prefix="/api/v1")
app.include_router(contact.router, prefix="/api/v1")
app.include_router(taxonomy.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(batches.router, prefix="/api/v1")
app.include_router(warehouses.router, prefix="/api/v1")
app.include_router(shipments.router, prefix="/api/v1")
app.include_router(collections.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(item_movements.router, prefix="/api/v1")
app.include_router(cargo.router, prefix="/api/v1")
app.include_router(codes.router)
app.include_router(health.router)
app.include_router(verify.router)
app.include_router(compliance.router, prefix="/api/v1")
app.include_router(rates.router, prefix="/api/v1")
app.include_router(enrichment.router, prefix="/api/v1")
app.include_router(continuous_enrichment.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(telemetry.router, prefix="/api/v1")
app.include_router(developer_portal.router, prefix="/api/v1")
app.include_router(gov_integration.router, prefix="/api/v1")
app.include_router(arabic_i18n.router, prefix="/api/v1")
app.include_router(recalls.router, prefix="/api/v1")
app.include_router(suppliers.router, prefix="/api/v1")
app.include_router(insurance.router, prefix="/api/v1")
app.include_router(retention.router, prefix="/api/v1")
app.include_router(tiers.router, prefix="/api/v1")
app.include_router(esg.router, prefix="/api/v1")
app.include_router(monitoring.router)
app.include_router(startup.router, prefix="/api/v1")

from pathlib import Path as _Path
_FRONTEND_DIR = _Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
