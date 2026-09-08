"""Single source of truth for runtime config. No literals elsewhere — everything
(URLs, keys, connection strings) comes from environment variables via this module.
See AGENTS.md §3/§6 for the rule this enforces.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    environment: str = Field(default="development")
    api_base_url: str = Field(default="http://127.0.0.1:8000")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # MongoDB Atlas — no default; must come from env. Never hardcode a connection string.
    mongodb_uri: str = Field(default="")
    mongodb_db_name: str = Field(default="chatbot")

    # Redis (background jobs / shared state) — added when we build ingestion (§5 step 4)
    redis_url: str = Field(default="")

    # Anthropic / RAG — added when we build inference (§5 step 5)
    anthropic_api_key: str = Field(default="")

    # Embeddings (§5 step 4). Empty => FakeEmbeddingsProvider is used (dev/test only).
    voyage_api_key: str = Field(default="")

    # Clerk (§5 step 7/8). JWKS URL for verifying session tokens the dashboard sends.
    # Derived from the Clerk publishable key's frontend-API domain — see
    # app/core/auth.py. Not a secret (JWKS is public by design), but still env-only
    # since it's per-environment (dev instance vs. prod instance have different domains).
    clerk_jwks_url: str = Field(default="")


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — read once per process."""
    return Settings()
