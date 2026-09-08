"""Bot CRUD. Ownership is enforced by filtering every query on owner_user_id, not by a
separate "check then act" step — so there's no window where a check passes and a later
query forgets to re-check (AGENTS.md §3: every bot-scoped endpoint must verify ownership).
"""

import secrets

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from pymongo import ReturnDocument

from app.core.auth import get_current_clerk_user_id
from app.core.db import get_db
from app.models.bot import BotConfig, Bot
from app.services.domains import extract_hostname
from app.services.users import get_or_create_user

router = APIRouter(prefix="/bots", tags=["bots"])


class CreateBotRequest(BaseModel):
    name: str


class UpdateAllowedDomainsRequest(BaseModel):
    allowed_domains: list[str]


class BotResponse(BaseModel):
    id: str
    name: str
    config: BotConfig
    site_key: str
    allowed_domains: list[str]


def _to_response(doc: dict) -> BotResponse:
    return BotResponse(
        id=str(doc["_id"]),
        name=doc["name"],
        config=BotConfig(**doc["config"]),
        site_key=doc["site_key"],
        allowed_domains=doc.get("allowed_domains", []),
    )


@router.post("", response_model=BotResponse, status_code=201)
async def create_bot(body: CreateBotRequest, clerk_user_id: str = Depends(get_current_clerk_user_id)):
    db = get_db()
    user = await get_or_create_user(db.users, clerk_user_id)

    bot = Bot(
        owner_user_id=str(user["_id"]),
        name=body.name,
        site_key=f"sk_pub_{secrets.token_urlsafe(24)}",
    )
    result = await db.bots.insert_one(bot.model_dump(by_alias=True, exclude={"id"}))
    doc = await db.bots.find_one({"_id": result.inserted_id})
    return _to_response(doc)


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


@router.delete("/{bot_id}", status_code=204)
async def delete_bot(bot_id: str, clerk_user_id: str = Depends(get_current_clerk_user_id)):
    db = get_db()
    user = await get_or_create_user(db.users, clerk_user_id)
    result = await db.bots.delete_one({"_id": ObjectId(bot_id), "owner_user_id": str(user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="bot not found")
