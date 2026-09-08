from types import SimpleNamespace

from app.models.chunk import Chunk
from app.services.llm import (
    MODEL_IDS,
    ClaudeProvider,
    FakeLLMProvider,
    _build_system_prompt,
    get_llm_provider,
)


def _chunk(text: str) -> Chunk:
    return Chunk(document_id="d1", bot_id="b1", chunk_index=0, text=text, embedding=[0.0])


class FakeMessages:
    def __init__(self, recorder: dict):
        self._recorder = recorder

    async def create(self, **kwargs):
        self._recorder.update(kwargs)
        return SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text="the "),
                SimpleNamespace(type="thinking", thinking="ignore me"),
                SimpleNamespace(type="text", text="answer"),
            ]
        )


class FakeAnthropicClient:
    def __init__(self):
        self.calls: dict = {}
        self.messages = FakeMessages(self.calls)


# --- prompt construction ----------------------------------------------------


def test_build_system_prompt_includes_context_and_grounding():
    prompt = _build_system_prompt("You are Planty.", [_chunk("water weekly"), _chunk("bright light")])
    assert "You are Planty." in prompt
    assert "water weekly" in prompt
    assert "bright light" in prompt
    assert "<context>" in prompt


def test_build_system_prompt_handles_no_chunks():
    prompt = _build_system_prompt("You are Planty.", [])
    assert "no relevant content found" in prompt


# --- provider selection ---------------------------------------------------------


def test_get_llm_provider_returns_fake_without_key():
    assert isinstance(get_llm_provider(SimpleNamespace(anthropic_api_key="")), FakeLLMProvider)


def test_get_llm_provider_returns_claude_with_key(monkeypatch):
    # Inject a fake client via a subclass so no real anthropic package/network is needed.
    created = {}

    class _Patched(ClaudeProvider):
        def __init__(self, api_key, model_tier="haiku"):
            created["tier"] = model_tier
            super().__init__(api_key, model_tier, client=FakeAnthropicClient())

    monkeypatch.setattr("app.services.llm.ClaudeProvider", _Patched)
    provider = get_llm_provider(SimpleNamespace(anthropic_api_key="sk-x"), model_tier="sonnet")
    assert isinstance(provider, ClaudeProvider)
    assert created["tier"] == "sonnet"


# --- ClaudeProvider.generate --------------------------------------------------


async def test_claude_provider_generate_joins_text_blocks_and_sends_context():
    client = FakeAnthropicClient()
    provider = ClaudeProvider("sk-x", "sonnet", client=client)

    answer = await provider.generate(
        system_prompt="You are Planty.",
        question="How often do I water?",
        context_chunks=[_chunk("water weekly")],
    )

    assert answer == "the answer"
    assert client.calls["model"] == MODEL_IDS["sonnet"]
    assert client.calls["messages"] == [{"role": "user", "content": "How often do I water?"}]
    assert "water weekly" in client.calls["system"]


async def test_claude_provider_defaults_unknown_tier_to_haiku():
    client = FakeAnthropicClient()
    provider = ClaudeProvider("sk-x", "enterprise-mega", client=client)
    await provider.generate(system_prompt="s", question="q", context_chunks=[])
    assert client.calls["model"] == MODEL_IDS["haiku"]
