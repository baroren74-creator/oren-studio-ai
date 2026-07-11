"""Research Agent test suite — docs/roadmap.md Phase 2.3 / 2.3.1.

Covers the three real code paths in agents/research_agent/agent.py:
1. source_type != "github" -> status="skipped" (Phase 2.4+ not implemented yet)
2. missing source_url -> status="failed", clean validation error
3. source_type == "github" -> real happy path, real LLM-failure path

For (3) we deliberately mock both fetch_repo_digest and complete rather
than hitting the network / a real LLM key:
- gitingest network calls are slow and flaky to depend on in a test suite
  that should run in CI without secrets or GitHub access.
- No real ANTHROPIC_API_KEY exists in CI or this sandbox (see
  providers/llm/llm_provider/client.py) — Oren adds his own key to his
  local .env when he's ready to actually run the app (docs/decisions.md
  ADR-006 area; consistent with the "just the code, don't run now" choice
  made for Phase 1).

A separate, explicitly-marked integration test (test_github_source_live)
exercises the real gitingest.ingest_async() call against a small public
repo, so the "does the async fix actually work end-to-end" question has
one real answer on record — but it's skippable/network-dependent and not
part of the default fast suite.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

# Registers every stub/real agent (side-effect import), same pattern as
# apps/api/tests/test_smoke_e2e.py.
import agents.research_agent.agent as ra_module
from agents.research_agent.github_source import GitHubSourceError, RepoDigest
from core.schemas.agent import AgentInput
from llm_provider import LLMError, LLMResponse

AGENT = ra_module.agent


def _input(payload: dict) -> AgentInput:
    return AgentInput(run_id=uuid.uuid4(), project_id=uuid.uuid4(), payload=payload)


# ---------------------------------------------------------------------
# 1. source_type routing
# ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_github_source_type_is_skipped_not_crashed():
    out = await AGENT.run(_input({"source_type": "youtube", "source_url": "https://youtube.com/watch?v=x"}))

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
async def test_github_llm_failure_is_caught_and_still_returns_digest_summary():
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
    assert out.result["digest_summary"] == FAKE_DIGEST.summary


# ---------------------------------------------------------------------
# 3. key-point parsing (pure function, no mocking needed)
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
# 4. optional live integration check (network + real gitingest, no LLM key
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
