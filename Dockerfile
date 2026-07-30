# ── FoodTrack — Dockerfile for Render ──────────────────────
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy entire project
COPY . .

# Expose port
EXPOSE 10000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:10000/health')"

# Run with gunicorn + uvicorn workers
CMD cd backend && gunicorn run:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:10000 \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -