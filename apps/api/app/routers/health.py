from fastapi import APIRouter

from app.middleware.rate_limit import limiter

router = APIRouter()


@router.get("/health", tags=["health"])
@limiter.limit("60/minute")
async def health_check(request) -> dict[str, str]:
    return {"status": "ok", "service": "atlasos-api"}
