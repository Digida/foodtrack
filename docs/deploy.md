# Bare-Metal Deployment Guide

## Prerequisites
- Python 3.12+
- PostgreSQL 16+
- Git

## Quick Start (Development)

```bash
# Clone & enter
git clone <repo> && cd FoodTrack

# Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env — set DATABASE_URL for PostgreSQL

# Install & run
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Or use the launcher:

```bash
# Windows
.\backend\scripts\start.ps1

# Linux/macOS
chmod +x backend/scripts/start.sh && ./backend/scripts/start.sh
```

## Production Setup

### 1. PostgreSQL

```bash
# Create database and user
.\backend\scripts\setup_db.ps1

# Or manually:
sudo -u postgres createdb foodtrack
sudo -u postgres createuser foodtrack -P
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE foodtrack TO foodtrack;"
```

### 2. Environment

```env
# backend/.env
SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(64))">
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=postgresql+asyncpg://foodtrack:password@localhost:5432/foodtrack
SITE_URL=https://yourdomain.com
```

### 3. Systemd Service (Linux)

```ini
# /etc/systemd/system/foodtrack.service
[Unit]
Description=FoodTrack API
After=network.target postgresql.service

[Service]
Type=simple
User=foodtrack
Group=foodtrack
WorkingDirectory=/opt/foodtrack/backend
EnvironmentFile=/opt/foodtrack/backend/.env
ExecStartPre=/opt/foodtrack/backend/.venv/bin/alembic upgrade head
ExecStart=/opt/foodtrack/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 4. Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/ssl/certs/foodtrack.crt;
    ssl_certificate_key /etc/ssl/private/foodtrack.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 5. Log Rotation

```ini
# /etc/logrotate.d/foodtrack
/var/log/foodtrack/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

### 6. Health Check

```
GET /api/v1/health
→ {"status": "ok", "database": "connected"}
```

## CI Pipeline

GitHub Actions runs on push/PR:
- lint (ruff)
- migration (alembic upgrade head)
- tests (pytest --cov --cov-fail-under=70)

No Docker build step — tests run directly on ubuntu-latest with a PostgreSQL service container.

---

## Vercel Deployment (Frontend)

The [`frontend/`](../frontend) directory is a static SPA (Single Page Application) that can be deployed directly to Vercel.

### Architecture

```
Vercel (CDN)
  └─ frontend/    →  Served as static files via vercel.json
       └─ js/api.js  →  Points to your backend API URL
                        (configured via VITE_API_URL or in api.js)
```

The backend API (FastAPI + PostgreSQL) must be deployed separately on a VPS, Railway, or any Python-capable host.

### Setup Steps

1. **Push to GitHub** (instructions below)
2. **Go to** https://vercel.com → Import your `foodtrack` repo
3. **Configure**:
   - **Framework Preset**: `Other`
   - **Root Directory**: `./`
   - **Build Command**: _(none — static)_
   - **Output Directory**: `frontend`
4. **Add Environment Variable**:
   - `VITE_API_URL` → your backend URL (e.g., `https://api.foodtrack.ae`)
5. **Deploy** — Vercel deploys instantly

### Custom Domain

1. Go to Vercel Dashboard → Project → Domains
2. Add `foodtrack.ae` or any custom domain
3. Update DNS A/AAAA/CNAME records as Vercel directs
4. Update `VITE_API_URL` to match

### Updating API Base URL

Edit [`frontend/js/api.js`](../frontend/js/api.js) and change:
```js
const API_BASE = 'https://your-backend-url.com/api/v1';
```

Or use the Vercel env var at runtime.

---

## Backend API Deployment (Separate — e.g., Railway, DigitalOcean, VPS)

The FastAPI backend cannot run on Vercel (Python ASGI not supported on free plan). Deploy it elsewhere.

### Option A: Railway (Recommended for Quick Deploy)

1. Push to GitHub
2. Go to https://railway.app → New Project → Deploy from GitHub
3. Set start command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add env vars: `DATABASE_URL`, `SECRET_KEY`, etc.
5. Railway auto-provisions PostgreSQL if you add the plugin

### Option B: VPS (Bare-metal)

Follow the [Production Setup](#production-setup) section above.

---

## Push to GitHub

```bash
git init
git add -A
git commit -m "Initial commit: FoodTrack — Phygital Trust Infrastructure

Core features:
- 298 taxonomy items across 21 categories with multilingual names
- Item detail, storage aggregation, movement tracking
- Digital certification with 17 certificate types
- Phygital identity (QR/NFC/barcode)
- AI item enrichment
- Multilingual search with fuzzy matching & analytics
- Multi-tenancy with SaaS tier model
- Real-time events via WebSocket + webhooks
- IoT telemetry with alert rules
- Arabic i18n
- Dubai government compliance lookups
- ESG/carbon footprint tracking
- Batch recall workflow
- Supplier scorecards & ranking
- Insurance policy & claims
- SLA dashboard & OpenTelemetry tracing
- 50+ async tests"

git remote add origin https://github.com/digida/foodtrack.git
git branch -M main
git push -u origin main
```
