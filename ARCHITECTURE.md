# Architecture (pointer)

The full architecture document lives at
[`docs/architecture.md`](docs/architecture.md), and the open-source
composition strategy behind it lives at
[`docs/open-source-landscape.md`](docs/open-source-landscape.md).

This root-level file exists only because `ARCHITECTURE.md` is a
conventional place people look first — keeping the real content in
`docs/` avoids having two copies that can drift out of sync.

**One-paragraph summary:** Next.js (Studio UI) + FastAPI (API/BFF) +
LangGraph (orchestrator, embedded — not the hosted Platform server) +
Redis (event bus) + PostgreSQL (source of truth) + Qdrant (vector index
only, never a second source of truth) + S3-compatible storage. Every
capability is an `Agent` behind a fixed `AgentInput`/`AgentOutput`
contract, registered in an Agent Registry, communicating only through
events — never by importing another agent directly. Every external
capability (LLM, video, avatar, voice, publishing) is a swappable
Provider plugin. Nothing publishes without a human approval gate, enforced
at the database level, not just in application code.

See `docs/decisions.md` for why each of these choices was made over the
alternatives that were evaluated.
