import hashlib
import time
from datetime import datetime, timezone

from fastapi import Request, HTTPException
from sqlalchemy import select

from app.models.api_key import ApiKey

# In-process sliding-window rate limit store.
# NOTE: This store is local to each worker process and is zeroed on restart.
# For multi-worker deployments (Gunicorn with multiple workers) each process
# maintains its own counter, so the effective limit per key is (limit * workers).
# Replace with a Redis-backed counter (e.g. redis-py, aioredis) for accurate
# cross-process rate limiting in production.
_rate_limit_store: dict[str, list[float]] = {}


async def api_key_middleware(request: Request, call_next):
    api_key_header = request.headers.get("X-API-Key")

    if api_key_header and not request.url.path.startswith("/api/v1/auth"):
        prefix = api_key_header[:8]

        async def _get_session():
            from app.database import async_session
            async with async_session() as session:
                yield session

        db_gen = _get_session()
        db = await db_gen.__anext__()
        try:
            key_hash = hashlib.sha256(api_key_header.encode()).hexdigest()
            result = await db.execute(
                select(ApiKey).where(
                    ApiKey.key_prefix == prefix,
                    ApiKey.key_hash == key_hash,
                    ApiKey.is_active == True,
                )
            )
            api_key = result.scalar_one_or_none()

            if api_key is None:
                raise HTTPException(status_code=401, detail="Invalid or revoked API key")

            now = time.time()
            window = api_key.rate_limit_window or 3600
            limit = api_key.rate_limit or 1000

            if prefix not in _rate_limit_store:
                _rate_limit_store[prefix] = []

            # Purge timestamps outside the current window
            _rate_limit_store[prefix] = [
                t for t in _rate_limit_store[prefix] if t > now - window
            ]

            if len(_rate_limit_store[prefix]) >= limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            _rate_limit_store[prefix].append(now)

            api_key.last_used_at = datetime.now(timezone.utc)
            await db.commit()

            request.state.api_key = api_key

        except HTTPException:
            raise
        except Exception as exc:
            # Log unexpected errors rather than silently swallowing them
            import logging
            logging.getLogger(__name__).warning(
                "API key middleware error: %s", exc, exc_info=True
            )
        finally:
            await db.close()

    response = await call_next(request)
    return response
