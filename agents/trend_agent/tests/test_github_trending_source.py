"""agents/trend_agent/github_trending_source.py — docs/roadmap.md Phase
2.10 (Trend Agent v1).

`_parse_trending_html` is tested against a hand-written minimal HTML
fixture (below) that mirrors github.com/trending's real structure
(verified by fetching the live page during development — see
test_fetch_trending_repos_live, the one test in this file allowed to
touch the network) rather than a full scraped-page dump, which would be
mostly irrelevant markup (sponsor buttons, SVG icons) and more fragile
to real-world noise than a deliberately minimal fixture.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from agents.trend_agent.github_trending_source import (
    TrendSourceError,
    _parse_trending_html,
    fetch_trending_repos,
)

# Two rows: one with every field present, one missing description/
# language/stars-today — real trending pages do have rows like the
# second (a repo with no language detected, or one that's been
# trending long enough that "stars today" isn't shown for it).
FIXTURE_HTML = """
<html><body>
<div class="Box">
  <article class="Box-row">
    <h2 class="h3 lh-condensed">
      <a href="/octocat/Hello-World">
        octocat /
        <span>Hello-World</span>
      </a>
    </h2>
    <p class="col-9 color-fg-muted my-1 pr-4">
      My first repository on GitHub!
    </p>
    <span itemprop="programmingLanguage">Python</span>
    <a href="/octocat/Hello-World/stargazers" class="Link--muted">1,234</a>
    <a href="/octocat/Hello-World/forks" class="Link--muted">56</a>
    <span class="d-inline-block float-sm-right">78 stars today</span>
  </article>
  <article class="Box-row">
    <h2 class="h3 lh-condensed">
      <a href="/someone/no-frills-repo">
        someone /
        <span>no-frills-repo</span>
      </a>
    </h2>
    <a href="/someone/no-frills-repo/stargazers" class="Link--muted">42</a>
    <a href="/someone/no-frills-repo/forks" class="Link--muted">3</a>
  </article>
</div>
</body></html>
"""


def test_parse_trending_html_extracts_full_row():
    repos = _parse_trending_html(FIXTURE_HTML)

    assert len(repos) == 2
    first = repos[0]
    assert first.full_name == "octocat/Hello-World"
    assert first.url == "https://github.com/octocat/Hello-World"
    assert first.description == "My first repository on GitHub!"
    assert first.language == "Python"
    assert first.stars_total == 1234
    assert first.stars_today == 78


def test_parse_trending_html_handles_missing_optional_fields():
    repos = _parse_trending_html(FIXTURE_HTML)

    second = repos[1]
    assert second.full_name == "someone/no-frills-repo"
    assert second.description is None
    assert second.language is None
    assert second.stars_today is None
    assert second.stars_total == 42  # stars total is always present, unlike the others


def test_parse_trending_html_returns_empty_list_for_no_rows():
    # _parse_trending_html itself is lenient (empty list, not an error) —
    # fetch_trending_repos is what decides an empty result is worth
    # raising over, see the next test.
    assert _parse_trending_html("<html><body>nothing here</body></html>") == []


def test_fetch_trending_repos_raises_when_page_has_no_rows():
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.text = "<html><body>nothing here</body></html>"

    with patch("httpx.get", return_value=fake_response):
        with pytest.raises(TrendSourceError, match="no repos found"):
            fetch_trending_repos()


def test_fetch_trending_repos_wraps_http_error():
    with patch("httpx.get", side_effect=httpx.ConnectTimeout("timed out")):
        with pytest.raises(TrendSourceError, match="failed to fetch GitHub Trending"):
            fetch_trending_repos()


def test_fetch_trending_repos_wraps_non_2xx_status():
    fake_response = MagicMock()
    fake_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=MagicMock(status_code=500)
    )
    with patch("httpx.get", return_value=fake_response):
        with pytest.raises(TrendSourceError, match="failed to fetch GitHub Trending"):
            fetch_trending_repos()


def test_fetch_trending_repos_parses_mocked_response_body():
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None
    fake_response.text = FIXTURE_HTML

    with patch("httpx.get", return_value=fake_response) as mock_get:
        repos = fetch_trending_repos(language="python", since="weekly")

    call_kwargs = mock_get.call_args.kwargs
    assert call_kwargs["params"] == {"since": "weekly"}
    assert mock_get.call_args.args[0] == "https://github.com/trending/python"
    assert len(repos) == 2


@pytest.mark.integration
def test_fetch_trending_repos_live():
    """The one test in this file allowed to touch the network —
    github.com is reachable from this sandbox (unlike most domains, see
    agents/research_agent/youtube_source.py's docstring for the
    contrast). Confirms the real page still matches the structure
    _parse_trending_html expects, i.e. GitHub hasn't changed their
    markup since this was written."""
    repos = fetch_trending_repos()

    assert len(repos) > 0
    assert all("/" in r.full_name for r in repos)
    assert all(r.url.startswith("https://github.com/") for r in repos)
