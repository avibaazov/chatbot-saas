import pytest

from app.models.document import DocumentStatus
from app.services.chunking import chunk_text
from app.services.embeddings import FakeEmbeddingsProvider
from app.services.ingestion import ingest_document, ingest_url
from app.services.queue import InMemoryQueue


class FakeDocumentsCollection:
    """Records every update_one call so tests can assert on the status transitions."""

    def __init__(self):
        self.updates: list[dict] = []

    async def update_one(self, filter, update):
        self.updates.append(update["$set"])

    @property
    def statuses(self) -> list[str]:
        return [u["status"] for u in self.updates if "status" in u]


class FakeChunksCollection:
    def __init__(self):
        self.inserted: list[dict] = []

    async def insert_many(self, documents):
        self.inserted.extend(documents)


# --- chunking -----------------------------------------------------------------


def test_chunk_text_splits_with_overlap():
    text = "a" * 1000
    chunks = chunk_text(text, chunk_size=400, overlap=50)
    assert len(chunks) == 3
    # last 50 chars of chunk[0] should equal first 50 of chunk[1] (the overlap)
    assert chunks[0][-50:] == chunks[1][:50]


def test_chunk_text_empty_returns_no_chunks():
    assert chunk_text("   ") == []


def test_chunk_text_rejects_bad_overlap():
    with pytest.raises(ValueError):
        chunk_text("hello", chunk_size=10, overlap=10)


# --- fake embeddings ------------------------------------------------------------


async def test_fake_embeddings_deterministic_and_right_shape():
    provider = FakeEmbeddingsProvider()
    vectors = await provider.embed(["hello", "hello", "world"])
    assert vectors[0] == vectors[1]  # deterministic
    assert vectors[0] != vectors[2]
    assert len(vectors[0]) == FakeEmbeddingsProvider.dimensions


# --- full pipeline ----------------------------------------------------------


async def test_ingest_document_happy_path():
    documents_col = FakeDocumentsCollection()
    chunks_col = FakeChunksCollection()

    await ingest_document(
        documents_col=documents_col,
        chunks_col=chunks_col,
        document_id="doc1",
        text="hello world " * 200,  # long enough to produce multiple chunks
        bot_id="bot1",
        embeddings=FakeEmbeddingsProvider(),
    )

    assert documents_col.statuses == [DocumentStatus.processing, DocumentStatus.ready]
    assert len(chunks_col.inserted) > 1
    assert all(c["bot_id"] == "bot1" for c in chunks_col.inserted)
    assert all(len(c["embedding"]) == FakeEmbeddingsProvider.dimensions for c in chunks_col.inserted)


async def test_ingest_document_empty_text_marks_failed():
    documents_col = FakeDocumentsCollection()
    chunks_col = FakeChunksCollection()

    with pytest.raises(ValueError):
        await ingest_document(
            documents_col=documents_col,
            chunks_col=chunks_col,
            document_id="doc1",
            text="   ",
            bot_id="bot1",
            embeddings=FakeEmbeddingsProvider(),
        )

    assert documents_col.statuses == [DocumentStatus.processing, DocumentStatus.failed]
    assert documents_col.updates[-1]["error"]
    assert chunks_col.inserted == []


# --- URL ingestion ----------------------------------------------------------


async def test_ingest_url_fetches_then_runs_pipeline_and_sets_title():
    documents_col = FakeDocumentsCollection()
    chunks_col = FakeChunksCollection()

    async def fake_fetch(url):
        assert url == "https://plants.example/care"
        return "Fig Care Guide", "water it weekly. " * 200

    await ingest_url(
        documents_col=documents_col,
        chunks_col=chunks_col,
        document_id="doc1",
        url="https://plants.example/care",
        bot_id="bot1",
        embeddings=FakeEmbeddingsProvider(),
        fetch=fake_fetch,
    )

    assert {"filename": "Fig Care Guide"} in documents_col.updates
    assert documents_col.statuses == [DocumentStatus.processing, DocumentStatus.ready]
    assert len(chunks_col.inserted) > 1


async def test_ingest_url_marks_failed_when_fetch_fails():
    documents_col = FakeDocumentsCollection()
    chunks_col = FakeChunksCollection()

    async def failing_fetch(url):
        raise RuntimeError("no readable text found — the page may need JavaScript to render")

    with pytest.raises(RuntimeError):
        await ingest_url(
            documents_col=documents_col,
            chunks_col=chunks_col,
            document_id="doc1",
            url="https://spa.example/",
            bot_id="bot1",
            embeddings=FakeEmbeddingsProvider(),
            fetch=failing_fetch,
        )

    assert documents_col.statuses == [DocumentStatus.failed]
    assert "JavaScript" in documents_col.updates[-1]["error"]
    assert chunks_col.inserted == []


# --- queue --------------------------------------------------------------------


async def test_in_memory_queue_runs_job_inline():
    ran = False

    async def job():
        nonlocal ran
        ran = True

    await InMemoryQueue().enqueue(job)
    assert ran is True
