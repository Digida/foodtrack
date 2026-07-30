import hashlib
import time

from fastapi import Request, HTTPException
from sqlalchemy import select

from app.models.api_key import ApiKey

_rate_limit_store: dict[str, list[float]] = {}


async def api_key_middleware(request: Request, call_next):
    api_key_header = request.headers.get("X-API-Key")
    
    if api_key_header and not request.url.path.startswith("/api/v1/auth"):
        prefix = api_key_header[:8]
        
        async def get_db_for_middleware():
            from app.database import async_session
            async with async_session() as session:
                yield session

        db_gen = get_db_for_middleware()
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
            
            if api_key:
                now = time.time()
                window = api_key.rate_limit_window or 3600
                limit = api_key.rate_limit or 1000
                
                if prefix not in _rate_limit_store:
                    _rate_limit_store[prefix] = []
                
                _rate_limit_store[prefix] = [t for t in _rate_limit_store[prefix] if t > now - window]
                
                if len(_rate_limit_store[prefix]) >= limit:
                    raise HTTPException(status_code=429, detail="Rate limit exceeded")
                
                _rate_limit_store[prefix].append(now)
                
                api_key.last_used_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                await db.commit()
                
                request.state.api_key = api_key
        except HTTPException:
            raise
        except Exception:
            pass
        finally:
            await db.close()

    response = await call_next(request)
    return response
