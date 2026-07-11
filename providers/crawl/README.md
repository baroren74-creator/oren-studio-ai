# providers/crawl

Crawl4AI (default, self-hosted, Apache-2.0, free) for straightforward
article/doc extraction; Firecrawl (self-hosted) as the fallback for
JS-heavy/anti-bot sites Crawl4AI struggles with. Browser Use + Playwright
(in `providers/llm`-adjacent agent code, not here) handle interactive
cases needing login/JS execution. See `docs/open-source-landscape.md`
section 6.
