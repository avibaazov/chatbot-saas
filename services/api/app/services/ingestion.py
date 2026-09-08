"""The ingestion pipeline: chunk -> embed -> upsert vectors. This is what "training" means
in the new architecture (AGENTS.md §4) — seconds, not gradient descent, and no .pth files.

Takes plain Mongo collection objects (not the whole db) so it's testable against small fake
stand-ins — see tests/test_ingestion.py — without a live Atlas cluster.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from app.models.chunk import Chunk
from app.models.document import DocumentStatus
from app.services.chunking import chunk_text
from app.services.embeddings import EmbeddingsProvider


class SupportsUpdateOne(Protocol):
    async def update_one(self, filter: dict, update: dict) -> Any: ...


class SupportsInsertMany(Protocol):
    async def insert_many(self, documents: list[dict]) -> Any: ...


async def ingest_document(
    *,
    documents_col: SupportsUpdateOne,
    chunks_col: SupportsInsertMany,
    document_id,
    text: str,
    bot_id: str,
    embeddings: EmbeddingsProvider,
) -> None:
    """Chunk `text`, embed each chunk, insert into chunks_col, and update the document's
    status field the dashboard polls. Any failure is caught and recorded as
    status=failed + error, rather than left stuck on "processing" forever.
    """
    await documents_col.update_one(
        {"_id": document_id},
        {"$set": {"status": DocumentStatus.processing, "updated_at": _now()}},
    )

    try:
        pieces = chunk_text(text)
        if not pieces:
            raise ValueError("document produced no chunks (empty text)")

        vectors = await embeddings.embed(pieces)

        chunk_docs = [
            Chunk(
                document_id=str(document_id),
                bot_id=bot_id,
                chunk_index=i,
                text=piece,
                embedding=vector,
            ).model_dump(by_alias=True, exclude={"id"})
            for i, (piece, vector) in enumerate(zip(pieces, vectors))
        ]
        await chunks_col.insert_many(chunk_docs)

        await documents_col.update_one(
            {"_id": document_id},
            {"$set": {"status": DocumentStatus.ready, "updated_at": _now()}},
        )
    except Exception as exc:
        await documents_col.update_one(
            {"_id": document_id},
            {
                "$set": {
                    "status": DocumentStatus.failed,
                    "error": str(exc),
                    "updated_at": _now(),
                }
            },
        )
        raise


def _now() -> datetime:
    return datetime.now(timezone.utc)
