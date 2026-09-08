"""Bot CRUD. Ownership is enforced by filtering every query on owner_user_id, not by a
separate "check then act" step — so there's no window where a check passes and a later
query forgets to re-check (AGENTS.md §3: every bot-scoped endpoint must verify ownership).
"""

import re
import secrets
from urllib.parse import urlparse

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

from app.core.auth import get_current_clerk_user_id
from app.core.config import get_settings
from app.core.db import get_db
from app.models.bot import BotConfig, Bot
from app.models.document import Document
from app.services.domains import extract_hostname
from app.services.ingestion_jobs import enqueue_url_ingestion
from app.services.users import get_or_create_user

router = APIRouter(prefix="/bots", tags=["bots"])


class CreateBotRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    website_url: str = Field(min_length=1, max_length=2048)


class UpdateAllowedDomainsRequest(BaseModel):
    allowed_domains: list[str]


FONT_SIZES = {"small", "medium", "large"}
_HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class UpdateAppearanceRequest(BaseModel):
    """The widget-facing look of the bot. Behavior fields (system_prompt, model_tier) are
    intentionally not editable here yet — this is the "Appearance" form on the dashboard."""

    display_name: str
    primary_color: str
    font_size: str


class BotResponse(BaseModel):
    id: str
    name: str
    website_url: str
    config: BotConfig
    site_key: str
    allowed_domains: list[str]


def _to_response(doc: dict) -> BotResponse:
    return BotResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        website_url=doc.get("website_url", ""),
        config=BotConfig(**doc["config"]),
        site_key=doc["site_key"],
        allowed_domains=doc.get("allowed_domains", []),
    )


@router.post("", response_model=BotResponse, status_code=201)
async def create_bot(
    body: CreateBotRequest,
    background_tasks: BackgroundTasks,
    clerk_user_id: str = Depends(get_current_clerk_user_id),
):
    website_url = body.website_url.strip()
    parsed = urlparse(website_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise HTTPException(status_code=400, detail="website_url must be a full http(s) URL")
    hostname = extract_hostname(website_url)

    db = get_db()
    settings = get_settings()
    user = await get_or_create_user(db.users, clerk_user_id)

    bot = Bot(
        owner_user_id=str(user["_id"]),
        name=body.name,
        website_url=website_url,
        # Seed the allow-list with the site's own hostname: the embed snippet targets that
        # site, and the dashboard preview loads the widget too (widget.py also always
        # allows the first-party dashboard origin). The user can edit the list afterwards.
        allowed_domains=[hostname] if hostname else [],
        site_key=f"sk_pub_{secrets.token_urlsafe(24)}",
    )
    result = await db.bots.insert_one(bot.model_dump(by_alias=True, exclude={"id"}))

    # Train on the site immediately — one URL document, ingested in the background exactly
    # like a document added later from the dashboard.
    doc = Document(bot_id=str(result.inserted_id), filename=website_url, source_type="url", url=website_url)
    doc_result = await db.documents.insert_one(doc.model_dump(by_alias=True, exclude={"id"}))
    await enqueue_url_ingestion(
        db,
        settings,
        document_id=doc_result.inserted_id,
        url=website_url,
        bot_id=str(result.inserted_id),
        background_tasks=background_tasks,
    )

    fresh = await db.bots.find_one({"_id": result.inserted_id})
    return _to_response(fresh)


@router.get("", response_model=list[BotResponse])
async def list_bots(clerk_user_id: str = Depends(get_current_clerk_user_id)):
    db = get_db()
    user = await get_or_create_user(db.users, clerk_user_id)
    docs = await db.bots.find({"owner_user_id": str(user["_id"])}).to_list(length=100)
    return [_to_response(d) for d in docs]


@router.get("/{bot_id}", response_model=BotResponse)
async def get_bot(bot_id: str, clerk_user_id: str = Depends(get_current_clerk_user_id)):
    db = get_db()
    user = await get_or_create_user(db.users, clerk_user_id)
    doc = await db.bots.find_one({"_id": ObjectId(bot_id), "owner_user_id": str(user["_id"])})
    if not doc:
        raise HTTPException(status_code=404, detail="bot not found")
    return _to_response(doc)


@router.put("/{bot_id}/allowed-domains", response_model=BotResponse)
async def update_allowed_domains(
    bot_id: str,
    body: UpdateAllowedDomainsRequest,
    clerk_user_id: str = Depends(get_current_clerk_user_id),
):
    # Accept whatever format a human pastes (bare "example.com", "localhost:3000", or a
    # full "http://example.com/path" copied from a browser bar) and normalize it to the
    # plain hostname[:port] form the widget compares real Origin headers against.
    normalized = []
    for raw in body.allowed_domains:
        hostname = extract_hostname(raw)
        if not hostname:
            raise HTTPException(status_code=400, detail=f"'{raw}' is not a valid domain")
        normalized.append(hostname)

    db = get_db()
    user = await get_or_create_user(db.users, clerk_user_id)
    result = await db.bots.find_one_and_update(
        {"_id": ObjectId(bot_id), "owner_user_id": str(user["_id"])},
        {"$set": {"allowed_domains": normalized}},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=404, detail="bot not found")
    return _to_response(result)


@router.put("/{bot_id}/appearance", response_model=BotResponse)
async def update_appearance(
    bot_id: str,
    body: UpdateAppearanceRequest,
    clerk_user_id: str = Depends(get_current_clerk_user_id),
):
    display_name = body.display_name.strip()
    if not (1 <= len(display_name) <= 40):
        raise HTTPException(status_code=400, detail="display_name must be 1–40 characters")
    if not _HEX_COLOR.match(body.primary_color):
        raise HTTPException(status_code=400, detail="primary_color must be a hex color like #4f46e5")
    if body.font_size not in FONT_SIZES:
        raise HTTPException(status_code=400, detail=f"font_size must be one of {sorted(FONT_SIZES)}")

    db = get_db()
    user = await get_or_create_user(db.users, clerk_user_id)
    result = await db.bots.find_one_and_update(
        {"_id": ObjectId(bot_id), "owner_user_id": str(user["_id"])},
        {
            "$set": {
                "config.display_name": display_name,
                "config.primary_color": body.primary_color,
                "config.font_size": body.font_size,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=404, detail="bot not found")
    return _to_response(result)


@router.delete("/{bot_id}", status_code=204)
async def delete_bot(bot_id: str, clerk_user_id: str = Depends(get_current_clerk_user_id)):
    db = get_db()
    user = await get_or_create_user(db.users, clerk_user_id)
    result = await db.bots.delete_one({"_id": ObjectId(bot_id), "owner_user_id": str(user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="bot not found")
