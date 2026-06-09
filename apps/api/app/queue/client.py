from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None

PIPELINE_QUEUE = "pipeline:jobs"


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=None,   # None = no timeout on blocking ops (blpop)
            retry_on_timeout=True,
            health_check_interval=30,
        )
        logger.info("[Redis] Client initialized")
    return _redis


async def enqueue_analysis(analysis_id: str, payload: dict) -> None:
    r = await get_redis()
    await r.rpush(
        PIPELINE_QUEUE,
        json.dumps({"job_type": "analysis", "analysis_id": analysis_id, **payload}),
    )
    logger.info(f"[Redis] Enqueued analysis {analysis_id}")


async def enqueue_workspace_discovery(workspace_id: str) -> None:
    r = await get_redis()
    await r.rpush(
        PIPELINE_QUEUE,
        json.dumps({
            "job_type": "workspace_discovery",
            "workspace_id": workspace_id,
        }),
    )
    logger.info(f"[Redis] Enqueued workspace discovery {workspace_id}")


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
        logger.info("[Redis] Connection closed")
