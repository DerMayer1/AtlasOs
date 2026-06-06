import os

# Set only the infrastructure env vars required for Settings to instantiate.
# API keys (OpenAI, Tavily) are NOT set here — unit tests mock the clients
# directly and never make real API calls. Smoke tests use the real .env file.
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
