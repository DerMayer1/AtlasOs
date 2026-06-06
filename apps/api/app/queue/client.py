from __future__ import annotations

import redis.asyncio as aioredis
from app.config import settings

_redis: aioredis.Redis | None = None

PIPELINE_QUEUE = "pipeline:jobs"


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def enqueue_analysis(analysis_id: str, payload: dict) -> None:
    import json
    r = await get_redis()
    await r.rpush(PIPELINE_QUEUE, json.dumps({"analysis_id": analysis_id, **payload}))


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
