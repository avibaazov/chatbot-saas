"""Embedding provider abstraction. The ingestion pipeline only depends on this Protocol,
so swapping FakeEmbeddingsProvider for a real one (Voyage AI, per AGENTS.md §4) later is a
one-line change in get_embeddings_provider() — nothing else moves.
"""

from __future__ import annotations

import hashlib
from typing import Protocol


class EmbeddingsProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class FakeEmbeddingsProvider:
    """Deterministic, dependency-free stand-in for local dev/tests. Vectors are NOT
    semantically meaningful — retrieval quality on these is garbage by design. This exists
    purely so the pipeline's plumbing (chunk -> embed -> upsert -> status) is exercisable
    without a Voyage/OpenAI API key.
    """

    dimensions = 8

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._fake_vector(t) for t in texts]

    def _fake_vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        return [b / 255 for b in digest[: self.dimensions]]


class VoyageEmbeddingsProvider:
    """Real provider. Not implemented yet — wire up the Voyage AI client here once
    VOYAGE_API_KEY exists. Raises rather than silently falling back so a misconfigured key
    fails loudly instead of quietly training on fake vectors.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "VOYAGE_API_KEY is set but the Voyage client isn't wired up yet."
        )


def get_embeddings_provider(settings) -> EmbeddingsProvider:
    if settings.voyage_api_key:
        return VoyageEmbeddingsProvider(settings.voyage_api_key)
    return FakeEmbeddingsProvider()
