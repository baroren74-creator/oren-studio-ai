"""GitHub Trending -> a list of candidate repos.

docs/roadmap.md Phase 2.10 (Trend Agent v1): GitHub Trending first, as
the cheapest/free source (docs/architecture.md risk #8 — start with
free sources, defer paid/rate-limited ones like Twitter/X). GitHub has
no official "trending" API, so this scrapes https://github.com/trending
directly with BeautifulSoup — deliberately not one of the several
unofficial "GitHub Trending API" wrapper packages on PyPI, since those
are themselves unofficial scrapers of the same page, one more layer of
indirection (and one more thing that can go stale) for no real benefit.
github.com is on this project's sandbox network allowlist, unlike most
other domains (see agents/research_agent/youtube_source.py's docstring
for the contrast with youtube.com), which made this the easiest source
to verify live during development.
"""

from __future__ import annotations

from dataclasses import dataclass

TRENDING_URL = "https://github.com/trending"


@dataclass
class TrendingRepo:
    full_name: str  # "owner/repo"
    url: str
    description: str | None
    language: str | None
    stars_total: int | None
    stars_today: int | None


class TrendSourceError(RuntimeError):
    """Raised on fetch/parse failure — Trend Agent catches this
    specifically (docs/standards.md section 8), same pattern as
    GitHubSourceError/YouTubeSourceError."""


def _parse_int(text: str | None) -> int | None:
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def _parse_trending_html(html: str) -> list[TrendingRepo]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    repos: list[TrendingRepo] = []

    for row in soup.select("article.Box-row"):
        link = row.select_one("h2 a")
        if link is None or not link.get("href"):
            continue  # malformed row — skip rather than fail the whole page

        full_name = link["href"].strip("/")
        desc_el = row.select_one("p")
        lang_el = row.select_one("span[itemprop=programmingLanguage]")
        stars_today_el = row.select_one("span.d-inline-block.float-sm-right")
        star_links = row.select("a.Link--muted")

        repos.append(
            TrendingRepo(
                full_name=full_name,
                url=f"https://github.com/{full_name}",
                description=desc_el.get_text(strip=True) if desc_el else None,
                language=lang_el.get_text(strip=True) if lang_el else None,
                stars_total=_parse_int(star_links[0].get_text()) if star_links else None,
                stars_today=_parse_int(stars_today_el.get_text()) if stars_today_el else None,
            )
        )

    return repos


def fetch_trending_repos(*, language: str | None = None, since: str = "daily") -> list[TrendingRepo]:
    """`since` matches GitHub's own query param (`daily`/`weekly`/`monthly`)."""
    import httpx

    url = f"{TRENDING_URL}/{language}" if language else TRENDING_URL

    try:
        response = httpx.get(
            url,
            params={"since": since},
            headers={"User-Agent": "Mozilla/5.0 (compatible; OrenStudioAI/1.0)"},
            timeout=15.0,
            follow_redirects=True,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise TrendSourceError(f"failed to fetch GitHub Trending ({url}): {exc}") from exc

    try:
        repos = _parse_trending_html(response.text)
    except Exception as exc:  # noqa: BLE001 — re-raised as our own type
        raise TrendSourceError(f"failed to parse GitHub Trending page ({url}): {exc}") from exc

    if not repos:
        # Not necessarily an error (a very narrow language filter could
        # legitimately be empty) but worth surfacing distinctly from a
        # network/parse failure — callers decide how to treat it.
        raise TrendSourceError(f"no repos found on GitHub Trending ({url}) — page structure may have changed")

    return repos
