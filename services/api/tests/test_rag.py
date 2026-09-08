from app.models.chunk import Chunk
from app.services.embeddings import FakeEmbeddingsProvider
from app.services.llm import FakeLLMProvider
from app.services.rag import answer_question
from app.services.retrieval import InMemoryVectorStore, _cosine_similarity


def _chunk(bot_id: str, embedding: list[float], text: str) -> Chunk:
    return Chunk(document_id="doc1", bot_id=bot_id, chunk_index=0, text=text, embedding=embedding)


# --- cosine similarity -------------------------------------------------------


def test_cosine_similarity_identical_vectors_is_one():
    assert _cosine_similarity([1, 0, 0], [1, 0, 0]) == 1.0


def test_cosine_similarity_orthogonal_vectors_is_zero():
    assert _cosine_similarity([1, 0], [0, 1]) == 0.0


def test_cosine_similarity_handles_zero_vector():
    assert _cosine_similarity([0, 0], [1, 1]) == 0.0


# --- InMemoryVectorStore ------------------------------------------------------


async def test_vector_store_ranks_by_similarity_and_scopes_to_bot():
    chunks = [
        _chunk("bot1", [1, 0], "closest"),
        _chunk("bot1", [0, 1], "farthest"),
        _chunk("bot1", [0.9, 0.1], "second closest"),
        _chunk("bot2", [1, 0], "wrong bot, should never show up"),
    ]
    store = InMemoryVectorStore(chunks)

    results = await store.search(bot_id="bot1", query_embedding=[1, 0], top_k=2)

    assert [c.text for c in results] == ["closest", "second closest"]
    assert all(c.bot_id == "bot1" for c in results)


# --- full RAG pipeline --------------------------------------------------------


async def test_answer_question_uses_retrieved_context():
    embeddings = FakeEmbeddingsProvider()
    [question_vector] = await embeddings.embed(["what are your hours?"])

    chunks = [
        _chunk("bot1", question_vector, "we are open 9-5"),  # identical -> most similar
        _chunk("bot1", [0.0] * FakeEmbeddingsProvider.dimensions, "unrelated"),
    ]
    store = InMemoryVectorStore(chunks)

    answer = await answer_question(
        question="what are your hours?",
        bot_id="bot1",
        system_prompt="You are a helpful assistant.",
        embeddings=embeddings,
        vector_store=store,
        llm=FakeLLMProvider(),
        top_k=1,
    )

    assert "what are your hours?" in answer
    assert "context_chunks=1" in answer
