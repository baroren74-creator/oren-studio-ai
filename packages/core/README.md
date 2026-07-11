# packages/core

Shared, provider-agnostic domain code used by `apps/`, `agents/`,
`services/`, and `providers/` — and only depended on, never the reverse
(see `docs/standards.md` section 2). Contains:

- `schemas/` — `AgentInput`/`AgentOutput` and friends (see `docs/agents.md`)
- `events/` — the canonical Event Type definitions (see `docs/api.md`)
- Agent Registry (config-driven agent lookup)

The LangGraph graph definition itself lives in `workflows/`, not here —
this package is data shapes and contracts, not orchestration logic.
