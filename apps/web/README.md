# apps/web

Next.js Studio UI. Chat, Projects, Knowledge Base, Prompt Library,
Settings — see `docs/architecture.md` section 2. Talks to `apps/api` over
REST + WebSocket only; never talks to Postgres/Redis/Qdrant directly.
No business logic here yet (Phase 1) — see `docs/roadmap.md` 1.10, 1.15–1.17.
