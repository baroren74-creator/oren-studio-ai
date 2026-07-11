# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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
