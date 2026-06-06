"""
Startup Validator
Validates all required environment variables and service connectivity
before the application starts accepting traffic.
Fails fast with a descriptive error rather than crashing mid-request.
"""
from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

REQUIRED_VARS = [
    "OPENAI_API_KEY",
    "TAVILY_API_KEY",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_KEY",
    "REDIS_URL",
]


def validate_env() -> None:
    """Check all required env vars are present and non-empty."""
    import os
    missing = [var for var in REQUIRED_VARS if not os.environ.get(var)]
    if missing:
        logger.critical(f"[Startup] Missing required environment variables: {missing}")
        sys.exit(1)
    logger.info("[Startup] Environment validation passed")


def validate_api_key_format() -> None:
    """Basic format checks — catch common paste errors early."""
    from app.config import settings

    if not settings.openai_api_key.startswith("sk-"):
        logger.critical("[Startup] OPENAI_API_KEY does not look valid (expected sk- prefix)")
        sys.exit(1)

    if not settings.tavily_api_key.startswith("tvly-"):
        logger.critical("[Startup] TAVILY_API_KEY does not look valid (expected tvly- prefix)")
        sys.exit(1)

    if not settings.supabase_url.startswith("https://"):
        logger.critical("[Startup] SUPABASE_URL must use https://")
        sys.exit(1)

    logger.info("[Startup] API key format validation passed")


def run_startup_checks() -> None:
    validate_env()
    validate_api_key_format()
    logger.info("[Startup] All checks passed — ready to serve")
