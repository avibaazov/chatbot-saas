"""Bot CRUD. Ownership is enforced by filtering every query on owner_user_id, not by a
separate "check then act" step — so there's no window where a check passes and a later
query forgets to re-check (AGENTS.md §3: every bot-scoped endpoint must verify ownership).
"""

import secrets

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_clerk_user_id
from app.core.db import get_db
from app.models.bot import BotConfig, Bot
from app.services.users import get_or_create_user

router = APIRouter(prefix="/bots", tags=["bots"])


class CreateBotRequest(BaseModel):
    name: str


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


@router.delete("/{bot_id}", status_code=204)
async def delete_bot(bot_id: str, clerk_user_id: str = Depends(get_current_clerk_user_id)):
    db = get_db()
    user = await get_or_create_user(db.users, clerk_user_id)
    result = await db.bots.delete_one({"_id": ObjectId(bot_id), "owner_user_id": str(user["_id"])})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="bot not found")
