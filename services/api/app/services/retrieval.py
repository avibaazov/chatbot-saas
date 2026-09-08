"""Vector retrieval abstraction. AtlasVectorStore (real) queries Mongo Atlas Vector Search
via a $vectorSearch aggregation stage — but that needs a Vector Search index that doesn't
exist yet (it requires real, semantically meaningful embeddings first; see
app/services/embeddings.py). InMemoryVectorStore stands in for tests/dev: brute-force
cosine similarity over whatever chunks it's given.
"""

from __future__ import annotations

import math
from typing import Protocol

from app.models.chunk import Chunk


class VectorStore(Protocol):
    async def search(self, *, bot_id: str, query_embedding: list[float], top_k: int) -> list[Chunk]: ...


class InMemoryVectorStore:
    """Brute-force cosine similarity over an in-memory list of chunks. O(n), fine for
    tests and tiny dev datasets — not how retrieval works once Atlas Vector Search is wired.
    """

    def __init__(self, chunks: list[Chunk] | None = None):
        self.chunks = chunks or []

    async def search(self, *, bot_id: str, query_embedding: list[float], top_k: int) -> list[Chunk]:
        candidates = [c for c in self.chunks if c.bot_id == bot_id]
        scored = [(c, _cosine_similarity(c.embedding, query_embedding)) for c in candidates]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return [c for c, _ in scored[:top_k]]


class AtlasVectorStore:
    """Real implementation. Not implemented yet — needs a $vectorSearch aggregation
    against a Vector Search index on chunks.embedding, which itself needs real (non-fake)
    embeddings to be meaningful. Wire up once VoyageEmbeddingsProvider exists.
    """

    def __init__(self, chunks_col):
        self.chunks_col = chunks_col

    async def search(self, *, bot_id: str, query_embedding: list[float], top_k: int) -> list[Chunk]:
        raise NotImplementedError(
            "Atlas Vector Search isn't wired up yet — create the index once real "
            "embeddings exist, then implement the $vectorSearch aggregation here."
        )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
