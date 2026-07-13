# Oren Studio AI

A personal, single-user, agent-based content studio. It turns a source (a
GitHub repo, a YouTube video, a tweet, an article) into a short,
Hebrew-language, published video — researched, scripted, edited, and
captioned by a pipeline of cooperating AI Agents, with a mandatory human
approval gate before anything goes live.

This is **not** a SaaS product. It is being built for one user. See
`docs/vision.md` for the full rationale.

## Status

**Phase 3 — Script + Storyboard, in progress.** Phases 1 (skeleton) and 2
(Research/Trend/Knowledge Agents, idea scoring) are done. Phase 3's
`style_profile` questionnaire, a real Script Agent, a synchronous
`POST /api/projects/{id}/run` endpoint wiring the whole graph together
end-to-end (with a matching "Run" button in `apps/web`), a
CRUD + versioning Prompt Library (with a diff view between versions),
Approval Gate #1 (review/approve/reject/request-edit a drafted script),
and the Storyboard module (a drafted script turned into an ordered scene
breakdown) are done. Next up: the real Storyboard UI (scene list +
preview) — see `docs/roadmap.md` for the exact state of every item.

## Repository layout

```
oren-studio-ai/
├── docs/          # all planning & reference docs — start here
├── apps/          # deployable applications (web = Next.js Studio UI, api = FastAPI backend)
├── packages/      # shared library code (core schemas, event types, memory layer)
├── services/      # standalone backend services (orchestrator worker, scheduler)
├── agents/        # one folder per Agent (Research, Trend, Knowledge, Script, ...)
├── providers/     # plugin adapters (llm, video, avatar, voice, publish, search, crawl)
├── workflows/     # LangGraph orchestration graph + event-flow definitions
├── prompts/       # versioned prompt library source
├── scripts/       # dev/ops scripts
├── docker/        # Dockerfiles + compose fragments per app/service
└── .github/       # CI, PR template, CODEOWNERS
```

Every folder above has its own `README.md` explaining its exact
responsibility and — critically — what it must **not** contain (the
architecture depends on agents never importing each other directly; see
`docs/architecture.md` section 3).

## Start here

1. `docs/vision.md` — why this project exists
2. `docs/prd.md` — the original product requirements
3. `docs/architecture.md` — full system architecture (updated after OSS research)
4. `docs/open-source-landscape.md` — what we adopt vs. build vs. defer, and why
5. `docs/roadmap.md` — the granular, phase-by-phase build plan
6. `docs/decisions.md` — architecture decision log (ADRs)
7. `docs/standards.md` — coding/commit/branch/testing conventions
8. `docs/agents.md`, `docs/api.md`, `docs/database.md` — implementation-level references

## Local development infrastructure

```bash
make up      # start postgres, redis, qdrant, minio, searxng
make ps      # check status
make down    # stop everything
```

Copy `.env.example` to `.env` and fill in real values before running
anything beyond the infra containers.

## Contributing (to yourself, six months from now)

See `CONTRIBUTING.md`. Yes, this matters even for a single-user project —
future-you will not remember why a decision was made unless past-you wrote
it down in `docs/decisions.md`.

## License

Proprietary / all rights reserved for the original code. Third-party
open-source components retain their own licenses — see
`docs/open-source-landscape.md` for a full audit. See `LICENSE`.
