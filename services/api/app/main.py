from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routes import bots, chat, documents, health

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


app = FastAPI(title="Chatbot API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # widget auth is a site key, not cookies — see AGENTS.md §3
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(bots.router)
app.include_router(documents.router)
app.include_router(chat.router)
