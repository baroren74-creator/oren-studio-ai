# agents

One folder per Agent. Every Agent implements the shared contract in
`packages/core/schemas` (`AgentInput` → `AgentOutput`) and is looked up
via the Agent Registry — never imported directly by another Agent (see
`docs/standards.md` section 2). Full roster and responsibilities:
`docs/agents.md`.
