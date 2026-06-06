from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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


settings = Settings()  # type: ignore[call-arg]
