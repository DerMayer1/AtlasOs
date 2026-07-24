"""Runtime configuration. All values overridable via ATLAS_* env vars."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ATLAS_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///var/atlas.db"
    # Empty redis_url = in-process queue (dev/tests). Set for ARQ + Redis.
    redis_url: str = ""
    data_dir: Path = Path("var/data")
    # Required for ALFRED point-in-time validation. Kept server-side.
    fred_api_key: str = ""
    # Dev convenience: create tables directly for SQLite. Postgres uses Alembic.
    auto_create_schema: bool = True
    job_max_tries: int = 3
    # Explicit local-only mode. Enables the unauthenticated demo bootstrap
    # endpoint used by `python -m atlas.interfaces.cli demo`.
    demo_mode: bool = False
    # Set the Secure flag on the browser session cookie. True in production
    # (HTTPS); set false only to exercise the login flow over plain http locally.
    session_cookie_secure: bool = True
    # Comma-separated browser origins allowed to call the API from a separately
    # deployed frontend, e.g. https://atlas-os.vercel.app.
    cors_allowed_origins: str = ""
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 120
    rate_limit_burst: int = 30
    # Number of trusted reverse proxies in front of the API. 0 (default) means
    # the API is directly exposed: X-Forwarded-For is client-controlled and must
    # be ignored, so the peer IP is used for rate limiting. Set to the real hop
    # count (e.g. 1 behind a single proxy) so the client IP is read from the
    # right of the X-Forwarded-For chain, where trusted proxies append it, and a
    # spoofed left-hand entry cannot bypass the limiter.
    trusted_proxy_count: int = 0
    # Hard cap on distinct rate-limit identities held in memory, so a flood of
    # unique identities cannot grow the bucket table without bound.
    rate_limit_max_tracked_identities: int = 100_000
    max_request_body_bytes: int = 1_000_000
    # Agent LLM. Empty key -> NullLLMClient -> graceful degradation (deterministic
    # planning + numbers-only narration). Set ATLAS_OPENAI_API_KEY for full mode.
    openai_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"


def get_settings() -> Settings:
    return Settings()
