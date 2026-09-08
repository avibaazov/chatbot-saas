"""LLM provider abstraction for the bot's answer generation. ClaudeProvider is the real
target (AGENTS.md §4 — Haiku default, Sonnet upgrade tier) but isn't wired up until
ANTHROPIC_API_KEY exists. FakeLLMProvider is a deterministic stand-in so app/services/rag.py
is testable today.
"""

from __future__ import annotations

from typing import Protocol

from app.models.chunk import Chunk


class LLMProvider(Protocol):
    async def generate(self, *, system_prompt: str, question: str, context_chunks: list[Chunk]) -> str: ...


class FakeLLMProvider:
    """Echoes the question and how many context chunks it saw. Enough to prove the RAG
    pipeline wires retrieval -> prompt -> generation correctly, without an Anthropic key.
    """

    async def generate(self, *, system_prompt: str, question: str, context_chunks: list[Chunk]) -> str:
        return f"[fake answer] question={question!r} context_chunks={len(context_chunks)}"


class ClaudeProvider:
    """Real provider. Not implemented yet — wire up the Anthropic SDK call here once
    ANTHROPIC_API_KEY exists. model_tier ("haiku" | "sonnet") comes from Bot.config.
    """

    def __init__(self, api_key: str, model_tier: str = "haiku"):
        self.api_key = api_key
        self.model_tier = model_tier

    async def generate(self, *, system_prompt: str, question: str, context_chunks: list[Chunk]) -> str:
        raise NotImplementedError(
            "ANTHROPIC_API_KEY is set but the Claude client isn't wired up yet."
        )


def get_llm_provider(settings, model_tier: str = "haiku") -> LLMProvider:
    if settings.anthropic_api_key:
        return ClaudeProvider(settings.anthropic_api_key, model_tier)
    return FakeLLMProvider()
