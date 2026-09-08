"""LLM provider abstraction for the bot's answer generation. ClaudeProvider is the real
implementation (AGENTS.md §4 — Haiku default, Sonnet upgrade tier); FakeLLMProvider is a
deterministic stand-in so app/services/rag.py is testable without an Anthropic key.
"""

from __future__ import annotations

from typing import Protocol

from app.models.chunk import Chunk

# model_tier ("haiku" | "sonnet") comes from Bot.config — see app/models/bot.py.
# Kept here rather than in config/env because it's a code-level product decision, not
# per-environment deployment config.
MODEL_IDS: dict[str, str] = {
    "haiku": "claude-haiku-4-5",
    "sonnet": "claude-sonnet-5",
}
DEFAULT_MODEL_TIER = "haiku"
MAX_ANSWER_TOKENS = 1024

_GROUNDING_INSTRUCTION = (
    "Answer the user's question using only the context below, which was retrieved from "
    "the site owner's own content. If the context does not contain the answer, say you "
    "don't have that information rather than guessing. Do not mention the context itself."
)


class LLMProvider(Protocol):
    async def generate(self, *, system_prompt: str, question: str, context_chunks: list[Chunk]) -> str: ...


def _build_system_prompt(system_prompt: str, context_chunks: list[Chunk]) -> str:
    context = "\n\n---\n\n".join(c.text for c in context_chunks) or "(no relevant content found)"
    return f"{system_prompt.strip()}\n\n{_GROUNDING_INSTRUCTION}\n\n<context>\n{context}\n</context>"


class FakeLLMProvider:
    """Echoes the question and how many context chunks it saw. Enough to prove the RAG
    pipeline wires retrieval -> prompt -> generation correctly, without an Anthropic key.
    """

    async def generate(self, *, system_prompt: str, question: str, context_chunks: list[Chunk]) -> str:
        return f"[fake answer] question={question!r} context_chunks={len(context_chunks)}"


class ClaudeProvider:
    """Real provider — calls the Anthropic Messages API. Retrieval context goes in the
    system prompt with a grounding instruction; the raw question is the only user turn.
    """

    def __init__(self, api_key: str, model_tier: str = DEFAULT_MODEL_TIER, *, client=None):
        if client is None:
            # Imported lazily so the package is only required when a real key is configured.
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=api_key)
        self._client = client
        self._model = MODEL_IDS.get(model_tier, MODEL_IDS[DEFAULT_MODEL_TIER])

    async def generate(self, *, system_prompt: str, question: str, context_chunks: list[Chunk]) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=MAX_ANSWER_TOKENS,
            system=_build_system_prompt(system_prompt, context_chunks),
            messages=[{"role": "user", "content": question}],
        )
        return "".join(block.text for block in response.content if block.type == "text").strip()


def get_llm_provider(settings, model_tier: str = DEFAULT_MODEL_TIER) -> LLMProvider:
    if settings.anthropic_api_key:
        return ClaudeProvider(settings.anthropic_api_key, model_tier)
    return FakeLLMProvider()
