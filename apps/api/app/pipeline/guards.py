"""
Pipeline Guards
Pre-flight checks before a pipeline job is enqueued or executed.
Each guard either passes silently or raises PipelineGuardError.
"""
from __future__ import annotations

import hashlib
import json
import logging

from app.queue.client import get_redis

logger = logging.getLogger(__name__)

MAX_CONCURRENT_PER_USER = 2
CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours


class PipelineGuardError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _cache_key(website_url: str, depth: str) -> str:
    token = f"{website_url.lower().rstrip('/')}:{depth}"
    return f"pipeline:cache:{hashlib.sha256(token.encode()).hexdigest()}"


async def check_concurrent_limit(user_id: str, db_client) -> None:
    """Reject if user already has MAX_CONCURRENT_PER_USER active analyses."""
    from app.db.repositories.analyses import count_active_analyses
    active = await count_active_analyses(user_id)
    if active >= MAX_CONCURRENT_PER_USER:
        logger.warning(f"[Guard] User {user_id} hit concurrent limit ({active} active)")
        raise PipelineGuardError(
            code="CONCURRENT_LIMIT",
            message=f"You already have {active} analyses running. Wait for them to complete before starting a new one.",
        )


async def check_cache(website_url: str, depth: str) -> dict | None:
    """Return cached MarketMap if this URL+depth was recently analyzed."""
    r = await get_redis()
    key = _cache_key(website_url, depth)
    cached = await r.get(key)
    if cached:
        logger.info(f"[Guard] Cache hit for {website_url} ({depth})")
        return json.loads(cached)
    return None


async def write_cache(website_url: str, depth: str, result: dict) -> None:
    """Cache a successful MarketMap result for 24 hours."""
    r = await get_redis()
    key = _cache_key(website_url, depth)
    await r.setex(key, CACHE_TTL_SECONDS, json.dumps(result))
    logger.info(f"[Guard] Cached result for {website_url} ({depth})")


async def invalidate_cache(website_url: str, depth: str) -> None:
    """Manually invalidate a cached result (e.g. user requests fresh analysis)."""
    r = await get_redis()
    key = _cache_key(website_url, depth)
    deleted = await r.delete(key)
    if deleted:
        logger.info(f"[Guard] Cache invalidated for {website_url} ({depth})")
