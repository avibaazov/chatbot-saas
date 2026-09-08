"""MongoDB connection. One shared AsyncIOMotorClient per process, created lazily so the
app can boot even without MONGODB_URI set (e.g. for the health check during scaffolding).
Do not read/write Mongo directly from route handlers without going through here.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.mongodb_uri:
            raise RuntimeError(
                "MONGODB_URI is not set. Configure it via .env (local) or the "
                "deployment's secret store — never hardcode it."
            )
        _client = AsyncIOMotorClient(settings.mongodb_uri)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    settings = get_settings()
    return get_client()[settings.mongodb_db_name]
