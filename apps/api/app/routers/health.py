import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", tags=["health"])
@limiter.limit("60/minute")
async def health_check(request) -> dict:
    checks: dict[str, str] = {}
    healthy = True

    # Redis check
    try:
        from app.queue.client import get_redis
        r = await get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        logger.error(f"[Health] Redis check failed: {e}")
        checks["redis"] = "error"
        healthy = False

    # Supabase check (lightweight — just verify client instantiates)
    try:
        from app.db.client import get_client
        await get_client()
        checks["database"] = "ok"
    except Exception as e:
        logger.error(f"[Health] Database check failed: {e}")
        checks["database"] = "error"
        healthy = False

    status_code = 200 if healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if healthy else "degraded",
            "service": "atlasos-api",
            "checks": checks,
        },
    )
