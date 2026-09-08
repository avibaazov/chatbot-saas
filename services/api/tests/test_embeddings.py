from types import SimpleNamespace

from app.services.embeddings import (
    DEFAULT_VOYAGE_MODEL,
    FakeEmbeddingsProvider,
    VoyageEmbeddingsProvider,
    get_embeddings_provider,
)


class FakeVoyageClient:
    """Records each embed() batch and returns one vector per input text."""

    def __init__(self):
        self.batches: list[list[str]] = []
        self.model: str | None = None

    async def embed(self, texts, model):
        self.batches.append(list(texts))
        self.model = model
        return SimpleNamespace(embeddings=[[float(len(t))] for t in texts])


# --- provider selection ---------------------------------------------------------


def test_get_embeddings_provider_returns_fake_without_key():
    provider = get_embeddings_provider(SimpleNamespace(voyage_api_key=""))
    assert isinstance(provider, FakeEmbeddingsProvider)


def test_get_embeddings_provider_returns_voyage_with_key(monkeypatch):
    class _Patched(VoyageEmbeddingsProvider):
        def __init__(self, api_key, model=DEFAULT_VOYAGE_MODEL):
            super().__init__(api_key, model, client=FakeVoyageClient())

    monkeypatch.setattr("app.services.embeddings.VoyageEmbeddingsProvider", _Patched)
    provider = get_embeddings_provider(SimpleNamespace(voyage_api_key="pa-x"))
    assert isinstance(provider, VoyageEmbeddingsProvider)


# --- VoyageEmbeddingsProvider.embed ------------------------------------------


async def test_voyage_embed_returns_one_vector_per_text():
    client = FakeVoyageClient()
    provider = VoyageEmbeddingsProvider("pa-x", client=client)

    vectors = await provider.embed(["a", "bb", "ccc"])

    assert vectors == [[1.0], [2.0], [3.0]]
    assert client.model == DEFAULT_VOYAGE_MODEL
    assert client.batches == [["a", "bb", "ccc"]]


async def test_voyage_embed_splits_into_batches_of_128():
    client = FakeVoyageClient()
    provider = VoyageEmbeddingsProvider("pa-x", client=client)

    texts = [f"t{i}" for i in range(300)]
    vectors = await provider.embed(texts)

    assert len(vectors) == 300
    assert [len(b) for b in client.batches] == [128, 128, 44]
