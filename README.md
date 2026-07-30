# FoodTrack — Phygital Trust Infrastructure

A full-stack food supply chain platform combining digital traceability, smart certification, AI enrichment, and phygital identity (QR/NFC/barcode) into a single SaaS product. Built for Dubai's agrifood sector and designed to scale across the GCC.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Project Structure](#project-structure)
- [Local Development](#local-development)
- [Environment Variables](#environment-variables)
- [Database Migrations](#database-migrations)
- [Running Tests](#running-tests)
- [Deploying to Render](#deploying-to-render)
- [CI/CD Pipeline](#cicd-pipeline)
- [API Reference](#api-reference)
- [Multi-Tenancy & Tiers](#multi-tenancy--tiers)
- [Contributing](#contributing)

---

## Overview

FoodTrack is an item-first supply chain platform. The core unit is the **TaxonomyItem** — the actual food (a banana, a tuna fillet, a bag of chia seeds) — not a shipment or container. Every supply-chain artifact (certificate, batch, warehouse stock, shipment event) resolves back to a taxonomy item.

**Target market:** Dubai hospitality groups, food manufacturers, importers/exporters, logistics providers, and government food-safety programmes.

**Business model:** SaaS tiers (Free → Growth → Enterprise → Government) + enterprise licensing + digital certification services + data analytics.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      TAXONOMY ITEM                        │
│   (atomic unit — a banana, a coffee bean, a fish fillet) │
├─────────────────┬────────────────────┬────────────────────┤
│  ITEM DETAIL    │   ITEM STORAGE     │   ITEM MOVEMENT    │
│  (digital twin) │   (aggregated)     │   (lifecycle)      │
├─────────────────┼────────────────────┼────────────────────┤
│  Certificates   │   Warehouses       │   Batches          │
│  Traceability   │   Zones / Bins     │   Shipments        │
│  Media/Attach   │   Stock levels     │   Tracking events  │
│  QR/NFC/Barcode │   Cold chain       │   ETAs / delays    │
│  Provenance     │   Capacity         │   Transshipments   │
└─────────────────┴────────────────────┴────────────────────┘
```

The entire application (backend API + frontend static files) runs as a **single service**. FastAPI serves the Vue/vanilla-JS frontend via `StaticFiles` mounted at `/`, so no separate frontend host is needed.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.115, Python 3.12 |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 (production) / SQLite (development) |
| Migrations | Alembic 1.13 |
| Auth | JWT (python-jose), bcrypt |
| QR / Barcode | qrcode, python-barcode, Pillow |
| Tracing | OpenTelemetry (optional, degrades gracefully) |
| Server | Uvicorn / Gunicorn |
| CI | GitHub Actions |
| Hosting | Render (native Python, no Docker) |
| Frontend | Vanilla JS + CSS (served by FastAPI) |

---

## Features

| # | Feature | Status |
|---|---------|--------|
| 1 | Item detail engine — digital twin per taxonomy item | ✅ |
| 2 | Item storage aggregation across warehouses | ✅ |
| 3 | Item movement tracking + cargo registration | ✅ |
| 4 | Digital certification (17 cert types, request/review flow) | ✅ |
| 5 | Phygital identity — QR, NFC, EAN-13 barcode | ✅ |
| 6 | Provenance & traceability timeline | ✅ |
| 7 | AI item enrichment (nutrition, pricing, translation) | ✅ |
| 8 | Item-specific rate cards & shipping cost calculator | ✅ |
| 9 | Dubai import compliance dashboard | ✅ |
| 10 | Item-centric analytics (top-moved, low-stock, cert gaps) | ✅ |
| 11 | Multilingual search with fuzzy matching & analytics | ✅ |
| 12 | Continuous enrichment from RSS feeds & web sources | ✅ |
| 13 | Alembic migrations (11 migration files) | ✅ |
| 14 | Multi-tenancy with JWT-scoped tenant isolation | ✅ |
| 15 | Async test suite (pytest + pytest-asyncio) | ✅ |
| 16 | Real-time events via WebSocket + webhooks | ✅ |
| 17 | IoT cold-chain telemetry with alert rules | ✅ |
| 18 | Developer portal with API key management & rate limiting | ✅ |
| 19 | SaaS tier model (Free / Growth / Enterprise / Government) | ✅ |
| 20 | Data retention policies with automated archival | ✅ |
| 21 | Monitoring: structured JSON logs, `/metrics`, SLA dashboard | ✅ |
| 22 | Dubai government integration (Dubai Trade, MOCCAE, ESMA) | ✅ |
| 23 | Arabic i18n with Accept-Language middleware | ✅ |
| 24 | ESG / carbon footprint tracking per item | ✅ |
| 25 | Batch recall workflow with affected-shipment tracing | ✅ |
| 26 | Supplier scorecards & ranking | ✅ |
| 27 | Cargo insurance policies & claims | ✅ |
| 28 | Consumer public portal — scan QR to verify item + certs | ✅ |

---

## Project Structure

```
FoodTrack/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, middleware, route registration
│   │   ├── config.py            # Settings from environment variables
│   │   ├── database.py          # Async SQLAlchemy engine + session
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── routes/              # FastAPI routers (one file per domain)
│   │   ├── services/            # Business logic layer
│   │   ├── middleware/          # API key middleware
│   │   └── i18n/                # en.json, ar.json translation files
│   ├── alembic/
│   │   └── versions/            # 11 migration files
│   ├── tests/
│   │   ├── conftest.py          # Async test DB, fixtures
│   │   ├── test_models/
│   │   ├── test_routes/
│   │   ├── test_services/
│   │   └── test_tools/
│   ├── tools/                   # 20 pluggable tool modules
│   ├── scripts/                 # start.sh / start.ps1 / setup_db.ps1
│   ├── requirements.txt
│   ├── .env.example
│   └── alembic.ini
├── frontend/
│   ├── index.html
│   ├── js/
│   ├── css/
│   └── assets/
├── docs/
│   ├── deploy.md                # Bare-metal + Render deployment guide
│   └── pending.md               # Feature roadmap and architecture notes
└── .github/
    └── workflows/
        └── ci.yml               # Lint → migrate → test pipeline
```

---

## Local Development

### Prerequisites

- Python 3.12+
- Git

SQLite is used by default for local development — no database installation needed.

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/Digida/foodtrack.git
cd foodtrack

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Copy and configure the environment file
cp backend/.env.example backend/.env
# Edit backend/.env if needed (defaults work for local SQLite dev)

# 5. Run database migrations
cd backend
alembic upgrade head

# 6. Start the development server
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`.  
Swagger UI: `http://localhost:8000/docs`  
ReDoc: `http://localhost:8000/redoc`  
Frontend: `http://localhost:8000/`

### Quick-start scripts

```bash
# Windows PowerShell
.\backend\scripts\start.ps1

# macOS / Linux
chmod +x backend/scripts/start.sh && ./backend/scripts/start.sh
```

These scripts install dependencies, run migrations, and start the server in one step.

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and set the values below.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | `change-me` | JWT signing key — use a random 64-char string in production |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | JWT token lifetime in minutes |
| `DATABASE_URL` | Yes | SQLite | Full connection string (see formats below) |
| `SITE_URL` | No | `http://localhost:8000` | Public URL of the deployed app |

**DATABASE_URL formats:**

```bash
# SQLite (development only)
DATABASE_URL=sqlite+aiosqlite:///./foodtrack.db

# PostgreSQL (staging / production)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/foodtrack
```

**Generating a secure SECRET_KEY:**

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## Database Migrations

FoodTrack uses Alembic for schema management. All migrations live in `backend/alembic/versions/`.

```bash
# Apply all pending migrations
cd backend
alembic upgrade head

# Create a new migration after changing a model
alembic revision --autogenerate -m "describe your change"

# Roll back one migration
alembic downgrade -1

# Show current migration state
alembic current
```

There are 11 migration files covering the full schema. Running `alembic upgrade head` on a fresh database will apply all of them in order.

---

## Running Tests

```bash
cd backend

# Run all tests with coverage
pytest --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_routes/test_health.py -v

# Run tests without coverage (faster)
pytest tests/
```

The CI pipeline enforces a minimum 70% coverage gate (`--cov-fail-under=70`).

---

## Deploying to Render

FoodTrack deploys as a single **Render Web Service** using the native Python runtime. No Docker or containerisation is required.

The frontend is served directly by FastAPI via `StaticFiles`, so one service handles everything.

### Step 1 — Create a PostgreSQL database on Render

1. Log in to [render.com](https://render.com) and go to your dashboard
2. Click **New** → **PostgreSQL**
3. Choose a name (e.g., `foodtrack-db`), select a region, and click **Create Database**
4. Once created, copy the **Internal Database URL** — you will need it in Step 3

### Step 2 — Create a Web Service

1. In the Render dashboard, click **New** → **Web Service**
2. Connect your GitHub repository (`Digida/foodtrack`)
3. Configure the service with these settings:

| Setting | Value |
|---------|-------|
| **Name** | `foodtrack-api` |
| **Region** | Same region as your PostgreSQL database |
| **Branch** | `main` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r backend/requirements.txt` |
| **Start Command** | `cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Starter (or Free for testing) |

> The start command runs migrations automatically on every deploy before starting the server.

### Step 3 — Set environment variables

In the Web Service settings, go to **Environment** and add:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Internal connection string from Step 1 (change `postgresql://` to `postgresql+asyncpg://`) |
| `SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
| `SITE_URL` | `https://foodtrack-api.onrender.com` (update after first deploy) |
| `PYTHON_VERSION` | `3.12.0` |

> **Important:** Render provides the DATABASE_URL as `postgresql://...`. You must change the scheme to `postgresql+asyncpg://` for the async driver to work.

### Step 4 — Deploy

Click **Create Web Service**. Render will:
1. Pull the repository
2. Run the build command (`pip install`)
3. Run the start command (`alembic upgrade head` then `uvicorn`)

The first deploy takes 2–4 minutes. Subsequent pushes to `main` trigger automatic redeployment.

### Step 5 — Verify the deployment

Once the service is live, check these endpoints:

```
GET https://foodtrack-api.onrender.com/health
→ {"status": "ok", "database": "connected"}

GET https://foodtrack-api.onrender.com/docs
→ Swagger UI
```

### Step 6 — Custom domain (optional)

1. In the Web Service settings, go to **Settings** → **Custom Domain**
2. Add your domain (e.g., `api.foodtrack.ae`)
3. Update your DNS provider: add a CNAME record pointing to `foodtrack-api.onrender.com`
4. Update the `SITE_URL` environment variable to your custom domain

### Render architecture summary

```
Render Web Service (foodtrack-api)
  ├── Build: pip install -r backend/requirements.txt
  ├── Start: alembic upgrade head → uvicorn app.main:app
  ├── API routes → /api/v1/...
  ├── Frontend → / (StaticFiles from ../frontend)
  └── Health check → /health

Render PostgreSQL (foodtrack-db)
  └── Internal URL → DATABASE_URL env var
```

### Notes on the free plan

Render's free plan spins down services after 15 minutes of inactivity. The first request after a spin-down takes 30–60 seconds. Use the Starter plan ($7/month) for always-on behaviour in production.

---

## CI/CD Pipeline

The GitHub Actions workflow at `.github/workflows/ci.yml` runs on every push and pull request to `main`:

1. **Lint** — `ruff` checks the backend code
2. **Migrate** — runs `alembic upgrade head` against a PostgreSQL service container
3. **Test** — runs `pytest --cov --cov-fail-under=70`

All three steps must pass before a PR can be merged.

---

## API Reference

The full interactive API reference is available at `/docs` (Swagger UI) and `/redoc` (ReDoc) on any running instance.

### Key endpoint groups

| Prefix | Description |
|--------|-------------|
| `POST /api/v1/auth/register` | Register a new user |
| `POST /api/v1/auth/login` | Get a JWT access token |
| `GET /api/v1/taxonomy/items` | Browse taxonomy items |
| `GET /api/v1/search?q=...` | Multilingual fuzzy search |
| `GET /api/v1/products` | Product management |
| `GET /api/v1/certificates` | Certificate management |
| `GET /api/v1/shipments` | Shipment tracking |
| `GET /api/v1/inventory` | Warehouse inventory |
| `GET /api/v1/compliance/items/{id}/dubai` | Dubai import compliance check |
| `GET /api/v1/analytics/items/top-moved` | Analytics dashboards |
| `POST /api/v1/telemetry/ingest` | IoT sensor data ingestion |
| `WS /api/v1/events/ws/{channel}` | Real-time WebSocket events |
| `GET /verify/{code}` | Public QR/barcode verification (no auth) |
| `GET /health` | Service health check |
| `GET /metrics` | Prometheus-style metrics |

### Authentication

All `/api/v1/` endpoints (except `/auth/` and public endpoints) require a JWT Bearer token:

```
Authorization: Bearer <token>
```

Or an API key for programmatic access:

```
X-API-Key: <key>
```

API keys are managed via the developer portal (`/api/v1/developer/api-keys`).

---

## Multi-Tenancy & Tiers

Every top-level resource (users, products, certificates, inventory, etc.) is scoped to a `tenant_id`. The JWT token carries the tenant context — users only see and interact with data belonging to their tenant.

### SaaS tiers

| Tier | Max Items | Max Users | Key Features |
|------|-----------|-----------|-------------|
| Free | 10 | 3 | View only, basic tracking |
| Growth | 1,000 | 25 | Certificates, analytics |
| Enterprise | Unlimited | Unlimited | AI enrichment, telemetry, webhooks, recalls, suppliers, insurance |
| Government | Unlimited | Unlimited | Everything + compliance, Dubai gov integration |

Tier is set per tenant and enforced via the `require_tier()` dependency on sensitive routes.

---

## Contributing

1. Fork the repository and create a branch from `main`
2. Follow the three-layer pattern: model → service → route
3. Add an Alembic migration for any schema change
4. Write tests mirroring the structure in `backend/tests/`
5. Ensure `pytest --cov=app --cov-fail-under=70` passes locally
6. Open a pull request — the CI pipeline must pass before review
