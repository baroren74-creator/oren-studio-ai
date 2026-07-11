"""Agent Registry — see docs/agents.md 'Agent Registry'.

Config-driven mapping of agent_name -> implementation, read by the
Orchestrator (workflows/graph.py) at runtime. Adding a new Agent means
registering it here (or in the config this loads from) — never hardcoding
an import into the Orchestrator graph itself. This is what makes the
Agent-First / Plugin-Based principle in docs/architecture.md real instead
of aspirational.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.schemas.agent import Agent


@dataclass
class AgentRegistration:
    name: str
    factory: "callable[[], Agent]"
    provider_config: dict = field(default_factory=dict)


class AgentRegistry:
    """In-memory registry. Backed today by explicit `.register()` calls
    at process startup (see agents/*/__init__.py registration side
    effect, or a central bootstrap module) — swappable later for a DB-
    or config-file-backed registry without changing callers, since
    everything goes through `.get()`."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentRegistration] = {}

    def register(self, name: str, factory: "callable[[], Agent]", **provider_config) -> None:
        if name in self._agents:
            raise ValueError(f"Agent '{name}' is already registered")
        self._agents[name] = AgentRegistration(name=name, factory=factory, provider_config=provider_config)

    def get(self, name: str) -> "Agent":
        try:
            registration = self._agents[name]
        except KeyError as exc:
            raise KeyError(
                f"No agent registered under '{name}'. Registered agents: "
                f"{sorted(self._agents)}"
            ) from exc
        return registration.factory()

    def names(self) -> list[str]:
        return sorted(self._agents)


# Process-wide default registry. Agents register themselves against this
# instance on import (see agents/*/agent.py bottom-of-file registration).
default_registry = AgentRegistry()
