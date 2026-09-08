"""Document ingestion routes. Deferred from the original ingestion-pipeline work until
Clerk auth existed to enforce bot ownership — see app/services/ingestion.py.
"""

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_current_clerk_user_id
from app.core.config import get_settings
from app.core.db import get_db
from app.models.document import Document, DocumentStatus
from app.services.ingestion_jobs import enqueue_text_ingestion, enqueue_url_ingestion
from app.services.users import get_or_create_user

router = APIRouter(prefix="/bots/{bot_id}/documents", tags=["documents"])

# Cap on a single pasted document. ~100k chars is roughly 25k tokens — enough for a big
# FAQ or policy page, small enough that one request can't run up an unbounded embedding
# bill or spike memory. Larger sources belong in file upload (a later decision).
MAX_DOCUMENT_CHARS = 100_000


class CreateDocumentRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=MAX_DOCUMENT_CHARS)  # raw text for now


class CreateUrlDocumentRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


class DocumentResponse(BaseModel):
    id: str
    filename: str
    url: str | None = None
    status: DocumentStatus
    error: str | None = None


def _to_response(doc: dict) -> DocumentResponse:
    return DocumentResponse(
        id=str(doc["_id"]),
        filename=doc["filename"],
        url=doc.get("url"),
        status=doc["status"],
        error=doc.get("error"),
    )


async def _verify_bot_ownership(db, bot_id: str, clerk_user_id: str) -> dict:
    user = await get_or_create_user(db.users, clerk_user_id)
    bot = await db.bots.find_one({"_id": ObjectId(bot_id), "owner_user_id": str(user["_id"])})
    if not bot:
        raise HTTPException(status_code=404, detail="bot not found")
    return bot


@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(
    bot_id: str,
    body: CreateDocumentRequest,
    background_tasks: BackgroundTasks,
    clerk_user_id: str = Depends(get_current_clerk_user_id),
):
    settings = get_settings()
    db = get_db()
    await _verify_bot_ownership(db, bot_id, clerk_user_id)

    doc = Document(bot_id=bot_id, filename=body.filename, source_type="text")
    result = await db.documents.insert_one(doc.model_dump(by_alias=True, exclude={"id"}))

    await enqueue_text_ingestion(
        db,
        settings,
        document_id=result.inserted_id,
        text=body.text,
        bot_id=bot_id,
        background_tasks=background_tasks,
    )

    fresh = await db.documents.find_one({"_id": result.inserted_id})
    return _to_response(fresh)


@router.post("/url", response_model=DocumentResponse, status_code=201)
async def create_document_from_url(
    bot_id: str,
    body: CreateUrlDocumentRequest,
    background_tasks: BackgroundTasks,
    clerk_user_id: str = Depends(get_current_clerk_user_id),
):
    settings = get_settings()
    db = get_db()
    await _verify_bot_ownership(db, bot_id, clerk_user_id)

    url = body.url.strip()
    doc = Document(bot_id=bot_id, filename=url, source_type="url", url=url)
    result = await db.documents.insert_one(doc.model_dump(by_alias=True, exclude={"id"}))

    await enqueue_url_ingestion(
        db,
        settings,
        document_id=result.inserted_id,
        url=url,
        bot_id=bot_id,
        background_tasks=background_tasks,
    )

    fresh = await db.documents.find_one({"_id": result.inserted_id})
    return _to_response(fresh)


@router.post("/{document_id}/reload", response_model=DocumentResponse)
async def reload_document(
    bot_id: str,
    document_id: str,
    background_tasks: BackgroundTasks,
    clerk_user_id: str = Depends(get_current_clerk_user_id),
):
    """Re-crawl a URL document: drop its old chunks, reset status, re-run ingestion. Used
    by the dashboard's "Reload" button to pick up changes to the trained site.
    """
    settings = get_settings()
    db = get_db()
    await _verify_bot_ownership(db, bot_id, clerk_user_id)

    doc = await db.documents.find_one({"_id": ObjectId(document_id), "bot_id": bot_id})
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    if doc.get("source_type") != "url" or not doc.get("url"):
        raise HTTPException(status_code=400, detail="only URL documents can be reloaded")

    await db.chunks.delete_many({"document_id": document_id})
    await db.documents.update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": DocumentStatus.pending, "error": None}},
    )
    await enqueue_url_ingestion(
        db,
        settings,
        document_id=doc["_id"],
        url=doc["url"],
        bot_id=bot_id,
        background_tasks=background_tasks,
    )

    fresh = await db.documents.find_one({"_id": doc["_id"]})
    return _to_response(fresh)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(bot_id: str, clerk_user_id: str = Depends(get_current_clerk_user_id)):
    db = get_db()
    await _verify_bot_ownership(db, bot_id, clerk_user_id)
    docs = await db.documents.find({"bot_id": bot_id}).to_list(length=100)
    return [_to_response(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    bot_id: str, document_id: str, clerk_user_id: str = Depends(get_current_clerk_user_id)
):
    db = get_db()
    await _verify_bot_ownership(db, bot_id, clerk_user_id)
    doc = await db.documents.find_one({"_id": ObjectId(document_id), "bot_id": bot_id})
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    return _to_response(doc)
