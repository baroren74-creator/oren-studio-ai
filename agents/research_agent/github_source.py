"""GitHub repo -> LLM-ready digest, via Gitingest.

docs/open-source-landscape.md section 6: Gitingest (MIT) adopted for
exactly this. Deliberately scoped to the Research Agent's own folder
rather than providers/ — this isn't a swappable vendor interface like
LLM/video/voice (docs/architecture.md's Plugin Providers), it's a
specific implementation choice for one data source. Repomix
(docs/open-source-landscape.md) is the documented alternative if
Gitingest's output proves too large/unwieldy for bigger repos later.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RepoDigest:
    source_url: str
    summary: str
    tree: str
    content: str

    def as_prompt_text(self, max_content_chars: int = 12_000) -> str:
        """Truncate defensively — a real repo can be far larger than any
        prompt budget. Phase 2.6's idea-scoring gate runs on this before
        anything more expensive happens (ADR-003), so keep it cheap."""
        content = self.content
        if len(content) > max_content_chars:
            content = content[:max_content_chars] + "\n... [truncated]"
        return f"{self.summary}\n\n{self.tree}\n\n{content}"


class GitHubSourceError(RuntimeError):
    """Raised on clone/fetch failure — Research Agent catches this
    specifically (docs/standards.md section 8) rather than crashing."""


async def fetch_repo_digest(source_url: str) -> RepoDigest:
    # Async on purpose: gitingest.ingest() (sync) internally calls
    # asyncio.run(), which breaks when called from inside an already-
    # running event loop — and every Agent.run() IS one (core.schemas.
    # agent.Agent.run is async). Use gitingest.ingest_async() directly
    # and await it instead. Found this the hard way while wiring this
    # into the Research Agent — worth remembering for any other
    # sync-wrapping-async library adopted later.
    try:
        from gitingest import ingest_async
    except ImportError as exc:  # pragma: no cover - dependency issue, not runtime
        raise GitHubSourceError("gitingest is not installed") from exc

    try:
        summary, tree, content = await ingest_async(source_url)
    except Exception as exc:  # noqa: BLE001 — re-raised as our own type
        raise GitHubSourceError(f"failed to fetch repo digest for {source_url}: {exc}") from exc

    return RepoDigest(source_url=source_url, summary=summary, tree=tree, content=content)
