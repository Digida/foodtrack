"""
FoodTrack — unified platform launcher.

Usage
-----
  python main.py                  # development mode (SQLite, auto-reload)
  python main.py --prod           # production mode (PostgreSQL, no reload, gunicorn workers)
  python main.py --port 9000      # override port
  python main.py --host 127.0.0.1 # bind to specific interface
  python main.py --skip-migrate   # skip Alembic migration step
  python main.py --workers 4      # number of Gunicorn workers (prod only)

Environment
-----------
All settings are read from backend/.env (or environment variables).
Copy backend/.env.example to backend/.env before first run.

This launcher is the single entry point for both local development and
production deployment. It mirrors exactly what Render's start command does:

  cd backend && alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT

Production uses Gunicorn with Uvicorn workers for multi-process concurrency.
Development uses Uvicorn's built-in reloader scoped to the app/ directory.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT    = Path(__file__).resolve().parent          # d:/Work/clients/FoodTrack
BACKEND = ROOT / "backend"                         # d:/Work/clients/FoodTrack/backend
FRONTEND = ROOT / "frontend"                       # d:/Work/clients/FoodTrack/frontend


# ── Python / venv resolution ──────────────────────────────────────────────────

def _find_python() -> str:
    """
    Return the Python executable to use, in priority order:
      1. backend/venv  (backend-local venv)
      2. .venv         (root-level venv)
      3. sys.executable (whatever launched this script)
    """
    candidates = [
        BACKEND / "venv" / "Scripts" / "python.exe",   # Windows backend venv
        BACKEND / "venv" / "bin" / "python",            # Unix backend venv
        ROOT / ".venv" / "Scripts" / "python.exe",      # Windows root venv
        ROOT / ".venv" / "bin" / "python",              # Unix root venv
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return sys.executable


# ── Argument parsing ───────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="FoodTrack platform launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--prod",         action="store_true", help="Production mode (Gunicorn + no reload)")
    p.add_argument("--host",         default="0.0.0.0",   help="Bind host (default: 0.0.0.0)")
    p.add_argument("--port",         type=int, default=None, help="Port (default: 8000, or $PORT env var)")
    p.add_argument("--workers",      type=int, default=None, help="Gunicorn workers [prod only] (default: CPU*2+1)")
    p.add_argument("--run-migrate",  action="store_true",
                   help="Run Alembic migrations synchronously BEFORE starting "
                        "(default: migrations run in the background after startup)")
    p.add_argument("--log-level",    default=None, choices=["debug","info","warning","error"],
                   help="Log level (default: debug in dev, info in prod)")
    return p.parse_args()


# ── Pre-flight checks ─────────────────────────────────────────────────────────

def _check_env():
    env_file = BACKEND / ".env"
    if not env_file.exists():
        example = BACKEND / ".env.example"
        print(f"\n  WARNING: {env_file} not found.")
        if example.exists():
            print(f"  Copy the example file to get started:")
            print(f"    copy backend\\.env.example backend\\.env   (Windows)")
            print(f"    cp backend/.env.example backend/.env      (Unix)")
        print()


def _check_frontend():
    index = FRONTEND / "index.html"
    if not index.exists():
        print(f"\n  WARNING: {index} not found — frontend will not be served.\n")


def _run(cmd: list[str], cwd: Path, label: str):
    """Run a subprocess and exit with its return code on failure."""
    print(f"\n  [{label}] {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(cwd))
    if result.returncode != 0:
        print(f"\n  ERROR: {label} failed (exit {result.returncode}). Aborting.\n")
        sys.exit(result.returncode)


# ── Migration ─────────────────────────────────────────────────────────────────

def _migrate(python: str):
    _run([python, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, label="Alembic migration")


# ── Server startup ────────────────────────────────────────────────────────────

def _start_dev(python: str, host: str, port: int, log_level: str):
    """Development: Uvicorn with auto-reload scoped to app/ only."""
    cmd = [
        python, "-m", "uvicorn", "app.main:app",
        "--host", host,
        "--port", str(port),
        "--reload",
        "--reload-dir", str(BACKEND / "app"),  # absolute path — works from any cwd
        "--log-level", log_level,
    ]
    print(f"\n  FoodTrack DEV server starting")
    print(f"  ─────────────────────────────────────────")
    print(f"  Frontend  →  http://{host}:{port}/")
    print(f"  Swagger   →  http://{host}:{port}/docs")
    print(f"  Health    →  http://{host}:{port}/health")
    print(f"  ─────────────────────────────────────────\n")
    os.chdir(BACKEND)       # uvicorn must run from backend/ to resolve app.main
    os.execv(python, cmd)   # replace current process — clean signal handling


def _start_prod(python: str, host: str, port: int, workers: int, log_level: str):
    """Production: Gunicorn with Uvicorn workers, no reload."""
    # Check Gunicorn is available (it's not on Windows natively)
    try:
        subprocess.run(
            [python, "-m", "gunicorn", "--version"],
            capture_output=True, check=True,
        )
        use_gunicorn = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        use_gunicorn = False

    if use_gunicorn:
        cmd = [
            python, "-m", "gunicorn", "app.main:app",
            "--worker-class", "uvicorn.workers.UvicornWorker",
            "--workers",      str(workers),
            "--bind",         f"{host}:{port}",
            "--log-level",    log_level,
            "--access-logfile", "-",    # stdout
            "--error-logfile",  "-",    # stdout
            "--forwarded-allow-ips", "*",
        ]
        print(f"\n  FoodTrack PROD server starting (Gunicorn x{workers} workers)")
    else:
        # Windows fallback — Gunicorn doesn't support Windows; use Uvicorn directly
        print(f"\n  NOTE: Gunicorn not available on this platform — using Uvicorn directly.")
        cmd = [
            python, "-m", "uvicorn", "app.main:app",
            "--host",      host,
            "--port",      str(port),
            "--log-level", log_level,
        ]
        print(f"\n  FoodTrack PROD server starting (Uvicorn, single process)")

    print(f"  ─────────────────────────────────────────")
    print(f"  Serving   →  http://{host}:{port}/")
    print(f"  Health    →  http://{host}:{port}/health")
    print(f"  ─────────────────────────────────────────\n")
    os.chdir(BACKEND)       # server must run from backend/ to resolve app.main
    os.execv(python, cmd)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    args = _parse_args()

    # Resolve port: CLI flag → $PORT env var → 8000
    port = args.port or int(os.getenv("PORT", "8000"))

    # Resolve log level
    log_level = args.log_level or ("info" if args.prod else "debug")

    # Resolve worker count for prod
    import multiprocessing
    workers = args.workers or (multiprocessing.cpu_count() * 2 + 1)

    python = _find_python()

    print(f"\n  FoodTrack — {'PRODUCTION' if args.prod else 'DEVELOPMENT'} mode")
    print(f"  Python   : {python}")
    print(f"  Backend  : {BACKEND}")
    print(f"  Frontend : {FRONTEND}")

    _check_env()
    _check_frontend()

    # Migrations and seeding now run in the background inside the FastAPI
    # lifespan — the server starts accepting requests immediately.
    # Use --run-migrate to run migrations synchronously BEFORE starting
    # (useful for CI, one-off provisioning, or the first-ever deployment).
    if args.run_migrate:
        _migrate(python)

    if args.prod:
        _start_prod(python, args.host, port, workers, log_level)
    else:
        _start_dev(python, args.host, port, log_level)


if __name__ == "__main__":
    main()
