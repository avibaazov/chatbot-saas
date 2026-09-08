"""Single source of truth for runtime config. No literals elsewhere — everything
(URLs, keys, connection strings) comes from environment variables via this module.
See AGENTS.md §3/§6 for the rule this enforces.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# packages/widget/dist/widget.js relative to the repo root — the default location of the
# built widget bundle when the API runs from a full monorepo checkout. In a deploy where
# only services/api ships, copy the built bundle somewhere and set WIDGET_BUNDLE_PATH.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_WIDGET_BUNDLE = _REPO_ROOT / "packages" / "widget" / "dist" / "widget.js"


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

    # Filesystem path to the built widget bundle, served at GET /widget.js so the embed
    # snippet the dashboard hands out points at a real, reachable URL. Defaults to the
    # monorepo build output; override in a split deploy. See app/main.py.
    widget_bundle_path: str = Field(default=str(_DEFAULT_WIDGET_BUNDLE))

    # MongoDB Atlas — no default; must come from env. Never hardcode a connection string.
    mongodb_uri: str = Field(default="")
    mongodb_db_name: str = Field(default="chatbot")

    # Redis (background jobs / shared state) — added when we build ingestion (§5 step 4)
    redis_url: str = Field(default="")

    # When true (dev / tests / small single-instance deploys) document ingestion is awaited
    # inside the create/reload request, so the response already carries a terminal status.
    # Set false behind a host with request timeouts: ingestion is handed to a background
    # task and the request returns immediately with status=pending. Neither path survives a
    # restart mid-job — that needs Redis + a worker (AGENTS.md §4).
    ingest_inline: bool = Field(default=True)

    # Anthropic / RAG — added when we build inference (§5 step 5)
    anthropic_api_key: str = Field(default="")

    # Embeddings (§5 step 4). Empty => FakeEmbeddingsProvider is used (dev/test only).
    voyage_api_key: str = Field(default="")

    # DEV ONLY. When true, URL ingestion may fetch loopback/private/link-local hosts —
    # needed to ingest a demo site served on 127.0.0.1. Never enable in a deployed
    # environment: it re-opens the SSRF hole the guard in app/services/web_fetch.py closes.
    ingest_allow_private_hosts: bool = Field(default=False)

    # Clerk (§5 step 7/8). JWKS URL for verifying session tokens the dashboard sends.
    # Derived from the Clerk publishable key's frontend-API domain — see
    # app/core/auth.py. Not a secret (JWKS is public by design), but still env-only
    # since it's per-environment (dev instance vs. prod instance have different domains).
    clerk_jwks_url: str = Field(default="")


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance — read once per process."""
    return Settings()
