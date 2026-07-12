"""Trend Agent — see docs/agents.md.

Phase 2.10 (docs/roadmap.md), v1: GitHub Trending only (free, no API
key, and the one external domain this project's sandbox network
allowlist actually includes — see github_trending_source.py's
docstring). Hacker News (v2) and Product Hunt (v3) are the same "2.10"
roadmap item but not implemented yet; Reddit (v4) and Twitter/X (v5,
deliberately deferred) are later still.

Unlike every other Agent so far, Trend Agent is NOT a node in
workflows/graph.py — it doesn't operate on an existing project's
pipeline run, it discovers *candidate* ideas independent of any project
(docs/database.md's `ideas.project_id` is nullable for exactly this).
It still satisfies the same Agent contract (core.schemas.agent.Agent) so
whatever eventually triggers it (a scheduler, a manual "scan now" API
route — neither built yet, see docs/roadmap.md 2.13) can call it the
same uniform way every other Agent is called; `run_id`/`project_id` on
its AgentInput are accepted but not meaningfully used.

No `ideas` table row is written here yet — same incremental-persistence
pattern as agents/research_agent/agent.py's research_notes (Phase 2.3):
land the real discovery logic first, wire it into a table once the
feature that actually needs it (Idea Backlog UI, Phase 2.13) exists to
consume it, rather than building persistence for a UI that doesn't exist
yet and might shape the schema differently once it does.
"""

from __future__ import annotations

from core.registry import default_registry
from core.schemas.agent import AgentInput, AgentOutput

from agents.trend_agent.github_trending_source import TrendSourceError, fetch_trending_repos

NAME = "trend_agent"
VERSION = "0.1.0"  # bumped from the 0.0.1-stub baseline — real logic, Phase 2.10 (v1: GitHub Trending)

MAX_IDEAS = 25  # defensive cap — GitHub Trending returns ~25 rows per page, no pagination needed at this scale


def _repo_to_idea(repo) -> dict:
    return {
        "title": repo.full_name,
        "source_type": "github",
        "source_url": repo.url,
        "description": repo.description,
        "tags": [repo.language] if repo.language else [],
        "stars_total": repo.stars_total,
        "stars_today": repo.stars_today,
    }


class TrendAgent:
    name = NAME
    version = VERSION

    async def run(self, input: AgentInput) -> AgentOutput:
        language = input.payload.get("language")
        since = input.payload.get("since", "daily")

        try:
            repos = fetch_trending_repos(language=language, since=since)
        except TrendSourceError as exc:
            return AgentOutput(status="failed", result={"reason": str(exc)})

        ideas = [_repo_to_idea(repo) for repo in repos[:MAX_IDEAS]]

        return AgentOutput(
            status="success",
            result={"source": "github_trending", "language": language, "since": since, "ideas": ideas},
            next_event="trend.discovered",
        )


agent = TrendAgent()
default_registry.register(NAME, lambda: agent)
