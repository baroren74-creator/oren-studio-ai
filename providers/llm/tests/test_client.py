"""providers/llm/llm_provider/client.py — the one place that calls
litellm. Both complete() and embed() are mocked at the litellm boundary
(litellm.completion / litellm.embedding) rather than hit for real: no
API key exists in this sandbox for any provider (Anthropic or Voyage),
consistent with every other Agent-level test in this repo — see
agents/research_agent/tests/test_agent.py's module docstring for the
same reasoning.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from llm_provider.client import EmbeddingResponse, LLMError, LLMMessage, LLMResponse, complete, embed


def _fake_completion_response(text: str = "hello") -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
        model="anthropic/claude-3-5-sonnet-20241022",
    )


def test_complete_returns_parsed_response():
    with (
        patch("litellm.completion", return_value=_fake_completion_response("hi there")),
        patch("litellm.completion_cost", return_value=0.001),
    ):
        result = complete([LLMMessage(role="user", content="hello")])

    assert isinstance(result, LLMResponse)
    assert result.text == "hi there"
    assert result.input_tokens == 10
    assert result.output_tokens == 5
    assert result.cost_usd == pytest.approx(0.001)


def test_complete_wraps_any_failure_as_llm_error():
    with patch("litellm.completion", side_effect=RuntimeError("provider down")):
        with pytest.raises(LLMError, match="LLM call failed"):
            complete([LLMMessage(role="user", content="hello")])


def test_complete_cost_tracking_failure_is_non_fatal():
    with (
        patch("litellm.completion", return_value=_fake_completion_response()),
        patch("litellm.completion_cost", side_effect=RuntimeError("no pricing data")),
    ):
        result = complete([LLMMessage(role="user", content="hello")])

    assert result.cost_usd == 0.0  # falls back cleanly, doesn't crash the whole call


def _fake_embedding_response(vectors: list[list[float]]) -> SimpleNamespace:
    return SimpleNamespace(
        data=[{"embedding": v, "index": i} for i, v in enumerate(vectors)],
        usage=SimpleNamespace(prompt_tokens=42, total_tokens=42),
        model="voyage/voyage-3-lite",
    )


def test_embed_returns_one_vector_per_input_in_order():
    fake_vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    with (
        patch("litellm.embedding", return_value=_fake_embedding_response(fake_vectors)) as mock_embed,
        patch("litellm.completion_cost", return_value=0.0002),
    ):
        result = embed(["first chunk", "second chunk"])

    mock_embed.assert_called_once_with(model="voyage/voyage-3-lite", input=["first chunk", "second chunk"])
    assert isinstance(result, EmbeddingResponse)
    assert result.vectors == fake_vectors
    assert result.tokens_used == 42
    assert result.cost_usd == pytest.approx(0.0002)


def test_embed_handles_attribute_style_response_items():
    """Defensive branch: some providers' embedding items come back as
    objects with an `.embedding` attribute rather than plain dicts."""
    item = SimpleNamespace(embedding=[0.7, 0.8])
    fake_response = SimpleNamespace(
        data=[item], usage=SimpleNamespace(prompt_tokens=5, total_tokens=5), model="voyage/voyage-3-lite"
    )
    with patch("litellm.embedding", return_value=fake_response):
        result = embed(["one chunk"])

    assert result.vectors == [[0.7, 0.8]]


def test_embed_wraps_any_failure_as_llm_error():
    with patch("litellm.embedding", side_effect=RuntimeError("403 Forbidden")):
        with pytest.raises(LLMError, match="embedding call failed"):
            embed(["hello"])


def test_embed_respects_model_override():
    with (
        patch("litellm.embedding", return_value=_fake_embedding_response([[0.1]])) as mock_embed,
        patch("litellm.completion_cost", return_value=0.0),
    ):
        embed(["x"], model="voyage/voyage-3-large")

    assert mock_embed.call_args.kwargs["model"] == "voyage/voyage-3-large"
