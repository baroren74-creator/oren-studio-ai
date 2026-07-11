"""The ONE place in the codebase that calls an LLM — see
docs/open-source-landscape.md section 2 and docs/decisions.md (LiteLLM
adoption). Every Agent that needs an LLM calls `complete()` here; nothing
else imports `litellm`, `anthropic`, or `openai` directly. That's what
makes "swap providers via config, not code" (docs/architecture.md
Future AI Providers) actually true instead of aspirational.

Default model is Claude (Anthropic) per docs/open-source-landscape.md
section 1 synthesis. Swapping to OpenAI/Gemini/a local model is a
one-line change to `DEFAULT_MODEL` or an env var — never a code change
in any Agent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

Role = Literal["system", "user", "assistant"]

# LiteLLM's model-name convention: "<provider>/<model>". Override via
# OREN_STUDIO_LLM_MODEL env var without touching any Agent code.
DEFAULT_MODEL = os.environ.get("OREN_STUDIO_LLM_MODEL", "anthropic/claude-3-5-sonnet-20241022")


@dataclass
class LLMMessage:
    role: Role
    content: str


@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class LLMError(RuntimeError):
    """Raised for any LLM call failure — Agents catch this specifically
    (docs/standards.md section 8) rather than a bare Exception, so a
    provider outage produces AgentOutput(status="failed") with a clear
    reason instead of an unhandled crash."""


def complete(
    messages: list[LLMMessage],
    *,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> LLMResponse:
    """Synchronous single-turn completion. Agents that need streaming or
    tool-calling get a dedicated function added here later — deliberately
    minimal for the first real Agent (Research Agent, docs/roadmap.md
    Phase 2.3)."""

    import litellm

    try:
        response = litellm.completion(
            model=model or DEFAULT_MODEL,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            max_tokens=max_tokens,
            temperature=temperature,
        )
    except Exception as exc:  # noqa: BLE001 — deliberately broad, re-raised as our own type
        raise LLMError(f"LLM call failed ({model or DEFAULT_MODEL}): {exc}") from exc

    choice = response.choices[0]
    usage = response.usage
    cost_usd = 0.0
    try:
        cost_usd = litellm.completion_cost(completion_response=response)
    except Exception:  # noqa: BLE001 — cost tracking is best-effort, never fatal
        pass

    return LLMResponse(
        text=choice.message.content or "",
        model=response.model,
        input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        cost_usd=cost_usd,
    )
