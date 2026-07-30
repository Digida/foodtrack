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

## Render Deployment (No Docker — Native Python)

Deploy directly from GitHub to Render using the native Python runtime. No Dockerfile needed.

### Architecture

```
Render Web Service
  └─ backend/  →  FastAPI served via uvicorn/gunicorn
  └─ frontend/ →  Static files mounted by FastAPI at /
  └─ PostgreSQL Database (Render add-on)
```

The entire app (backend API + frontend static files) runs as a single Render Web Service. The frontend is served by FastAPI's `StaticFiles` mount at `app.main.py:96`.

### Setup Steps

1. **Push to GitHub** (see below)
2. **Create a Render account** at https://render.com
3. **New Web Service** → Connect your `digida/foodtrack` repo
4. **Configure**:

   | Setting | Value |
   |---------|-------|
   | **Name** | `foodtrack-api` |
   | **Runtime** | `Python 3` |
   | **Build Command** | `pip install -r backend/requirements.txt` |
   | **Start Command** | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | **Plan** | Starter (or Free) |

5. **Add Environment Variables** in Render dashboard:

   | Variable | Value |
   |----------|-------|
   | `DATABASE_URL` | `postgresql+asyncpg://foodtrack:pass@host:5432/foodtrack` |
   | `SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
   | `ALGORITHM` | `HS256` |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
   | `SITE_URL` | `https://foodtrack-api.onrender.com` |
   | `PYTHON_VERSION` | `3.12.0` |

6. **Add a PostgreSQL Database** in Render:
   - Go to Dashboard → New → PostgreSQL
   - Copy the internal connection string
   - Set it as `DATABASE_URL` in your Web Service environment

7. **Run migrations** once the DB is ready:
   - Go to Render Dashboard → Your Web Service → Shell
   - Run: `cd backend && alembic upgrade head`

8. **Deploy** — Render auto-deploys on every push to `main`

### Health Check

Render will automatically ping:
```
GET /health → {"status": "ok", "database": "connected"}
```

### Custom Domain

1. Render Dashboard → Your Web Service → Settings → Custom Domain
2. Add your domain (e.g., `api.foodtrack.ae`)
3. Update DNS CNAME to point to `onrender.com`
4. Update `SITE_URL` env var

### Updating API Base URL

The frontend uses relative paths (`/api/v1/...`) which proxy to the same Render service. For production with a custom domain, update [`frontend/js/api.js`](../frontend/js/api.js):
```js
const API_BASE = 'https://api.foodtrack.ae/api/v1';
```

---

## Push to GitHub

```bash
# From project root (D:\Work\clients\FoodTrack)
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

> **Note:** If you get `403 Permission denied`, your machine has cached credentials for another GitHub account. Run this to clear them and try again:
> ```
> cmdkey /delete:git:https://github.com
> git push -u origin main
> ```
> A browser will open — log in as **digida** to authenticate.
