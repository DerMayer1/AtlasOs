"""
Pipeline Guards
Pre-flight checks that run before a pipeline job is enqueued or executed.
Each guard either passes silently or raises a descriptive exception.
"""
from __future__ import annotations

import hashlib
import json
import logging

from app.queue.client import get_redis

logger = logging.getLogger(__name__)

# Max analyses a single user can have in pending/running state simultaneously
MAX_CONCURRENT_PER_USER = 2

# Cache TTL: if identical URL+depth was analyzed within this window, reuse result
CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours


class PipelineGuardError(Exception):
    """Raised when a guard rejects the pipeline request."""
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _cache_key(website_url: str, depth: str) -> str:
    token = f"{website_url.lower().rstrip('/')}:{depth}"
    return f"pipeline:cache:{hashlib.sha256(token.encode()).hexdigest()}"


def _concurrent_key(user_id: str) -> str:
    return f"pipeline:concurrent:{user_id}"


async def check_concurrent_limit(user_id: str, db_client) -> None:
    """Reject if user already has MAX_CONCURRENT_PER_USER active analyses."""
    from supabase import AsyncClient
    res = await db_client.table("analyses") \
        .select("id", count="exact") \
        .eq("user_id", user_id) \
        .in_("status", ["pending", "running"]) \
        .execute()

    active = res.count or 0
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
