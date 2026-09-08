from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.routes import bots, chat, documents, health, widget

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Skip index creation when MONGODB_URI isn't set so the app still boots for local
    # dev / the health check without a live cluster (see app/core/db.py).
    if settings.mongodb_uri:
        from app.core.db import get_db
        from app.core.indexes import create_indexes

        await create_indexes(get_db())
    yield


# `app` itself carries NO middleware. Starlette middleware added via add_middleware()
# wraps the entire ASGI call chain, including mounted sub-apps — app.mount() does not
# escape it. So the dashboard-only CORSMiddleware lives on `dashboard_app` instead, and
# `widget_app` (mounted below, handling its own per-bot CORS from allowed_domains) never
# passes through it. Mount order matters: /widget must be registered before "/", or the
# root mount (which prefix-matches everything) would swallow it first.
# docs/openapi/redoc disabled here on purpose: FastAPI auto-registers those as routes at
# construction time, and since they'd be registered before the mounts below, they'd win
# path-matching over dashboard_app's own /docs and /openapi.json (Starlette matches routes
# in registration order) — silently shadowing them instead of erroring, so it's easy to
# miss. dashboard_app's copies are what's actually reachable through the "/" mount.
app = FastAPI(
    title="Chatbot API",
    version="0.1.0",
    lifespan=lifespan,
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
)

dashboard_app = FastAPI(title="Chatbot API — dashboard-facing")
dashboard_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # widget auth is a site key, not cookies — see AGENTS.md §3
    allow_methods=["*"],
    allow_headers=["*"],
)
dashboard_app.include_router(health.router)
dashboard_app.include_router(bots.router)
dashboard_app.include_router(documents.router)
dashboard_app.include_router(chat.router)

@app.get("/widget.js", include_in_schema=False)
async def widget_bundle():
    """Serve the built embeddable widget bundle. The embed snippet the dashboard generates
    points a third-party <script src> here, so it's sent with permissive caching and an
    open CORS header (it's public static JS, no per-bot auth — that happens on /widget/*).
    Registered before the "/" mount below, which would otherwise swallow the path.
    """
    path = Path(settings.widget_bundle_path)
    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail="widget bundle not found — build packages/widget or set WIDGET_BUNDLE_PATH",
        )
    return FileResponse(
        path,
        media_type="application/javascript",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=300",
        },
    )


app.mount("/widget", widget.widget_app)
app.mount("/", dashboard_app)
