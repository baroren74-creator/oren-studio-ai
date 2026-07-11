"""Research Agent — see docs/agents.md.

Phase 2.3 (docs/roadmap.md): real logic for GitHub sources — fetch a
repo digest (github_source.py, Gitingest) and summarize it via the LLM
provider (providers/llm, LiteLLM). Other source types (YouTube, articles,
tweets) are not implemented yet (Phase 2.4+) and return status="skipped"
rather than pretending to handle them.

This replaces the Stub Agent registration from Phase 1.18 — note that
NOTHING about how it's registered or called changed (core.registry,
core.schemas.agent.Agent contract). That's the entire point of the Agent
contract: swapping stub-for-real is invisible to the Orchestrator.
"""

from __future__ import annotations

import sys
from pathlib import Path

# providers/llm is a sibling package, not installed via the (not-yet-set-up)
# workspace package manager — see docs/roadmap.md for when a proper
# monorepo Python tool (uv/pdm workspaces) replaces this sys.path shim.
_PROVIDERS_LLM = Path(__file__).resolve().parents[2] / "providers" / "llm"
if str(_PROVIDERS_LLM) not in sys.path:
    sys.path.insert(0, str(_PROVIDERS_LLM))

from core.registry import default_registry
from core.schemas.agent import AgentInput, AgentOutput, CostInfo
from llm_provider import LLMError, LLMMessage, complete

from agents.research_agent.github_source import GitHubSourceError, fetch_repo_digest

NAME = "research_agent"
VERSION = "0.2.0"  # bumped from the 0.0.1-stub baseline — real logic, Phase 2.3

SYSTEM_PROMPT = (
    "You are the Research Agent inside Oren Studio AI, a personal Hebrew "
    "tech-content studio. Given a GitHub repository's file digest, write: "
    "(1) a 2-3 sentence summary of what the project does and why it might "
    "be interesting for a short tech video, and (2) 3-5 short bullet key "
    "points (one per line, each starting with '- '). Be concrete — name "
    "actual things from the code/README, don't write generic filler. "
    "Respond in English regardless of the repo's language; Script Agent "
    "handles Hebrew translation later (docs/agents.md)."
)


def _parse_key_points(text: str) -> tuple[str, list[str]]:
    """Best-effort split of the LLM response into (summary, key_points).
    Deliberately lenient — Phase 2.3 scope is 'works on real repos', not
    'never needs a human to glance at the output'."""
    lines = text.strip().splitlines()
    summary_lines: list[str] = []
    key_points: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("-") or stripped.startswith("*"):
            key_points.append(stripped.lstrip("-*").strip())
        elif stripped and not key_points:
            summary_lines.append(stripped)
    summary = " ".join(summary_lines).strip() or text.strip()
    return summary, key_points


class ResearchAgent:
    name = NAME
    version = VERSION

    async def run(self, input: AgentInput) -> AgentOutput:
        source_type = input.payload.get("source_type")
        source_url = input.payload.get("source_url")

        if source_type != "github":
            return AgentOutput(
                status="skipped",
                result={"reason": f"source_type '{source_type}' not implemented yet (Phase 2.3 is GitHub-only)"},
                next_event=None,
            )

        if not source_url:
            return AgentOutput(status="failed", result={"reason": "payload.source_url is required"})

        try:
            digest = await fetch_repo_digest(source_url)
        except GitHubSourceError as exc:
            return AgentOutput(status="failed", result={"reason": str(exc)})

        try:
            response = complete(
                [
                    LLMMessage(role="system", content=SYSTEM_PROMPT),
                    LLMMessage(role="user", content=digest.as_prompt_text()),
                ],
                max_tokens=600,
            )
        except LLMError as exc:
            return AgentOutput(status="failed", result={"reason": str(exc), "digest_summary": digest.summary})

        summary, key_points = _parse_key_points(response.text)

        return AgentOutput(
            status="success",
            result={
                "source_url": source_url,
                "repo_summary": digest.summary,
                "summary": summary,
                "key_points": key_points,
            },
            cost=CostInfo(
                tokens_used=response.input_tokens + response.output_tokens,
                cost_usd=response.cost_usd,
                provider=response.model,
            ),
            next_event="research.completed",
        )


agent = ResearchAgent()
default_registry.register(NAME, lambda: agent)
