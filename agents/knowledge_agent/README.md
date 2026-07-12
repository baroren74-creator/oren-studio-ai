# knowledge_agent

Chunks + embeds + indexes the Research Agent's raw digest/transcript text
into Qdrant's `knowledge_docs` collection via `packages/memory`. Does
**not** own a RAG framework — see ADR-002. Semantic search itself is a
separate `apps/api` route (`GET /api/knowledge/search`), not this Agent.

**Implemented** — `docs/roadmap.md` Phase 2.8/2.9, `docs/agents.md`'s
Knowledge Agent section for the full write-up (payload shape, the
`source_id`/point-ID pragmatic stand-ins, current search limitations).
