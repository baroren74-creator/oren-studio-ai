# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

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
