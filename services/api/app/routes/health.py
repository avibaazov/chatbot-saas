from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness check. Does not touch Mongo/Redis on purpose — those get a
    separate /health/ready once they're wired in, so this stays fast and dependency-free.
    """
    settings = get_settings()
    return {"status": "ok", "environment": settings.environment}
