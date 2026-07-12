"""agents/research_agent/youtube_source.py — docs/roadmap.md Phase 2.5,
docs/decisions.md ADR-013.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agents.research_agent.youtube_source import (
    YouTubeSourceError,
    extract_video_id,
    fetch_video_transcript,
)


@pytest.mark.parametrize(
    "url,expected_id",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/watch?v=dQw4w9WgXcQ&t=30s", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ],
)
def test_extract_video_id_handles_common_url_shapes(url, expected_id):
    assert extract_video_id(url) == expected_id


def test_extract_video_id_rejects_url_without_a_video_id():
    with pytest.raises(YouTubeSourceError, match="could not extract"):
        extract_video_id("https://www.youtube.com/channel/UCxxxxx")


def _fake_snippet(text: str) -> MagicMock:
    snippet = MagicMock()
    snippet.text = text
    return snippet


def test_fetch_video_transcript_joins_snippets_and_returns_metadata():
    fetched = MagicMock()
    fetched.snippets = [_fake_snippet("Hello and"), _fake_snippet("welcome back.")]
    fetched.language_code = "en"
    fetched.is_generated = True

    with patch("youtube_transcript_api.YouTubeTranscriptApi.fetch", return_value=fetched):
        transcript = fetch_video_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    assert transcript.video_id == "dQw4w9WgXcQ"
    assert transcript.language_code == "en"
    assert transcript.is_generated is True
    assert transcript.text == "Hello and welcome back."


def test_fetch_video_transcript_wraps_library_exception():
    from youtube_transcript_api import TranscriptsDisabled

    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi.fetch",
        side_effect=TranscriptsDisabled("dQw4w9WgXcQ"),
    ):
        with pytest.raises(YouTubeSourceError, match="failed to fetch transcript"):
            fetch_video_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_fetch_video_transcript_rejects_empty_transcript():
    fetched = MagicMock()
    fetched.snippets = [_fake_snippet("   ")]
    fetched.language_code = "en"
    fetched.is_generated = True

    with patch("youtube_transcript_api.YouTubeTranscriptApi.fetch", return_value=fetched):
        with pytest.raises(YouTubeSourceError, match="empty"):
            fetch_video_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_as_prompt_text_truncates_long_transcripts():
    from agents.research_agent.youtube_source import VideoTranscript

    long_transcript = VideoTranscript(
        source_url="https://youtu.be/x",
        video_id="x",
        language_code="en",
        is_generated=False,
        text="word " * 5000,
    )
    prompt_text = long_transcript.as_prompt_text(max_chars=100)
    assert len(prompt_text) <= 100 + len("\n... [truncated]")
    assert prompt_text.endswith("[truncated]")
