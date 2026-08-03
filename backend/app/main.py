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
    commerce,
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


# ────────────────────────────────────────────────────────────────
# 🛡️ Request body size limit (multi-GB POST protection) — B7
# ────────────────────────────────────────────────────────────────

MAX_BODY_SIZE = int(_os.getenv("MAX_BODY_SIZE", "10_485_760"))  # 10 MB default

@app.middleware("http")
async def body_size_limit_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        from fastapi.responses import PlainTextResponse
        logger.warning({
            "event": "body_too_large",
            "method": request.method,
            "path": request.url.path,
            "content_length": int(content_length),
            "max_size": MAX_BODY_SIZE,
        })
        return PlainTextResponse(
            f"Request body too large. Maximum size is {MAX_BODY_SIZE} bytes.",
            status_code=413,
        )
    return await call_next(request)


# ────────────────────────────────────────────────────────────────
# 🛡️ Rate limiting (login brute-force, public endpoints) — B6
# ────────────────────────────────────────────────────────────────

from collections import defaultdict
import asyncio as _asyncio

RATE_LIMIT_WINDOW = int(_os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
RATE_LIMIT_MAX = int(_os.getenv("RATE_LIMIT_MAX", "100"))        # requests per window

_rate_limit_buckets: dict[str, list[float]] = defaultdict(list)
_rate_limit_lock = _asyncio.Lock()  # single lock — good enough for in-memory

@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    # Apply to API routes only. Static assets (JS/CSS/images served by the
    # frontend mount) and infra endpoints must never be throttled — doing so
    # would 429 the app's own assets and break the UI under normal load.
    path = request.url.path
    if not path.startswith("/api/"):
        return await call_next(request)
    # Public endpoints get stricter limits
    is_public = any(path.startswith(p) for p in [
        "/api/v1/auth/login", "/api/v1/auth/register",
        "/api/v1/auth/send-otp", "/api/v1/auth/verify-otp",
        "/api/v1/verify/", "/api/v1/contact",
        "/api/v1/search", "/api/v1/search/autocomplete",
        "/api/v1/health",
    ])

    window = RATE_LIMIT_WINDOW
    max_reqs = min(RATE_LIMIT_MAX, 30) if is_public else RATE_LIMIT_MAX

    # Use client IP as rate limit key
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{path.split('/')[3] if len(path.split('/')) > 3 else 'other'}"

    async with _rate_limit_lock:
        now = time.time()
        bucket = _rate_limit_buckets.get(key, [])
        window_start = now - window
        bucket = [t for t in bucket if t > window_start]

        if len(bucket) >= max_reqs:
            logger.warning({
                "event": "rate_limit_exceeded",
                "key": key,
                "client_ip": client_ip,
                "path": path,
                "limit": max_reqs,
                "window": window,
            })
            from fastapi.responses import JSONResponse
            return JSONResponse(
                {"detail": "Rate limit exceeded. Try again later."},
                status_code=429,
                headers={"Retry-After": str(window)},
            )

        bucket.append(now)
        _rate_limit_buckets[key] = bucket

    return await call_next(request)


# ────────────────────────────────────────────────────────────────
# X-API-Key authentication + per-key rate limiting (Developer Portal keys).
# ────────────────────────────────────────────────────────────────
from app.middleware.api_key_middleware import api_key_middleware
app.middleware("http")(api_key_middleware)

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
app.include_router(verify.router, prefix="/api/v1")
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
app.include_router(commerce.router, prefix="/api/v1")

from pathlib import Path as _Path
_FRONTEND_DIR = _Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")