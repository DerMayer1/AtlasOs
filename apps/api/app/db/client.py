from __future__ import annotations

import asyncio
import logging

from supabase import AsyncClient, acreate_client

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncClient | None = None
_lock = asyncio.Lock()


async def get_client() -> AsyncClient:
    """
    Returns a singleton AsyncClient.
    Uses a lock to prevent race conditions during concurrent first-time initialization.
    """
    global _client
    if _client is not None:
        return _client
    async with _lock:
        # Double-checked locking — another coroutine may have initialized while we waited
        if _client is None:
            logger.info("[DB] Initializing Supabase client...")
            _client = await acreate_client(
                settings.supabase_url,
                settings.supabase_service_key,
            )
            logger.info("[DB] Supabase client ready")
    return _client


async def close_client() -> None:
    """Call on application shutdown to cleanly close the connection."""
    global _client
    if _client is not None:
        _client = None
        logger.info("[DB] Supabase client closed")
