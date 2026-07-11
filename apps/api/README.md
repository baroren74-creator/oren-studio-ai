# apps/api

FastAPI backend — the BFF for `apps/web`, and the host process for the
embedded LangGraph Orchestrator (see ADR-001: not the hosted LangGraph
Platform server). Owns auth, request validation, and is the only thing
that talks to Postgres directly. See `docs/api.md` for the route
contract. No business logic yet (Phase 1) — see `docs/roadmap.md` 1.8–1.14.
