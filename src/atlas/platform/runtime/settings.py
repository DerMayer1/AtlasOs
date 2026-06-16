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
    # Dev convenience: create tables directly for SQLite. Postgres uses Alembic.
    auto_create_schema: bool = True
    job_max_tries: int = 3
    # Explicit local-only mode. Enables the unauthenticated demo bootstrap
    # endpoint used by `python -m atlas.interfaces.cli demo`.
    demo_mode: bool = False
    # Comma-separated browser origins allowed to call the API from a separately
    # deployed frontend, e.g. https://atlas-os.vercel.app.
    cors_allowed_origins: str = ""
    # Agent LLM. Empty key -> NullLLMClient -> graceful degradation (deterministic
    # planning + numbers-only narration). Set ATLAS_ANTHROPIC_API_KEY for full mode.
    anthropic_api_key: str = ""
    llm_model: str = "claude-haiku-4-5-20251001"


def get_settings() -> Settings:
    return Settings()
