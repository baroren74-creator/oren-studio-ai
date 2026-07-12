"""Research Agent — see docs/agents.md.

Phase 2.3 (docs/roadmap.md): real logic for GitHub sources — fetch a
repo digest (github_source.py, Gitingest) and summarize it via the LLM
provider (providers/llm, LiteLLM).

Phase 2.5: real logic for YouTube sources — fetch a transcript
(youtube_source.py, youtube-transcript-api; see that module's docstring
and docs/decisions.md ADR-013 for why this replaced the originally-
specced faster-whisper approach) and summarize it the same way.

Remaining source types (articles, tweets) are not implemented yet and
return status="skipped" rather than pretending to handle them.

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
from agents.research_agent.youtube_source import YouTubeSourceError, fetch_video_transcript

NAME = "research_agent"
VERSION = "0.3.0"  # bumped for Phase 2.5 (YouTube support)

SUPPORTED_SOURCE_TYPES = ("github", "youtube")

GITHUB_SYSTEM_PROMPT = (
    "You are the Research Agent inside Oren Studio AI, a personal Hebrew "
    "tech-content studio. Given a GitHub repository's file digest, write: "
    "(1) a 2-3 sentence summary of what the project does and why it might "
    "be interesting for a short tech video, and (2) 3-5 short bullet key "
    "points (one per line, each starting with '- '). Be concrete — name "
    "actual things from the code/README, don't write generic filler. "
    "Respond in English regardless of the repo's language; Script Agent "
    "handles Hebrew translation later (docs/agents.md)."
)

YOUTUBE_SYSTEM_PROMPT = (
    "You are the Research Agent inside Oren Studio AI, a personal Hebrew "
    "tech-content studio. Given a YouTube video's transcript (auto-"
    "generated or human-written captions — expect imperfect punctuation "
    "and no speaker labels), write: (1) a 2-3 sentence summary of what "
    "the video covers and why it might be interesting for a short tech "
    "video reacting to or building on it, and (2) 3-5 short bullet key "
    "points (one per line, each starting with '- '). Be concrete — name "
    "actual things said in the video, don't write generic filler. "
    "Respond in English regardless of the transcript's language; Script "
    "Agent handles Hebrew translation later (docs/agents.md)."
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


def _summarize(*, system_prompt: str, prompt_text: str, extra_result: dict) -> AgentOutput:
    """Shared LLM-summarization tail for every source type: call the LLM
    provider, parse the response, build the AgentOutput. `extra_result`
    is source-type-specific context (e.g. GitHub's `repo_summary`,
    YouTube's `video_id`) merged into `result` alongside the common
    `summary`/`key_points` — kept out of the parsed text itself so
    _parse_key_points doesn't need to know which source type it's
    looking at."""
    try:
        response = complete(
            [
                LLMMessage(role="system", content=system_prompt),
                LLMMessage(role="user", content=prompt_text),
            ],
            max_tokens=600,
        )
    except LLMError as exc:
        return AgentOutput(status="failed", result={"reason": str(exc), **extra_result})

    summary, key_points = _parse_key_points(response.text)

    return AgentOutput(
        status="success",
        result={**extra_result, "summary": summary, "key_points": key_points},
        cost=CostInfo(
            tokens_used=response.input_tokens + response.output_tokens,
            cost_usd=response.cost_usd,
            provider=response.model,
        ),
        next_event="research.completed",
    )


class ResearchAgent:
    name = NAME
    version = VERSION

    async def run(self, input: AgentInput) -> AgentOutput:
        source_type = input.payload.get("source_type")
        source_url = input.payload.get("source_url")

        if source_type not in SUPPORTED_SOURCE_TYPES:
            return AgentOutput(
                status="skipped",
                result={"reason": f"source_type '{source_type}' not implemented yet (supported: {SUPPORTED_SOURCE_TYPES})"},
                next_event=None,
            )

        if not source_url:
            return AgentOutput(status="failed", result={"reason": "payload.source_url is required"})

        if source_type == "github":
            try:
                digest = await fetch_repo_digest(source_url)
            except GitHubSourceError as exc:
                return AgentOutput(status="failed", result={"reason": str(exc)})

            return _summarize(
                system_prompt=GITHUB_SYSTEM_PROMPT,
                prompt_text=digest.as_prompt_text(),
                extra_result={"source_url": source_url, "repo_summary": digest.summary},
            )

        # source_type == "youtube" — fetch_video_transcript is a regular
        # sync call (youtube-transcript-api is requests-based, no event
        # loop involved), unlike fetch_repo_digest which specifically
        # needs `await` (see github_source.py's comment on gitingest).
        try:
            transcript = fetch_video_transcript(source_url)
        except YouTubeSourceError as exc:
            return AgentOutput(status="failed", result={"reason": str(exc)})

        return _summarize(
            system_prompt=YOUTUBE_SYSTEM_PROMPT,
            prompt_text=transcript.as_prompt_text(),
            extra_result={
                "source_url": source_url,
                "video_id": transcript.video_id,
                "transcript_language": transcript.language_code,
                "transcript_is_generated": transcript.is_generated,
            },
        )


agent = ResearchAgent()
default_registry.register(NAME, lambda: agent)
