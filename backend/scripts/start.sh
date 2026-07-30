#!/usr/bin/env bash
set -euo pipefail

HOST="${1:-0.0.0.0}"
PORT="${2:-8000}"
RELOAD="${3:-}"

cd "$(dirname "$0")/.."

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running database migrations..."
alembic upgrade head || { echo "Migration failed"; exit 1; }

if [ -n "$RELOAD" ]; then
    echo "Starting uvicorn with reload on $HOST:$PORT"
    exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
else
    echo "Starting uvicorn on $HOST:$PORT"
    exec uvicorn app.main:app --host "$HOST" --port "$PORT"
fi
