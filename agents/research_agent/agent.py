"""Research Agent — see docs/agents.md.

Phase 2.3 (docs/roadmap.md): real logic for GitHub sources — fetch a
repo digest (github_source.py, Gitingest) and summarize it via the LLM
provider (providers/llm, LiteLLM).

Phase 2.5: real logic for YouTube sources — fetch a transcript
(youtube_source.py, youtube-transcript-api; see that module's docstring
and docs/decisions.md ADR-013 for why this replaced the originally-
specced faster-whisper approach) and summarize it the same way.

Phase 2.8: result now includes `raw_text` (the full digest/transcript
text, not just the LLM summary) alongside `summary`/`key_points` — this
is what the Knowledge Agent (agents/knowledge_agent) chunks, embeds, and
indexes into Qdrant. See workflows/graph.py's research_node/knowledge_node
for how it's threaded through StudioState.

Phase 3.9: real logic for Instagram Reels — but NOT automated fetching.
Investigated first (docs/roadmap.md's write-up has the full research):
Meta disabled most public Reel scraping/download endpoints in late 2024,
so yt-dlp/proxy-scraper approaches are unreliable and sit in grey-area
territory around Instagram's terms of service — not something to build
a "real Agent" on. The only options that are both reliable and
ToS-clean are (a) Instagram's official Graph API, which requires a
connected Business/Creator account and app review — deferred alongside
the rest of Phase 0.5's publishing-API applications, same reasoning as
ADR-011 — or (b) Oren pastes the caption/transcript himself, which is
what this ships: `source_type in MANUAL_TEXT_SOURCE_TYPES` (reel/post/
tweet — the free-text source types docs/database.md's schema already
listed) reads `payload.source_text` directly instead of fetching
anything, then runs it through the exact same summarize-and-index
pipeline `github`/`youtube` already use. Most of Oren's own content is
Instagram-first, so this was explicitly prioritized over polishing
already-working parts of the pipeline.

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
VERSION = "0.5.0"  # bumped: Phase 3.9 manual-text source types (reel/post/tweet)

# reel/post/tweet: no reliable, ToS-clean automated fetch exists (see this
# module's docstring) — Oren pastes the caption/transcript himself via
# payload.source_text instead of a fetchable source_url.
MANUAL_TEXT_SOURCE_TYPES = ("reel", "post", "tweet")
SUPPORTED_SOURCE_TYPES = ("github", "youtube") + MANUAL_TEXT_SOURCE_TYPES

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

MANUAL_TEXT_SYSTEM_PROMPT = (
    "You are the Research Agent inside Oren Studio AI, a personal Hebrew "
    "tech-content studio. Given the caption or transcript text a person "
    "pasted in from a social media post (Instagram Reel, post, or tweet — "
    "expect informal writing, hashtags, emoji, possibly Hebrew), write: "
    "(1) a 2-3 sentence summary of what the post is about and why it "
    "might be interesting to react to or build on for a short tech "
    "video, and (2) 3-5 short bullet key points (one per line, each "
    "starting with '- '). Be concrete — name actual things said in the "
    "text, don't write generic filler. Respond in English regardless of "
    "the source text's language; Script Agent handles Hebrew translation "
    "later (docs/agents.md)."
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

        if source_type in MANUAL_TEXT_SOURCE_TYPES:
            # No source_url fetch at all here — see this module's
            # docstring for why (no reliable, ToS-clean automated fetch
            # exists for Instagram as of this writing). source_url is
            # still accepted and carried through as a reference link
            # (e.g. "which Reel was this"), but it's optional and never
            # dereferenced.
            source_text = input.payload.get("source_text")
            if not source_text or not source_text.strip():
                return AgentOutput(status="failed", result={"reason": "payload.source_text is required for a manual-text source_type"})

            return _summarize(
                system_prompt=MANUAL_TEXT_SYSTEM_PROMPT,
                prompt_text=source_text.strip(),
                extra_result={
                    "source_url": source_url,
                    # Same reasoning as the GitHub/YouTube branches below —
                    # this is what the Knowledge Agent chunks/embeds/indexes.
                    # Here it's simply the pasted text verbatim, since
                    # there's no separate "raw digest" vs "LLM summary"
                    # distinction to make for manually-provided text.
                    "raw_text": source_text.strip(),
                },
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
                extra_result={
                    "source_url": source_url,
                    "repo_summary": digest.summary,
                    # Full digest text, not just the LLM's summary — this is
                    # what the Knowledge Agent (agents/knowledge_agent)
                    # chunks/embeds/indexes into Qdrant (Phase 2.8); the LLM
                    # summary above is for the human-facing research note,
                    # not what gets searched later.
                    "raw_text": digest.as_prompt_text(),
                },
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
                # See the GitHub branch's comment above — same reasoning,
                # this is what the Knowledge Agent indexes.
                "raw_text": transcript.as_prompt_text(),
            },
        )


agent = ResearchAgent()
default_registry.register(NAME, lambda: agent)
