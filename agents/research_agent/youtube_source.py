"""YouTube video -> LLM-ready transcript.

docs/roadmap.md Phase 2.5 originally specced this as "YouTube URL ->
transcript (faster-whisper) -> summary" — downloading audio and running
a local Whisper model. Revised during implementation (Oren approved the
switch, docs/decisions.md ADR-013): YouTube already serves a transcript
(human-written or auto-generated captions) for the overwhelming majority
of videos worth summarizing, retrievable directly via YouTube's own
timedtext API — no audio download, no local STT model, no GPU. This
module uses `youtube-transcript-api` (MIT) for that. faster-whisper
remains the documented fallback for the rare video with no transcript
available at all (not implemented here — see ADR-013's Consequences).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class VideoTranscript:
    source_url: str
    video_id: str
    language_code: str
    is_generated: bool
    text: str

    def as_prompt_text(self, max_chars: int = 12_000) -> str:
        """Truncate defensively — same reasoning as RepoDigest.as_prompt_text
        (agents/research_agent/github_source.py): a long video's transcript
        can exceed any prompt budget, and idea_scoring_node needs a
        summary before anything more expensive runs (ADR-003)."""
        text = self.text
        if len(text) > max_chars:
            text = text[:max_chars] + "\n... [truncated]"
        return text


class YouTubeSourceError(RuntimeError):
    """Raised on URL-parsing or transcript-fetch failure — Research Agent
    catches this specifically (docs/standards.md section 8), same
    pattern as GitHubSourceError."""


# Covers the common URL shapes: watch?v=, youtu.be/, /shorts/, /embed/.
# YouTube video IDs are always exactly 11 characters from
# [A-Za-z0-9_-] — this doesn't need to be a full RFC-grade URL parser.
_VIDEO_ID_PATTERN = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{11})")


def extract_video_id(source_url: str) -> str:
    match = _VIDEO_ID_PATTERN.search(source_url)
    if not match:
        raise YouTubeSourceError(f"could not extract a YouTube video ID from URL: {source_url}")
    return match.group(1)


def fetch_video_transcript(source_url: str) -> VideoTranscript:
    from youtube_transcript_api import YouTubeTranscriptApi, YouTubeTranscriptApiException

    video_id = extract_video_id(source_url)

    try:
        fetched = YouTubeTranscriptApi().fetch(video_id)
    except YouTubeTranscriptApiException as exc:
        # Covers TranscriptsDisabled, NoTranscriptFound, VideoUnavailable,
        # IpBlocked, AgeRestricted, etc. — every library-specific failure
        # shares this base (docs/standards.md section 8: catch the
        # specific thing, not a bare Exception).
        raise YouTubeSourceError(f"failed to fetch transcript for {source_url}: {exc}") from exc

    text = " ".join(snippet.text for snippet in fetched.snippets).strip()
    if not text:
        raise YouTubeSourceError(f"transcript for {source_url} was empty")

    return VideoTranscript(
        source_url=source_url,
        video_id=video_id,
        language_code=fetched.language_code,
        is_generated=fetched.is_generated,
        text=text,
    )
