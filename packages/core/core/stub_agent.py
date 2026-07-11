"""Generic Stub Agent — see docs/roadmap.md Phase 1.18.

Used to validate the full pipeline shape (Orchestrator graph, event flow,
DB writes) end-to-end before any Agent has real logic. Every real agent
module below (agents/*/agent.py) currently just instantiates this with
its own name/next_event and registers it — swap in real logic later
without touching the Orchestrator or the registry wiring.
"""

from __future__ import annotations

from core.events.types import EventType
from core.schemas.agent import AgentInput, AgentOutput, CostInfo


class StubAgent:
    """Satisfies the Agent protocol (core.schemas.agent.Agent) by
    always succeeding immediately with an empty result."""

    def __init__(self, name: str, version: str = "0.0.1-stub", next_event: str | None = None) -> None:
        self.name = name
        self.version = version
        self._next_event = next_event

    async def run(self, input: AgentInput) -> AgentOutput:
        return AgentOutput(
            status="success",
            result={"stub": True, "agent": self.name, "run_id": str(input.run_id)},
            artifacts=[],
            cost=CostInfo(tokens_used=0, cost_usd=0.0, provider=None),
            next_event=self._next_event,
        )


__all__ = ["StubAgent", "EventType"]
