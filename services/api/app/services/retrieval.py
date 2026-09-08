"""Vector retrieval abstraction.

MongoBruteForceVectorStore is the real implementation in use right now: it loads a bot's
chunks from Mongo and ranks them by cosine similarity in Python. O(n) per query — perfectly
fine at today's per-bot chunk counts, and it works without an Atlas Search index, which a
meaningful $vectorSearch needs real (non-fake) embeddings to justify setting up. Swap for
AtlasVectorStore once VoyageEmbeddingsProvider exists and chunk volume actually warrants it.

InMemoryVectorStore is the same ranking logic over a plain list, kept separate for fast,
network-free unit tests (see tests/test_rag.py).
"""

from __future__ import annotations

import math
from typing import Protocol

from app.models.chunk import Chunk


class VectorStore(Protocol):
    async def search(self, *, bot_id: str, query_embedding: list[float], top_k: int) -> list[Chunk]: ...


def _rank(chunks: list[Chunk], query_embedding: list[float], top_k: int) -> list[Chunk]:
    scored = [(c, _cosine_similarity(c.embedding, query_embedding)) for c in chunks]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [c for c, _ in scored[:top_k]]


class InMemoryVectorStore:
    """Brute-force cosine similarity over an in-memory list of chunks — test-only stand-in
    for MongoBruteForceVectorStore, so tests don't need a live Mongo connection.
    """

    def __init__(self, chunks: list[Chunk] | None = None):
        self.chunks = chunks or []

    async def search(self, *, bot_id: str, query_embedding: list[float], top_k: int) -> list[Chunk]:
        candidates = [c for c in self.chunks if c.bot_id == bot_id]
        return _rank(candidates, query_embedding, top_k)


class MongoBruteForceVectorStore:
    """Real implementation: fetches every chunk for a bot from Mongo, ranks in Python. See
    module docstring for why this is the right tradeoff today instead of Atlas Vector Search.
    """

    def __init__(self, chunks_col):
        self.chunks_col = chunks_col

    async def search(self, *, bot_id: str, query_embedding: list[float], top_k: int) -> list[Chunk]:
        docs = await self.chunks_col.find({"bot_id": bot_id}).to_list(length=None)
        chunks = [Chunk(**doc) for doc in docs]
        return _rank(chunks, query_embedding, top_k)


class AtlasVectorStore:
    """Future implementation: a $vectorSearch aggregation against a Vector Search index on
    chunks.embedding. Worth building once per-bot chunk counts make MongoBruteForceVectorStore's
    O(n) scan too slow, and once embeddings are real enough for an index to be meaningful.
    """

    def __init__(self, chunks_col):
        self.chunks_col = chunks_col

    async def search(self, *, bot_id: str, query_embedding: list[float], top_k: int) -> list[Chunk]:
        raise NotImplementedError(
            "Atlas Vector Search isn't wired up yet — create the index once real "
            "embeddings exist and MongoBruteForceVectorStore's O(n) scan becomes the "
            "bottleneck, then implement the $vectorSearch aggregation here."
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
