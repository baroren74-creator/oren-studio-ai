# workflows

The LangGraph orchestration graph definition(s) — the one place that
knows the order Agents run in and where the human-approval interrupts sit
(see `docs/architecture.md` section 2 and `docs/api.md` Event Types).
Agents themselves never know what comes before/after them; only this
layer does. Empty scaffold until Phase 1.13.
