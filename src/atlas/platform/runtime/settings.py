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


def get_settings() -> Settings:
    return Settings()
