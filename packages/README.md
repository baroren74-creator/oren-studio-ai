# packages

Shared library code with a strict one-way dependency rule: `apps/`,
`agents/`, `services/`, and `providers/` may depend on `packages/`, never
the reverse (see `docs/standards.md` section 2). Currently `core/`
(schemas, event types, agent registry) and `memory/` (knowledge/RAG
layer, ADR-002).
