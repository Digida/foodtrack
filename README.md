# FoodTrack — Phygital Trust Infrastructure

A full-stack food supply chain platform combining digital traceability, smart certification,
AI enrichment, and phygital identity (QR/NFC/barcode) into a single SaaS product.
Built for Dubai's agrifood sector and designed to scale across the GCC.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [Project Structure](#project-structure)
- [Running the Platform Locally](#running-the-platform-locally)
- [Environment Variables](#environment-variables)
- [Background Startup: Migrations & Seeding](#background-startup-migrations--seeding)
- [Database Migrations (manual)](#database-migrations-manual)
- [Running Tests](#running-tests)
- [Deploying to Render — Complete Step-by-Step](#deploying-to-render--complete-step-by-step)
- [Render Environment Variables Reference](#render-environment-variables-reference)
- [CI/CD Pipeline](#cicd-pipeline)
- [API Reference](#api-reference)
- [Multi-Tenancy & Tiers](#multi-tenancy--tiers)
- [Contributing](#contributing)

---

## Overview

FoodTrack is an item-first supply chain platform. The core unit is the **TaxonomyItem** —
the actual food (a banana, a tuna fillet, a bag of chia seeds) — not a shipment or container.
Every supply-chain artifact (certificate, batch, warehouse stock, shipment event) resolves
back to a taxonomy item.

**Target market:** Dubai hospitality groups, food manufacturers, importers/exporters,
logistics providers, and government food-safety programmes.

**Business model:** SaaS tiers (Free → Growth → Enterprise → Government) + enterprise
licensing + digital certification services + data analytics.

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

The entire application (backend API + frontend static files) runs as a **single service**.
FastAPI serves the frontend via `StaticFiles` mounted at `/`, so no separate frontend
server is needed in development or production.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.115, Python 3.11 |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 (production) / SQLite (development) |
| Migrations | Alembic 1.13 (12 migration files) |
| Auth | JWT (python-jose), bcrypt |
| QR / Barcode | qrcode, python-barcode, Pillow |
| Tracing | OpenTelemetry (optional, degrades gracefully) |
| Server | Uvicorn (dev + production) |
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
| 13 | Alembic migrations (12 migration files) | ✅ |
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
| 29 | Background incremental migrations + seeding with live status | ✅ |

---

## Project Structure

```
FoodTrack/
├── main.py                      ← SINGLE ENTRY POINT — run this to start everything
├── start.bat                    ← Windows double-click launcher (delegates to main.py)
├── start.ps1                    ← PowerShell launcher (delegates to main.py)
├── start-port.bat               ← Custom-port Windows launcher
├── run_smoke.ps1                ← Local smoke test script (36 endpoint checks)
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, middleware, route registration
│   │   ├── config.py            # Settings from environment variables
│   │   ├── database.py          # Async SQLAlchemy engine + session
│   │   ├── models/              # SQLAlchemy ORM models (20 files)
│   │   ├── routes/              # FastAPI routers (one file per domain, 30+ files)
│   │   ├── services/            # Business logic layer
│   │   │   └── startup_service.py  # Background migration + seeding engine
│   │   ├── middleware/          # API key middleware
│   │   ├── schemas.py           # Pydantic response models
│   │   └── i18n/                # en.json, ar.json translation files
│   ├── alembic/
│   │   └── versions/            # 12 migration files
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_routes/
│   │   └── test_services/
│   ├── tools/                   # 20 pluggable tool modules
│   ├── seed_food_items.py        # 120+ base food taxonomy items
│   ├── seed_more_items.py        # 200+ additional items (21 categories total)
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── .env.example
│   └── alembic.ini
├── frontend/
│   ├── index.html
│   ├── js/                      # app.js, pages.js, api.js, auth.js, router.js
│   ├── css/
│   └── assets/
├── docs/
│   ├── deploy.md
│   └── pending.md
└── .github/workflows/ci.yml
```

---

## Running the Platform Locally

### Prerequisites

- Python 3.11 or 3.12
- Git

SQLite is used by default for local development — no database installation needed.

### First-time setup

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
# Windows
copy backend\.env.example backend\.env

# macOS / Linux
cp backend/.env.example backend/.env
# The defaults work as-is for local SQLite development.
# Only change DATABASE_URL if you want to point at PostgreSQL locally.
```

### Starting the platform — one command from the project root

```bash
python main.py
```

That single command:
1. Detects your virtual environment automatically
2. Starts the server immediately (you can open the browser right away)
3. Runs Alembic migrations in the background
4. Seeds the full 298-item food taxonomy catalogue in the background
5. Shows a live progress banner in the frontend until everything is ready

#### All launcher options

```bash
python main.py                   # development mode — SQLite, auto-reload, debug logs
python main.py --port 9000       # run on a custom port
python main.py --prod            # production mode — Uvicorn, info logs, no reload
python main.py --prod --workers 4  # production with explicit worker count
python main.py --run-migrate     # run migrations synchronously BEFORE starting
                                 # (useful for CI or one-off provisioning)
python main.py --log-level debug # override log level
```

#### Convenience launchers (same as `python main.py`)

```bash
# Windows Command Prompt
start.bat
start.bat --prod
start-port.bat 9000

# PowerShell
.\start.ps1
.\start.ps1 --prod --port 9000
```

### What opens where

| URL | What you get |
|-----|-------------|
| `http://localhost:8000/` | Frontend application |
| `http://localhost:8000/docs` | Swagger UI — interactive API explorer |
| `http://localhost:8000/redoc` | ReDoc API reference |
| `http://localhost:8000/health` | Health check (DB connectivity) |
| `http://localhost:8000/api/v1/startup/status` | Live migration + seeding progress |

### Testing interactively

The quickest way to explore the API is through Swagger at `http://localhost:8000/docs`.

1. Open `/docs`
2. Click **POST /api/v1/auth/register** → fill in email, password, name → Execute
3. Click **POST /api/v1/auth/login** → enter same credentials → copy the `access_token`
4. Click the **Authorize** button (top right) → paste the token → Authorize
5. All authenticated endpoints are now unlocked

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env`.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | `change-me` | JWT signing key — must be changed in production |
| `ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `60` | Token lifetime in minutes |
| `DATABASE_URL` | Yes | SQLite | Full async connection string (see formats below) |
| `SITE_URL` | No | `http://localhost:8000` | Public URL of the deployed app |
| `CORS_ORIGINS` | No | `SITE_URL` | Comma-separated allowed CORS origins |
| `PYTHON_VERSION` | No | — | Pin for Render (e.g. `3.11.0`) |
| `EMAIL_API_URL` | No | — | Transactional email endpoint for OTP MFA |
| `EMAIL_API_KEY` | No | — | Bearer token for email service |
| `SMS_API_URL` | No | — | SMS gateway endpoint for phone OTP MFA |
| `SMS_API_KEY` | No | — | Bearer token for SMS gateway |

**DATABASE_URL formats:**

```bash
# SQLite (development only — zero config)
DATABASE_URL=sqlite+aiosqlite:///./foodtrack.db

# PostgreSQL (staging / production)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/foodtrack
```

> The `+asyncpg` driver suffix is required. Render provides URLs as `postgresql://` —
> you must manually change the scheme to `postgresql+asyncpg://`.

**Generating a secure SECRET_KEY:**

```bash
# Windows
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"

# macOS / Linux
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

> The server will refuse to start with `SECRET_KEY=change-me` when pointed at a
> PostgreSQL database. This safety guard is intentional.

---

## Background Startup: Migrations & Seeding

FoodTrack uses a non-blocking background startup system. The server starts and
accepts requests immediately. Migrations and seeding run behind it as a background
asyncio task.

### How it works

```
python main.py
    │
    ├── Server binds and accepts requests   ← instant
    │
    └── Background task starts
            │
            ├── Phase 1: Migrations
            │       alembic upgrade head (only pending revisions)
            │       Skips if already at head — sub-second
            │
            └── Phase 2: Seeding (incremental)
                    For each of 21 categories:
                      1. SELECT existing item codes from DB
                      2. Compare against catalogue (298 items total)
                      3. INSERT only what is missing
                      4. Commit every 10 rows (progress survives restarts)
                      5. yield to event loop (server stays responsive)
```

### Checking progress

```bash
# Full status — phase, migration revision, per-section counts
GET /api/v1/startup/status

# Minimal check — 200 when done, 503 while initialising
GET /api/v1/startup/ready

# Per-section check — is a specific data section ready?
GET /api/v1/startup/section/SEAFOOD
GET /api/v1/startup/section/GRAINS
```

**Example status response while seeding:**

```json
{
  "ready": false,
  "phase": "seeding",
  "migration": { "status": "done", "current": "c1d2e3f4a5b6" },
  "seeding": {
    "status": "running",
    "total_inserted": 87,
    "sections": {
      "GRAINS":          { "status": "done",    "expected": 15, "seeded": 15, "missing": 0 },
      "LEGUMES":         { "status": "done",    "expected": 13, "seeded": 13, "missing": 0 },
      "TROPICAL_FRUITS": { "status": "running", "expected": 14, "seeded": 6,  "missing": 8 },
      "SEAFOOD":         { "status": "pending", "expected": 8,  "seeded": 0,  "missing": 8 }
    }
  }
}
```

### Frontend progress banner

While the platform is initialising the frontend shows a fixed top banner:

```
🌱 Seeding catalogue data — 14/21 sections complete    [████████░░░░]   87 items added
```

It fades out automatically 3 seconds after `ready: true`.

### User-facing feedback when data is not yet ready

If a user requests data from a section that has not been seeded yet, the API returns
a descriptive 503 instead of a database error:

```json
{
  "error": "data_not_ready",
  "section": "SEAFOOD",
  "status": "pending",
  "message": "The 'SEAFOOD' dataset is still being initialised in the background.
              Please retry in a few seconds.
              Check /api/v1/startup/status for live progress."
}
```

---

## Database Migrations (manual)

Migrations run automatically in the background on every startup. Use these commands
for manual control, CI pipelines, or schema development.

```bash
cd backend

# Apply all pending migrations (run from backend/)
alembic upgrade head

# Check current revision
alembic current

# Show pending migrations
alembic history --indicate-current

# Create a new migration after changing a model
alembic revision --autogenerate -m "describe your change"

# Roll back one migration
alembic downgrade -1

# Roll back all the way to an empty schema
alembic downgrade base
```

There are 12 migration files covering the full schema. Running `alembic upgrade head`
on a fresh PostgreSQL database applies all of them in order.

---

## Running Tests

```bash
cd backend

# Run all tests with coverage
pytest --cov=app --cov-report=term-missing

# Run a specific domain
pytest tests/test_services/test_auth_service.py -v

# Run all boundary / security tests
pytest tests/test_routes/test_auth_boundaries.py -v

# Skip coverage (faster iteration)
pytest tests/
```

The CI pipeline enforces a minimum 70% coverage gate.

### Test database

Tests use an in-memory SQLite database (`test_foodtrack.db`) that is created before
each test and dropped after. No external services are required to run the test suite.

---

## Deploying to Render — Complete Step-by-Step

FoodTrack deploys as a single **Render Web Service** (Python runtime, no Docker).
The frontend is served by FastAPI, so one service handles everything.

---

### Step 1 — Create a PostgreSQL database

1. Log in to [render.com](https://render.com)
2. Click **New** → **PostgreSQL**
3. Fill in:
   - **Name:** `foodtrack-db`
   - **Region:** Singapore (Southeast Asia) — or match where your users are
   - **Plan:** Free (testing) or Starter ($7/month, always-on)
4. Click **Create Database**
5. Wait ~1 minute for provisioning, then click into the database
6. Under **Connections**, copy the **Internal Database URL**

   It will look like:
   ```
   postgresql://foodtrack_user:AbCdEf123@dpg-abc123.singapore-postgres.render.com/foodtrack_db
   ```

7. **Change the scheme** from `postgresql://` to `postgresql+asyncpg://`:
   ```
   postgresql+asyncpg://foodtrack_user:AbCdEf123@dpg-abc123.singapore-postgres.render.com/foodtrack_db
   ```
   Save this — you will paste it as `DATABASE_URL` in Step 3.

---

### Step 2 — Create the Web Service

1. In the Render dashboard, click **New** → **Web Service**
2. Under **Source Code**, connect your GitHub account if not already connected,
   then select the `Digida/foodtrack` repository
3. Fill in the following fields exactly:

| Field | Value |
|-------|-------|
| **Name** | `foodtrack` |
| **Project** | `foodtrack` (or create a new project with that name) |
| **Environment** | `Production` |
| **Language** | `Python 3` |
| **Branch** | `main` |
| **Region** | `Singapore (Southeast Asia)` — same as your database |
| **Root Directory** | `backend` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Plan** | Free (testing) or Starter ($7/month, recommended) |

> **Root Directory is critical.** Setting it to `backend` tells Render to run all
> commands from the `backend/` folder where `requirements.txt` and `alembic.ini` live.
> If you leave it blank the build will fail with "No module named app".

> **Do not use Gunicorn in the Start Command.** The app uses async SQLAlchemy which
> requires a single async event loop per process. Uvicorn handles this correctly.
> Migrations and seeding run automatically inside the app's lifespan task — the
> Start Command does not need to run `alembic upgrade head` first.

---

### Step 3 — Set environment variables

Still on the Web Service creation page, scroll down to **Environment Variables**.
Click **Add Environment Variable** for each row below:

| Key | Value | Notes |
|-----|-------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | The modified URL from Step 1 |
| `SECRET_KEY` | *(generated — see below)* | Required — server refuses to start without it |
| `ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | |
| `SITE_URL` | `https://foodtrack.onrender.com` | Update after first deploy with the actual URL |
| `CORS_ORIGINS` | `https://foodtrack.onrender.com` | Same as SITE_URL |
| `PYTHON_VERSION` | `3.11.0` | Pins the Python version Render uses |

**Generating SECRET_KEY — run this locally and paste the output:**

```powershell
# Windows
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
```

```bash
# macOS / Linux
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Example output (use yours, not this one):
```
xK9mP2nQrT5vW8yBzD1eF4hJ7kL0oA3cG6iN9qS2uV5xY8bE1fH4jM7pR0sU3wX6
```

---

### Step 4 — Deploy

Click **Create Web Service**. Render will:

1. Pull the `main` branch from GitHub
2. Change into the `backend/` directory (Root Directory setting)
3. Run `pip install -r requirements.txt` (Build Command)
4. Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (Start Command)

The first deploy takes 3–5 minutes (dependency install + cold start).

**What happens inside the app on first boot:**

1. Uvicorn starts — Render's health check passes within seconds
2. Background task fires automatically:
   - Runs `alembic upgrade head` → creates all 12 tables on the fresh PostgreSQL DB
   - Incrementally seeds 298 taxonomy items across 21 categories
3. The frontend becomes fully functional once seeding completes (~30 seconds)

---

### Step 5 — Watch the startup progress

Once the service shows **Live** in the Render dashboard, open:

```
https://foodtrack.onrender.com/api/v1/startup/status
```

You will see the seeding progress in real time:

```json
{
  "ready": false,
  "phase": "seeding",
  "seeding": {
    "total_inserted": 45,
    "sections": {
      "GRAINS":   { "status": "done",    "seeded": 15 },
      "LEGUMES":  { "status": "done",    "seeded": 13 },
      "SEAFOOD":  { "status": "running", "seeded": 6, "missing": 2 },
      "MUSHROOMS":{ "status": "pending", "seeded": 0, "missing": 12 }
    }
  }
}
```

When all sections show `"status": "done"` and `"ready": true`, the platform is fully loaded.

---

### Step 6 — Verify the deployment

```
GET https://foodtrack.onrender.com/health
→ {"status": "ok", "database": "connected", "timestamp": "..."}

GET https://foodtrack.onrender.com/docs
→ Swagger UI with all 100+ endpoints

GET https://foodtrack.onrender.com/api/v1/startup/ready
→ {"ready": true, "phase": "done"}  ← when fully initialised

GET https://foodtrack.onrender.com/
→ FoodTrack frontend application
```

---

### Step 7 — Update SITE_URL after first deploy

Once the service is live Render assigns a URL like `https://foodtrack.onrender.com`.

1. In the Web Service settings → **Environment**
2. Update `SITE_URL` to `https://foodtrack.onrender.com`
3. Update `CORS_ORIGINS` to the same value
4. Render will automatically redeploy with the new values

---

### Step 8 — Custom domain (optional)

1. In the Web Service settings → **Settings** → **Custom Domain**
2. Enter your domain (e.g. `app.foodtrack.ae`)
3. Add a CNAME record at your DNS provider pointing to `foodtrack.onrender.com`
4. Wait for SSL certificate provisioning (~5 minutes)
5. Update `SITE_URL` and `CORS_ORIGINS` to `https://app.foodtrack.ae`

---

### Render architecture summary

```
GitHub (Digida/foodtrack)
    │  push to main
    ▼
Render Build
    ├── cwd: backend/
    └── pip install -r requirements.txt

Render Web Service: foodtrack
    ├── Start: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    ├── Lifespan background task:
    │     ├── alembic upgrade head (PostgreSQL)
    │     └── incremental seed (298 taxonomy items)
    ├── API     → https://foodtrack.onrender.com/api/v1/...
    ├── Docs    → https://foodtrack.onrender.com/docs
    ├── Frontend → https://foodtrack.onrender.com/
    └── Status  → https://foodtrack.onrender.com/api/v1/startup/status

Render PostgreSQL: foodtrack-db
    └── Internal URL → DATABASE_URL env var (postgresql+asyncpg://...)
```

---

### Free plan limitations

Render's free plan spins down services after 15 minutes of inactivity. The first
request after a spin-down takes 30–60 seconds while the container wakes up.
Use the **Starter plan ($7/month)** for always-on production behaviour.

The free PostgreSQL plan expires after 90 days. Upgrade to a paid plan before
expiry to avoid data loss.

---
