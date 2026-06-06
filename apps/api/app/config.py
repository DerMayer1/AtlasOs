from pathlib import Path
from typing import Any, Tuple, Type

from pydantic_settings import BaseSettings, EnvSettingsSource, PydanticBaseSettingsSource, SettingsConfigDict

# Walk up from this file to find the root .env (works from any CWD)
_here = Path(__file__).resolve()
_root_env = next(
    (p / ".env" for p in [_here.parent, *_here.parents] if (p / ".env").exists()),
    Path(".env"),
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_root_env),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI
    openai_api_key: str

    # Tavily
    tavily_api_key: str

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Pipeline
    pipeline_timeout_s: int = 90
    log_level: str = "info"

    # R2 (optional)
    r2_bucket_url: str = ""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # Priority: init kwargs > .env file > system env vars > defaults
        # .env takes precedence over system environment variables
        return init_settings, dotenv_settings, env_settings, file_secret_settings


settings = Settings()  # type: ignore[call-arg]
