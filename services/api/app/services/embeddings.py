"""Embedding provider abstraction. The ingestion pipeline and RAG retrieval only depend
on this Protocol, so swapping FakeEmbeddingsProvider for the real Voyage AI client
(AGENTS.md §4) is contained to get_embeddings_provider() — nothing else moves.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

# Voyage's default general-purpose model. A code-level product choice, not per-environment
# deployment config, so it lives here rather than in settings/env.
DEFAULT_VOYAGE_MODEL = "voyage-3.5"
_VOYAGE_MAX_BATCH = 128


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
    """Real provider — calls Voyage AI. Fails loudly on a misconfigured key rather than
    silently falling back to fake vectors. Requests are split into Voyage's max batch size.
    """

    def __init__(self, api_key: str, model: str = DEFAULT_VOYAGE_MODEL, *, client=None):
        if client is None:
            # Imported lazily so the package is only required when a real key is configured.
            import voyageai

            client = voyageai.AsyncClient(api_key=api_key)
        self._client = client
        self._model = model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), _VOYAGE_MAX_BATCH):
            batch = texts[start : start + _VOYAGE_MAX_BATCH]
            result = await self._client.embed(batch, model=self._model)
            vectors.extend(result.embeddings)
        return vectors


def get_embeddings_provider(settings) -> EmbeddingsProvider:
    if settings.voyage_api_key:
        return VoyageEmbeddingsProvider(settings.voyage_api_key)
    return FakeEmbeddingsProvider()
