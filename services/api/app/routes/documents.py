"""Document ingestion routes. Deferred from the original ingestion-pipeline work until
Clerk auth existed to enforce bot ownership — see app/services/ingestion.py.
"""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import get_current_clerk_user_id
from app.core.config import get_settings
from app.core.db import get_db
from app.models.document import Document, DocumentStatus
from app.services.embeddings import get_embeddings_provider
from app.services.ingestion import ingest_document
from app.services.queue import get_queue
from app.services.users import get_or_create_user

router = APIRouter(prefix="/bots/{bot_id}/documents", tags=["documents"])


class CreateDocumentRequest(BaseModel):
    filename: str
    text: str  # raw text for now; file upload storage is a later decision


class DocumentResponse(BaseModel):
    id: str
    filename: str
    status: DocumentStatus
    error: str | None = None


def _to_response(doc: dict) -> DocumentResponse:
    return DocumentResponse(
        id=str(doc["_id"]), filename=doc["filename"], status=doc["status"], error=doc.get("error")
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
    clerk_user_id: str = Depends(get_current_clerk_user_id),
):
    settings = get_settings()
    db = get_db()
    await _verify_bot_ownership(db, bot_id, clerk_user_id)

    doc = Document(bot_id=bot_id, filename=body.filename, source_type="text")
    result = await db.documents.insert_one(doc.model_dump(by_alias=True, exclude={"id"}))

    embeddings = get_embeddings_provider(settings)
    queue = get_queue(settings)

    async def job():
        try:
            await ingest_document(
                documents_col=db.documents,
                chunks_col=db.chunks,
                document_id=result.inserted_id,
                text=body.text,
                bot_id=bot_id,
                embeddings=embeddings,
            )
        except Exception:
            # ingest_document already recorded status=failed + error on the document
            # before re-raising — that re-raise is for a real queue's retry/alerting
            # logic. InMemoryQueue runs inline in this request, so let the response
            # report the failed status instead of turning it into a 500.
            pass

    await queue.enqueue(job)

    fresh = await db.documents.find_one({"_id": result.inserted_id})
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
