"""Public endpoints the embeddable widget calls from third-party sites. Auth here is
NOT Clerk — it's a public per-bot site_key plus a domain allow-list, checked against the
request's Origin header (AGENTS.md §3/§4: widget auth must not be cookies, since the
widget runs on a domain we don't control).

CORS for this router is handled manually, not by the app-wide CORSMiddleware in main.py.
That middleware's allow_origins is the fixed dashboard origin (see main.py) — it can't
know in advance which third-party domains a given bot is allowed to run on, since that's
per-bot, database-driven data. Worse, Starlette's CORSMiddleware intercepts every OPTIONS
preflight app-wide (it isn't path-scoped) and would reject an unlisted third-party origin
before this router ever ran — so these routes live on their own sub-app (`widget_app`,
mounted at /widget in main.py) that never gets that middleware attached. Every response
here sets its own Access-Control-Allow-Origin, computed from the bot's allowed_domains.
"""

from fastapi import APIRouter, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.db import get_db
from app.models.bot import BotConfig
from app.services.domains import extract_hostname
from app.services.embeddings import get_embeddings_provider
from app.services.llm import get_llm_provider
from app.services.rag import answer_question
from app.services.rate_limit import is_rate_limited
from app.services.retrieval import MongoBruteForceVectorStore

router = APIRouter(prefix="/{site_key}", tags=["widget"])

RATE_LIMIT_PER_MINUTE = 20


def _is_origin_allowed(origin: str | None, allowed_domains: list[str]) -> bool:
    if "*" in allowed_domains:
        return True
    # The dashboard is first-party: it embeds the real widget as a live preview on the bot
    # detail page. Its own origin is always allowed, regardless of the bot's allow-list, so
    # the preview works without the user adding their dashboard domain by hand.
    if origin and origin in get_settings().cors_origins:
        return True
    hostname = extract_hostname(origin) if origin else None
    if hostname is None:
        return False
    # A bot is tied to one website (its training URL's host). Match that host exactly, or
    # any subdomain of it — so a bot for "acme.com" also works when embedded on
    # "www.acme.com" or "help.acme.com" without the user maintaining a domain list.
    return any(
        hostname == allowed or hostname.endswith(f".{allowed}") for allowed in allowed_domains
    )


async def _get_bot_by_site_key(site_key: str) -> dict:
    db = get_db()
    bot = await db.bots.find_one({"site_key": site_key})
    if not bot:
        raise HTTPException(status_code=404, detail="bot not found")
    return bot


def _apply_cors(response: Response, origin: str | None) -> None:
    response.headers["Access-Control-Allow-Origin"] = origin or "null"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Max-Age"] = "600"
    response.headers["Vary"] = "Origin"


class WidgetConfigResponse(BaseModel):
    display_name: str
    primary_color: str
    font_size: str


@router.get("/config", response_model=WidgetConfigResponse)
async def widget_config(site_key: str, request: Request, response: Response):
    bot = await _get_bot_by_site_key(site_key)
    origin = request.headers.get("origin")
    if not _is_origin_allowed(origin, bot.get("allowed_domains", [])):
        raise HTTPException(status_code=403, detail="origin not allowed for this bot")
    _apply_cors(response, origin)

    config = BotConfig(**bot["config"])
    return WidgetConfigResponse(
        display_name=config.display_name,
        primary_color=config.primary_color,
        font_size=config.font_size,
    )


class WidgetAskRequest(BaseModel):
    question: str


class WidgetAskResponse(BaseModel):
    answer: str


@router.options("/ask")
async def widget_ask_preflight(site_key: str, request: Request):
    response = Response(status_code=204)
    try:
        bot = await _get_bot_by_site_key(site_key)
    except HTTPException:
        return response  # unknown bot: no CORS headers, browser blocks the real request

    origin = request.headers.get("origin")
    if _is_origin_allowed(origin, bot.get("allowed_domains", [])):
        _apply_cors(response, origin)
    return response


@router.post("/ask", response_model=WidgetAskResponse)
async def widget_ask(site_key: str, body: WidgetAskRequest, request: Request, response: Response):
    bot = await _get_bot_by_site_key(site_key)
    origin = request.headers.get("origin")
    if not _is_origin_allowed(origin, bot.get("allowed_domains", [])):
        raise HTTPException(status_code=403, detail="origin not allowed for this bot")
    _apply_cors(response, origin)

    if is_rate_limited(site_key, max_per_minute=RATE_LIMIT_PER_MINUTE):
        raise HTTPException(status_code=429, detail="rate limit exceeded, try again shortly")

    settings = get_settings()
    db = get_db()
    config = BotConfig(**bot["config"])
    bot_id = str(bot["_id"])

    answer = await answer_question(
        question=body.question,
        bot_id=bot_id,
        system_prompt=config.system_prompt,
        embeddings=get_embeddings_provider(settings),
        vector_store=MongoBruteForceVectorStore(db.chunks),
        llm=get_llm_provider(settings, model_tier=config.model_tier),
    )
    return WidgetAskResponse(answer=answer)


# Mounted at /widget in main.py, deliberately with no CORSMiddleware attached — see the
# module docstring for why the app-wide one can't be used for these routes.
widget_app = FastAPI(title="Chatbot Widget API")
widget_app.include_router(router)
