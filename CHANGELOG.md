# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added — Phase 3.1: style_profile v0 (manual questionnaire)
- `apps/api/app/models.py`: new `StyleProfile` (table `style_profile`,
  matching docs/database.md). `opening_patterns`/`closing_patterns`
  stored as JSON lists rather than Postgres `TEXT[]` — same engine-
  agnostic simplification `ResearchNote.key_points` already uses.
  Migration: `alembic/versions/c3a9f1d8e2b4_add_style_profile_table.py`.
- `apps/api/app/services/style_profile.py`: `create_style_profile()`
  (always inserts at `max(version) + 1` — versioned, not updated in
  place) and `get_current_style_profile()` (highest version).
- `apps/api/app/routers/style_profile.py`: `POST /api/style-profile`
  (create) and `GET /api/style-profile/current` (404 if none exists) —
  the GET was already in docs/api.md's route list; POST is a symmetric
  addition documented alongside it.
- `scripts/seed_style_profile.py`: seeds the actual v0 row from Oren's
  answers, collected in chat (tone: energetic/fast + professional/
  precise + friendly/conversational, not one register; 30-45s videos;
  two opening patterns, two closing patterns, both in Hebrew). Not yet
  run against a real Postgres instance (none live from this sandbox) —
  verified end-to-end against a throwaway SQLite DB instead, including
  correct Hebrew round-tripping through JSON storage.
- Tests: `apps/api/tests/test_style_profile.py` (9 cases — versioning,
  current-lookup, both routes, 404, auth). Full suite: 24/24 passing in
  `apps/api`.

### Added — Phase 2.8/2.9: Knowledge Agent (chunk/embed/index + semantic search)
- `packages/memory` (new package, ADR-002's "~300-line custom layer, not
  LlamaIndex/Haystack"): `chunking.py`'s `chunk_text()` (word-count
  chunks with overlap, no tokenizer dependency) and `store.py`'s
  `MemoryStore` (thin `qdrant-client` wrapper — `path=` for embedded
  local mode, `url=`/`api_key=` for a real server; `upsert_document()`,
  `search()`, `delete_source()`; new `MemoryStoreError` for qdrant-layer
  failures, kept separate from `LLMError`, which still surfaces directly
  from embedding failures).
- `providers/llm/llm_provider/client.py`: new `embed()` +
  `EmbeddingResponse`, routed through LiteLLM to Voyage AI
  (`voyage/voyage-3-lite` default, `OREN_STUDIO_EMBEDDING_MODEL`
  override) — Oren-approved choice, no prior doc specified an embedding
  provider.
- `agents/research_agent/agent.py`: result now includes `raw_text` (the
  full digest/transcript, not just the LLM summary) for both GitHub and
  YouTube paths — this is what Knowledge Agent indexes. Bumped to 0.4.0.
- `agents/knowledge_agent/agent.py`: real logic replacing the Phase 1.18
  stub — chunks + embeds + upserts `payload.text` into `knowledge_docs`,
  emits `source.ingested`; skips cleanly (no event) when there's nothing
  to index, same convention as Research Agent's unsupported-source-type
  path.
- `workflows/graph.py`: new `StudioState.research_raw_text` field;
  `knowledge_node` now builds a real payload (`source_id`, `text`,
  `project_id`, `source_type`, `source_url`) instead of the empty `{}`
  every Stub Agent got by default — the same class of wiring gap fixed
  for `research_node` back in Phase 2.3 (a Stub Agent ignoring its input
  hides a bug that only surfaces once real logic depends on that input).
  `source_id` is `run_id` for now — no live orchestrator-worker persists
  `sources` rows yet; documented as a pragmatic stand-in in
  `packages/memory/memory/store.py` and `docs/agents.md`.
- `apps/api/app/routers/knowledge.py` + `app/services/knowledge.py`: new
  `GET /api/knowledge/search?q=...&project_id=...&limit=...` (Phase 2.9).
  Returns Qdrant's own payload directly, not yet the full "Qdrant +
  Postgres hydrate" docs/api.md describes (no `sources` rows to hydrate
  from yet); 503 on a down/unreachable store.
- Tests: `packages/memory/tests/` (13, incl. real qdrant-client embedded
  mode with mocked embeddings), `providers/llm/tests/test_client.py` (7,
  first-ever tests for this provider's `complete()` too), `agents/
  knowledge_agent/tests/` (7), `apps/api/tests/test_knowledge_search.py`
  (5), plus new/updated `apps/api/tests/test_smoke_e2e.py` cases proving
  the graph wiring end-to-end and updating the low-score-rejection test's
  expected event list (`source.ingested` no longer fires unconditionally).
- `Makefile`'s `test` target now also runs `agents/knowledge_agent/`,
  `packages/memory/`, and `providers/llm/`.

### Added — Phase 2.10: Trend Agent v1 (GitHub Trending)
- `agents/trend_agent/github_trending_source.py`: `fetch_trending_repos()`
  scrapes `github.com/trending` directly with BeautifulSoup — no official
  GitHub Trending API exists, and github.com is the one external domain
  this project's sandbox network allowlist includes, which made it both
  the pragmatic and the verifiable choice.
- `agents/trend_agent/agent.py`: real logic replacing the Phase 1.18
  stub — returns candidate ideas (title, source_url, description,
  language tag, star counts) from the current trending page, optionally
  filtered by language/since. Unlike every other Agent so far, Trend
  Agent is **not** a `workflows/graph.py` node — it discovers ideas
  independent of any project (see `agent.py`'s module docstring); no
  `ideas` table persistence yet, deferred until the Idea Backlog UI
  (Phase 2.13) exists to shape that schema around.
- `packages/core/core/events/types.py`: added `TREND_DISCOVERED =
  "trend.discovered"`; documented in `docs/api.md`'s Event types list.
- Tests: `agents/trend_agent/tests/` — parser tests against a
  hand-written HTML fixture (deliberately minimal rather than a full
  scraped-page dump), agent-level tests (mocked), plus one
  `@pytest.mark.integration` test that fetches the real trending page
  and checks the parser still matches GitHub's actual markup.
- `Makefile`'s `test` target now also runs `agents/trend_agent/tests/`.

### Added — Phase 2.5: Research Agent v2 (YouTube support)
- `agents/research_agent/youtube_source.py`: `fetch_video_transcript()` —
  fetches YouTube's own captions via `youtube-transcript-api`, not the
  originally-specced faster-whisper (docs/decisions.md ADR-013: no audio
  download, no local STT model, no GPU; also the only option that works
  from this sandbox at all, since its network allowlist doesn't include
  youtube.com or any model-hosting domain).
- `agents/research_agent/agent.py`: `run()` now branches on
  `source_type` (`SUPPORTED_SOURCE_TYPES = ("github", "youtube")`);
  summarization logic extracted into a shared `_summarize()` helper
  rather than duplicated per source type. GitHub's LLM-failure result key
  renamed `digest_summary` → `repo_summary` for consistency with the
  success-path key of the same name (docs/roadmap.md 2.5's note); the
  failure path also now includes `source_url`, which it previously
  didn't.
- Tests: `agents/research_agent/tests/test_youtube_source.py` (URL
  parsing across common link shapes, transcript fetch, error wrapping —
  mocked, no network), `test_agent.py` extended with youtube-path tests
  mirroring the existing github-path ones; the old
  `test_non_github_source_type_is_skipped_not_crashed` (which used
  `source_type="youtube"` to represent "unsupported") renamed/repointed
  to `article` now that youtube is supported.
  `apps/api/tests/test_smoke_e2e.py`'s scoring-gate test updated the
  same way.

### Added — Phase 2.6/2.7: real Idea Scoring rubric + cost gate
- `workflows/idea_scoring.py`: `score_idea()` — a written 4-criterion
  rubric (novelty, audience_relevance, source_reliability,
  visual_potential, each 0-25), LLM judges each criterion independently,
  total is summed in code rather than asked of the LLM directly (ADR-003:
  not a bare freeform prompt). Rubric text documented in `docs/agents.md`
  'Idea scoring rubric'.
- `workflows/graph.py`: `idea_scoring_node` replaced from a hardcoded
  `idea_score=100.0` stub with the real rubric; a project with no
  Research Agent output to score (unsupported source type, fetch/LLM
  failure) is scored 0.0 automatically. `StudioState` gained
  `research_summary`/`research_key_points`/`idea_score_breakdown`;
  `research_node` now forwards the Agent's summary/key_points forward
  through graph state (without clobbering a caller-seeded value when the
  registered Agent is a Stub that doesn't produce one — see
  `research_node`'s comment).
- `apps/api/app/services/research.py`: `update_idea_score()` — fills in
  the existing `research_notes` row's `interest_score`/`scored_by`
  (Phase 2.3's `persist_research_note()` had left these NULL on purpose,
  as noted at the time).
- Tests: `workflows/tests/test_idea_scoring.py` (rubric parsing, clamping,
  error paths — mocked LLM, no network), `apps/api/tests/
  test_research_persistence.py` (score persistence),
  `apps/api/tests/test_smoke_e2e.py` updated: the all-stub pipeline-shape
  test now also mocks `score_idea` (idea_scoring_node isn't Agent-
  Registry-based, so `_all_stub_registry()` alone doesn't cover it) and
  seeds a `research_summary`; `test_rejecting_final_review_does_not_publish`
  now uses a passing mock score so it actually reaches final_review
  (previously it used a YouTube project, which — now correctly — gets
  rejected at the *scoring* gate before ever reaching final_review); new
  `test_low_score_idea_is_rejected_before_final_review` covers that real
  behavior explicitly.
- `Makefile`'s `test` target now also runs `workflows/tests/`.

### Added — Phase 2.1/2.4: LLM provider + Research Agent v1 (real logic)
- `providers/llm/llm_provider/client.py`: LiteLLM-based provider
  abstraction (`complete()`, `LLMMessage`, `LLMResponse`, `LLMError`),
  `<provider>/<model>` naming convention, configurable via
  `OREN_STUDIO_LLM_MODEL`.
- `agents/research_agent/github_source.py`: GitHub repo → LLM-ready
  digest via Gitingest's async `ingest_async()` (its sync wrapper isn't
  safe to call from inside an Agent's own running event loop — found and
  documented while building this).
- `agents/research_agent/agent.py`: real Research Agent v1 — GitHub
  sources only (other types return `status="skipped"`, not a crash);
  fetches a repo digest, summarizes it via the LLM provider, and returns
  a parsed summary + key points.
- `apps/api/app/models.py` + migration `7f805ed657bb`: new
  `research_notes` table (`docs/database.md`); `apps/api/app/services/
  research.py`: `persist_research_note()` writes a row for every
  `status="success"` Research Agent run.
- `workflows/graph.py`: `research_node` now forwards the project's
  `source_type`/`source_url` into the Agent's payload (previously always
  sent `{}` — invisible while every node was a Stub Agent that ignored
  its input); added `_agent_event()` so a `None` next_event
  ("skipped"/"failed" status) no longer leaks into the graph's `events`
  list.
- Tests: `agents/research_agent/tests/` (unit tests + one live-network
  integration test behind `@pytest.mark.integration`),
  `apps/api/tests/test_research_persistence.py`,
  `apps/api/tests/test_smoke_e2e.py` updated — its original "all Stub
  Agents" pipeline-shape test now runs against an isolated stub-only
  `AgentRegistry` (`build_graph(registry=...)`) so it stays network-free
  and immune to future stub→real swaps, plus a new test asserting
  research_node's payload-wiring fix.
- `Makefile`'s `test` target now actually runs both Python test suites
  (was a placeholder).

### Changed — Publishing model (ADR-011)
- Publishing Agent no longer targets an automated publish API for v1 —
  it prepares a final export package + Studio UI preview; Oren uploads
  manually via each platform's own app. Phase 0.5 (platform API
  applications) is deferred, not required for v1.
- `docs/decisions.md`, `docs/roadmap.md`, `docs/agents.md`, `docs/api.md`,
  `agents/publishing_agent/README.md`, `providers/publish/README.md`
  updated accordingly.

### Added — Phase 1: first real code (all tested, not just written)
- `packages/core`: `AgentInput`/`AgentOutput`/`AgentContext` schemas,
  canonical `EventType` enum, config-driven `AgentRegistry`.
- All 8 agents (`agents/*/agent.py`) registered as Stub Agents satisfying
  the Agent contract.
- `workflows/graph.py`: the full LangGraph Orchestrator — research →
  knowledge → idea-scoring gate → script → storyboard → recording →
  video → voice → mandatory approval gate (native `interrupt()`) →
  publish. See `docs/decisions.md` ADR-012 for a LangGraph
  at-least-once-execution gotcha found and documented while building
  this.
- `apps/api`: FastAPI app, SQLAlchemy models + Alembic migration for the
  5 Phase 1 tables, API-key auth, `/api/projects`, `/api/agent-runs`,
  and a WebSocket endpoint — all covered by passing tests.
- `apps/web`: Next.js 16 Studio UI — layout/nav, New Project screen,
  Project timeline view, Ops view (`agent_runs` table); `npm run build`
  passes clean.
- `apps/api/tests/test_smoke_e2e.py`: Phase 1.19's end-to-end smoke
  test — new project → full stub pipeline → mandatory approval gate →
  published (faked) — plus the rejection-path counterpart. Both passing.

### Added — Phase 1: Project Initialization
- Full monorepo skeleton: `docs/`, `apps/`, `packages/`, `services/`,
  `agents/`, `providers/`, `workflows/`, `prompts/`, `scripts/`, `docker/`,
  `.github/`.
- Repository standard files: README, CONTRIBUTING, ARCHITECTURE (pointer),
  ROADMAP (pointer), LICENSE, CODEOWNERS.
- Local dev infra via `docker-compose.yml` (Postgres, Redis, Qdrant, MinIO,
  self-hosted SearXNG) and `Makefile` shortcuts.
- Pre-commit hooks (ruff, prettier, gitleaks) and a CI hygiene workflow
  (compose validation, secret scanning, markdown lint); Python/web test
  jobs stubbed out but commented until real code lands.
- `docs/standards.md` — naming, style, commit, branch, versioning, logging,
  error handling, testing, and documentation conventions.
- `docs/` populated with all Phase 0 planning output: `vision.md`,
  `prd.md`, `architecture.md`, `open-source-landscape.md`, `roadmap.md`,
  `decisions.md`, `agents.md`, `api.md`, `database.md`.

### Notes
- No business logic yet, by design — see `docs/roadmap.md` Phase 2 for the
  first real Agent implementation (Research Agent).

## [0.0.0] - Phase 0
- Architecture proposal and Open Source Landscape research completed and
  approved (see `docs/decisions.md` ADR-001 onward).
