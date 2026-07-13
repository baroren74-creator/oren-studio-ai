"""Research Agent test suite — docs/roadmap.md Phase 2.3 / 2.3.1 / 2.5.

Covers the real code paths in agents/research_agent/agent.py:
1. source_type not in SUPPORTED_SOURCE_TYPES -> status="skipped"
2. missing source_url -> status="failed", clean validation error
3. source_type == "github" -> real happy path, real fetch/LLM-failure paths
4. source_type == "youtube" -> real happy path, real fetch/LLM-failure paths
   (Phase 2.5, ADR-013 — youtube-transcript-api, not faster-whisper)

For (3)/(4) we deliberately mock the source fetch + complete rather than
hitting the network / a real LLM key:
- gitingest/youtube-transcript-api network calls are slow and flaky to
  depend on in a test suite that should run in CI without secrets or
  external access.
- No real ANTHROPIC_API_KEY exists in CI or this sandbox (see
  providers/llm/llm_provider/client.py) — Oren adds his own key to his
  local .env when he's ready to actually run the app (docs/decisions.md
  ADR-006 area; consistent with the "just the code, don't run now" choice
  made for Phase 1).

A separate, explicitly-marked integration test (test_github_source_live)
exercises the real gitingest.ingest_async() call against a small public
repo, so the "does the async fix actually work end-to-end" question has
one real answer on record — but it's skippable/network-dependent and not
part of the default fast suite. No YouTube equivalent exists: this
sandbox's network allowlist doesn't include youtube.com at all (unlike
github.com), so there's no way to verify youtube_source.py against a
real video from here — see agents/research_agent/youtube_source.py's
docstring.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

# Registers every stub/real agent (side-effect import), same pattern as
# apps/api/tests/test_smoke_e2e.py.
import agents.research_agent.agent as ra_module
from agents.research_agent.github_source import GitHubSourceError, RepoDigest
from agents.research_agent.youtube_source import VideoTranscript, YouTubeSourceError
from core.schemas.agent import AgentInput
from llm_provider import LLMError, LLMResponse

AGENT = ra_module.agent


def _input(payload: dict) -> AgentInput:
    return AgentInput(run_id=uuid.uuid4(), project_id=uuid.uuid4(), payload=payload)


# ---------------------------------------------------------------------
# 1. source_type routing
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsupported_source_type_is_skipped_not_crashed():
    out = await AGENT.run(_input({"source_type": "article", "source_url": "https://example.com/post"}))

    assert out.status == "skipped"
    assert "not implemented yet" in out.result["reason"]
    assert out.next_event is None


@pytest.mark.asyncio
async def test_missing_source_url_fails_cleanly():
    out = await AGENT.run(_input({"source_type": "github"}))

    assert out.status == "failed"
    assert "source_url" in out.result["reason"]


# ---------------------------------------------------------------------
# 2. github happy path (fetch_repo_digest + complete both mocked)
# ---------------------------------------------------------------------


FAKE_DIGEST = RepoDigest(
    source_url="https://github.com/octocat/Hello-World",
    summary="Repository: octocat/hello-world\nFiles analyzed: 1\n",
    tree="└── octocat-hello-world/\n    └── README\n",
    content="FILE: README\nHello World!\n",
)

FAKE_LLM_TEXT = (
    "This repo is the canonical GitHub \"Hello World\" example, used to teach "
    "the basics of forking and pull requests.\n"
    "- Single README file\n"
    "- Created by GitHub for onboarding new users\n"
    "- Frequently the very first repo a developer ever forks"
)


@pytest.mark.asyncio
async def test_github_happy_path_returns_parsed_summary_and_key_points():
    fake_response = LLMResponse(
        text=FAKE_LLM_TEXT,
        model="anthropic/claude-3-5-sonnet-20241022",
        input_tokens=120,
        output_tokens=60,
        cost_usd=0.0021,
    )

    with (
        patch.object(ra_module, "fetch_repo_digest", new=AsyncMock(return_value=FAKE_DIGEST)) as mock_fetch,
        patch.object(ra_module, "complete", return_value=fake_response) as mock_complete,
    ):
        out = await AGENT.run(
            _input({"source_type": "github", "source_url": "https://github.com/octocat/Hello-World"})
        )

    mock_fetch.assert_awaited_once_with("https://github.com/octocat/Hello-World")
    mock_complete.assert_called_once()

    assert out.status == "success"
    assert out.next_event == "research.completed"
    assert out.result["source_url"] == "https://github.com/octocat/Hello-World"
    assert out.result["repo_summary"] == FAKE_DIGEST.summary
    assert out.result["raw_text"] == FAKE_DIGEST.as_prompt_text()
    assert "Hello World" in out.result["summary"]
    assert len(out.result["key_points"]) == 3
    assert out.result["key_points"][0] == "Single README file"

    # cost accounting must round-trip from LLMResponse -> CostInfo
    assert out.cost.tokens_used == 180
    assert out.cost.cost_usd == pytest.approx(0.0021)
    assert out.cost.provider == "anthropic/claude-3-5-sonnet-20241022"


@pytest.mark.asyncio
async def test_github_source_fetch_failure_is_caught_not_raised():
    with patch.object(
        ra_module,
        "fetch_repo_digest",
        new=AsyncMock(side_effect=GitHubSourceError("failed to fetch repo digest for bad-url: 404")),
    ):
        out = await AGENT.run(_input({"source_type": "github", "source_url": "https://github.com/nope/nope"}))

    assert out.status == "failed"
    assert "404" in out.result["reason"]


@pytest.mark.asyncio
async def test_github_llm_failure_is_caught_and_still_returns_repo_summary():
    """This is the exact case verified manually against the real gitingest
    fetch during Phase 2.3 development: gitingest succeeds, the LLM call
    fails (no API key in this environment), and the agent must fail
    cleanly while still surfacing what it *did* manage to fetch."""
    with (
        patch.object(ra_module, "fetch_repo_digest", new=AsyncMock(return_value=FAKE_DIGEST)),
        patch.object(ra_module, "complete", side_effect=LLMError("Missing Anthropic API Key")),
    ):
        out = await AGENT.run(
            _input({"source_type": "github", "source_url": "https://github.com/octocat/Hello-World"})
        )

    assert out.status == "failed"
    assert "Missing Anthropic API Key" in out.result["reason"]
    # proves the failure happened AFTER a successful fetch, not instead of one
    assert out.result["repo_summary"] == FAKE_DIGEST.summary


# ---------------------------------------------------------------------
# 3. youtube happy path (fetch_video_transcript + complete both mocked)
# ---------------------------------------------------------------------


FAKE_TRANSCRIPT = VideoTranscript(
    source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    video_id="dQw4w9WgXcQ",
    language_code="en",
    is_generated=True,
    text="In this video we walk through building a small CLI tool from scratch.",
)

FAKE_YOUTUBE_LLM_TEXT = (
    "The video is a walkthrough of building a small command-line tool from "
    "scratch, aimed at viewers new to CLI development.\n"
    "- Step-by-step CLI build\n"
    "- Beginner-friendly framing\n"
    "- Good candidate for a short recap video"
)


@pytest.mark.asyncio
async def test_youtube_happy_path_returns_parsed_summary_and_key_points():
    fake_response = LLMResponse(
        text=FAKE_YOUTUBE_LLM_TEXT,
        model="anthropic/claude-3-5-sonnet-20241022",
        input_tokens=90,
        output_tokens=40,
        cost_usd=0.0015,
    )

    with (
        patch.object(ra_module, "fetch_video_transcript", return_value=FAKE_TRANSCRIPT) as mock_fetch,
        patch.object(ra_module, "complete", return_value=fake_response) as mock_complete,
    ):
        out = await AGENT.run(
            _input({"source_type": "youtube", "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
        )

    mock_fetch.assert_called_once_with("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    mock_complete.assert_called_once()

    assert out.status == "success"
    assert out.next_event == "research.completed"
    assert out.result["source_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert out.result["video_id"] == "dQw4w9WgXcQ"
    assert out.result["transcript_language"] == "en"
    assert out.result["transcript_is_generated"] is True
    assert out.result["raw_text"] == FAKE_TRANSCRIPT.as_prompt_text()
    assert "command-line tool" in out.result["summary"]
    assert len(out.result["key_points"]) == 3

    assert out.cost.tokens_used == 130
    assert out.cost.cost_usd == pytest.approx(0.0015)


@pytest.mark.asyncio
async def test_youtube_source_fetch_failure_is_caught_not_raised():
    with patch.object(
        ra_module,
        "fetch_video_transcript",
        side_effect=YouTubeSourceError("failed to fetch transcript for bad-url: transcripts disabled"),
    ):
        out = await AGENT.run(_input({"source_type": "youtube", "source_url": "https://youtu.be/nope"}))

    assert out.status == "failed"
    assert "transcripts disabled" in out.result["reason"]


@pytest.mark.asyncio
async def test_youtube_llm_failure_is_caught_and_still_returns_video_id():
    with (
        patch.object(ra_module, "fetch_video_transcript", return_value=FAKE_TRANSCRIPT),
        patch.object(ra_module, "complete", side_effect=LLMError("Missing Anthropic API Key")),
    ):
        out = await AGENT.run(
            _input({"source_type": "youtube", "source_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
        )

    assert out.status == "failed"
    assert "Missing Anthropic API Key" in out.result["reason"]
    assert out.result["video_id"] == "dQw4w9WgXcQ"


# ---------------------------------------------------------------------
# 4. key-point parsing (pure function, no mocking needed)
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected_summary_contains,expected_points",
    [
        (
            "A short summary line.\n- point one\n- point two",
            "A short summary line.",
            ["point one", "point two"],
        ),
        (
            "Multi-sentence summary.\nStill summary.\n* bullet a\n* bullet b\n* bullet c",
            "Multi-sentence summary. Still summary.",
            ["bullet a", "bullet b", "bullet c"],
        ),
        (
            "No bullets at all, just prose.",
            "No bullets at all, just prose.",
            [],
        ),
    ],
)
def test_parse_key_points(text, expected_summary_contains, expected_points):
    summary, points = ra_module._parse_key_points(text)

    assert expected_summary_contains in summary
    assert points == expected_points


# ---------------------------------------------------------------------
# 5. optional live integration check (network + real gitingest, no LLM key
#    needed) — proves the asyncio.run()-inside-a-running-loop fix
#    (docs/decisions.md, github_source.py comment) actually works against
#    the real library, not just mocks. Skipped by default; run explicitly
#    with: pytest -m integration
# ---------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.asyncio
async def test_github_source_live_fetch_does_not_raise_asyncio_error():
    from agents.research_agent.github_source import fetch_repo_digest

    digest = await fetch_repo_digest("https://github.com/octocat/Hello-World")

    assert "hello-world" in digest.summary.lower()


# ---------------------------------------------------------------------
# 6. manual-text source types (reel/post/tweet) — Phase 3.9. No fetch at
#    all here (see this module's docstring for why Instagram scraping
#    isn't a real Agent's job) — only `complete` needs mocking.
# ---------------------------------------------------------------------


FAKE_REEL_LLM_TEXT = (
    "The post shows a quick before/after of a home-cooked recipe, framed "
    "as a fast weeknight dinner idea.\n"
    "- Under 20 minutes total\n"
    "- Uses 5 common ingredients\n"
    "- Strong hook in the first 2 seconds"
)


@pytest.mark.asyncio
async def test_manual_text_happy_path_returns_parsed_summary_and_key_points():
    fake_response = LLMResponse(
        text=FAKE_REEL_LLM_TEXT,
        model="anthropic/claude-3-5-sonnet-20241022",
        input_tokens=70,
        output_tokens=35,
        cost_usd=0.0012,
    )

    with patch.object(ra_module, "complete", return_value=fake_response) as mock_complete:
        out = await AGENT.run(
            _input(
                {
                    "source_type": "reel",
                    "source_url": "https://www.instagram.com/reel/ABC123/",
                    "source_text": "20 minute dinner using 5 ingredients you already have #cooking",
                }
            )
        )

    mock_complete.assert_called_once()

    assert out.status == "success"
    assert out.next_event == "research.completed"
    assert out.result["source_url"] == "https://www.instagram.com/reel/ABC123/"
    assert out.result["raw_text"] == "20 minute dinner using 5 ingredients you already have #cooking"
    assert "recipe" in out.result["summary"]
    assert len(out.result["key_points"]) == 3


@pytest.mark.asyncio
async def test_manual_text_works_for_post_and_tweet_too():
    fake_response = LLMResponse(text="A short post.", model="m", input_tokens=10, output_tokens=5, cost_usd=0.0)
    with patch.object(ra_module, "complete", return_value=fake_response):
        for source_type in ("post", "tweet"):
            out = await AGENT.run(
                _input({"source_type": source_type, "source_url": "https://example.com/x", "source_text": "hello"})
            )
            assert out.status == "success"


@pytest.mark.asyncio
async def test_manual_text_rejects_missing_source_text():
    out = await AGENT.run(_input({"source_type": "reel", "source_url": "https://www.instagram.com/reel/ABC123/"}))

    assert out.status == "failed"
    assert "source_text" in out.result["reason"]


@pytest.mark.asyncio
async def test_manual_text_rejects_blank_source_text():
    out = await AGENT.run(
        _input(
            {
                "source_type": "reel",
                "source_url": "https://www.instagram.com/reel/ABC123/",
                "source_text": "   ",
            }
        )
    )

    assert out.status == "failed"
    assert "source_text" in out.result["reason"]


@pytest.mark.asyncio
async def test_manual_text_does_not_require_source_url():
    # source_url is a reference link, never dereferenced for manual-text
    # types — a run with no link at all still has something to work
    # with as long as source_text is present.
    fake_response = LLMResponse(text="A short post.", model="m", input_tokens=10, output_tokens=5, cost_usd=0.0)
    with patch.object(ra_module, "complete", return_value=fake_response):
        out = await AGENT.run(_input({"source_type": "reel", "source_text": "hello"}))

    assert out.status == "success"
    assert out.result["source_url"] is None


@pytest.mark.asyncio
async def test_manual_text_llm_failure_is_caught_not_raised():
    with patch.object(ra_module, "complete", side_effect=LLMError("Missing Anthropic API Key")):
        out = await AGENT.run(
            _input(
                {
                    "source_type": "reel",
                    "source_url": "https://www.instagram.com/reel/ABC123/",
                    "source_text": "hello",
                }
            )
        )

    assert out.status == "failed"
    assert "Missing Anthropic API Key" in out.result["reason"]
