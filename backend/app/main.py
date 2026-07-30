import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routes import (
    auth, products, traceability, certificates, analytics, share, contact, taxonomy,
    search, batches, warehouses, shipments, collections, inventory, item_movements,
    codes, health, cargo, verify, compliance, rates, enrichment, continuous_enrichment,
    events, telemetry, developer_portal, gov_integration, arabic_i18n,
    recalls, suppliers, insurance, monitoring, retention, tiers, esg,
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
except ImportError:
    _otel_available = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    if _otel_available:
        FastAPIInstrumentor.instrument_app(app)
        logging.info("OpenTelemetry tracing enabled")
    await init_db()
    yield


app = FastAPI(title="FoodTrack - Digital Trust Infrastructure", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def structured_logging_and_sla(request: Request, call_next):
    from app.services.monitoring_service import record_request
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    record_request(duration_ms, response.status_code)

    # Structured JSON log every request
    logging.info(json.dumps({
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "duration_ms": duration_ms,
        "client": request.client.host if request.client else None,
    }))
    return response


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

app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
