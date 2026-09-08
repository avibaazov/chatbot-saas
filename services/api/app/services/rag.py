"""RAG inference: embed the question, retrieve relevant chunks, ask the LLM. This is the
bot's "brain" per AGENTS.md §4 — no bag-of-words classifier, no .pth files.
"""

from __future__ import annotations

from app.services.embeddings import EmbeddingsProvider
from app.services.llm import LLMProvider
from app.services.retrieval import VectorStore

DEFAULT_TOP_K = 5


async def answer_question(
    *,
    question: str,
    bot_id: str,
    system_prompt: str,
    embeddings: EmbeddingsProvider,
    vector_store: VectorStore,
    llm: LLMProvider,
    top_k: int = DEFAULT_TOP_K,
) -> str:
    [query_embedding] = await embeddings.embed([question])
    context_chunks = await vector_store.search(bot_id=bot_id, query_embedding=query_embedding, top_k=top_k)
    return await llm.generate(system_prompt=system_prompt, question=question, context_chunks=context_chunks)
