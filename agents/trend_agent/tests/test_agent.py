"""agents/trend_agent/agent.py — docs/roadmap.md Phase 2.10 (Trend Agent
v1: GitHub Trending)."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

import agents.trend_agent.agent as trend_module
from agents.trend_agent.github_trending_source import TrendingRepo, TrendSourceError
from core.schemas.agent import AgentInput

AGENT = trend_module.agent

FAKE_REPOS = [
    TrendingRepo(
        full_name="octocat/Hello-World",
        url="https://github.com/octocat/Hello-World",
        description="My first repository on GitHub!",
        language="Python",
        stars_total=1234,
        stars_today=78,
    ),
    TrendingRepo(
        full_name="someone/no-frills-repo",
        url="https://github.com/someone/no-frills-repo",
        description=None,
        language=None,
        stars_total=42,
        stars_today=None,
    ),
]


def _input(payload: dict | None = None) -> AgentInput:
    # project_id/run_id are required by the Agent contract but not
    # meaningfully used by Trend Agent (see agent.py's module docstring)
    # — any UUID satisfies the schema.
    return AgentInput(run_id=uuid.uuid4(), project_id=uuid.uuid4(), payload=payload or {})


@pytest.mark.asyncio
async def test_run_returns_ideas_from_trending_repos():
    with patch.object(trend_module, "fetch_trending_repos", return_value=FAKE_REPOS) as mock_fetch:
        out = await AGENT.run(_input())

    mock_fetch.assert_called_once_with(language=None, since="daily")

    assert out.status == "success"
    assert out.next_event == "trend.discovered"
    assert out.result["source"] == "github_trending"
    assert len(out.result["ideas"]) == 2

    first = out.result["ideas"][0]
    assert first["title"] == "octocat/Hello-World"
    assert first["source_type"] == "github"
    assert first["source_url"] == "https://github.com/octocat/Hello-World"
    assert first["tags"] == ["Python"]
    assert first["stars_today"] == 78

    second = out.result["ideas"][1]
    assert second["tags"] == []  # no language -> empty tags, not [None]
    assert second["description"] is None


@pytest.mark.asyncio
async def test_run_passes_language_and_since_filters_through():
    with patch.object(trend_module, "fetch_trending_repos", return_value=FAKE_REPOS) as mock_fetch:
        await AGENT.run(_input({"language": "python", "since": "weekly"}))

    mock_fetch.assert_called_once_with(language="python", since="weekly")


@pytest.mark.asyncio
async def test_run_catches_source_error_cleanly():
    with patch.object(trend_module, "fetch_trending_repos", side_effect=TrendSourceError("network unreachable")):
        out = await AGENT.run(_input())

    assert out.status == "failed"
    assert "network unreachable" in out.result["reason"]
    assert out.next_event is None


@pytest.mark.asyncio
async def test_run_caps_ideas_at_max_ideas():
    many_repos = [
        TrendingRepo(full_name=f"org/repo-{i}", url=f"https://github.com/org/repo-{i}", description=None, language=None, stars_total=1, stars_today=1)
        for i in range(50)
    ]
    with patch.object(trend_module, "fetch_trending_repos", return_value=many_repos):
        out = await AGENT.run(_input())

    assert len(out.result["ideas"]) == trend_module.MAX_IDEAS
