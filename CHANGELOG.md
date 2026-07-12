# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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
