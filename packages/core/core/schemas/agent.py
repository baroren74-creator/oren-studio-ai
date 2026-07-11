"""The Agent contract — see docs/agents.md.

Every Agent in the system, without exception, implements this contract:
it receives an AgentInput and returns an AgentOutput. Agents never import
or call each other directly; the Orchestrator (workflows/graph.py) is the
only thing that knows what order they run in, and all cross-agent
communication happens through events (core.events) and the database, not
through Python imports.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, Field

AgentStatus = Literal["success", "failed", "needs_approval", "skipped"]


class ArtifactRef(BaseModel):
    """Pointer to something an Agent produced (a DB row, a file in
    storage, etc.) — never the artifact's full content inline."""

    type: str
    ref_id: str
    storage_url: str | None = None


class CostInfo(BaseModel):
    """Cost accounting for a single Agent run — see docs/decisions.md
    ADR-003 (idea scoring is a hard cost gate) and standards.md's
    guidance on not letting expensive stages run unchecked."""

    tokens_used: int = 0
    cost_usd: float = 0.0
    provider: str | None = None


class AgentContext(BaseModel):
    """Read-only context handed to every Agent run: references into
    memory/style guide, and remaining budget for this run. An Agent reads
    from this — it never mutates shared state directly."""

    style_profile_id: str | None = None
    memory_refs: list[str] = Field(default_factory=list)
    budget_remaining_usd: float | None = None


class AgentInput(BaseModel):
    run_id: UUID
    project_id: UUID
    payload: dict[str, Any] = Field(default_factory=dict)
    context: AgentContext = Field(default_factory=AgentContext)


class AgentOutput(BaseModel):
    status: AgentStatus
    result: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    cost: CostInfo = Field(default_factory=CostInfo)
    next_event: str | None = None


@runtime_checkable
class Agent(Protocol):
    """Structural contract every agent implementation satisfies. See
    agents/*/agent.py for concrete implementations, and
    core.registry.AgentRegistry for how the Orchestrator looks them up
    by name instead of importing them directly."""

    name: str
    version: str

    async def run(self, input: AgentInput) -> AgentOutput: ...
