from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routes import health

settings = get_settings()

app = FastAPI(title="Chatbot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,  # widget auth is a site key, not cookies — see AGENTS.md §3
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
