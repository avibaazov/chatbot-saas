"""The actual "talk to the bot" endpoint — ties together retrieval + generation
(app/services/rag.py) behind the same ownership check every bot-scoped route uses.
"""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_clerk_user_id
from app.core.config import get_settings
from app.core.db import get_db
from app.models.bot import BotConfig
from app.services.embeddings import get_embeddings_provider
from app.services.llm import get_llm_provider
from app.services.rag import answer_question
from app.services.retrieval import MongoBruteForceVectorStore
from app.services.users import get_or_create_user

router = APIRouter(prefix="/bots/{bot_id}/ask", tags=["chat"])


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


@router.post("", response_model=AskResponse)
async def ask_bot(
    bot_id: str, body: AskRequest, clerk_user_id: str = Depends(get_current_clerk_user_id)
):
    settings = get_settings()
    db = get_db()

    user = await get_or_create_user(db.users, clerk_user_id)
    bot_doc = await db.bots.find_one({"_id": ObjectId(bot_id), "owner_user_id": str(user["_id"])})
    if not bot_doc:
        raise HTTPException(status_code=404, detail="bot not found")

    config = BotConfig(**bot_doc["config"])
    answer = await answer_question(
        question=body.question,
        bot_id=bot_id,
        system_prompt=config.system_prompt,
        embeddings=get_embeddings_provider(settings),
        vector_store=MongoBruteForceVectorStore(db.chunks),
        llm=get_llm_provider(settings, model_tier=config.model_tier),
    )
    return AskResponse(answer=answer)
