"""Knowledge Agent — see docs/agents.md for its responsibility and
docs/roadmap.md for when real logic replaces this stub.

Currently a StubAgent registration only (Phase 1.18): it always succeeds
immediately so the Orchestrator graph and event flow can be validated
end-to-end before this agent has real behavior. Replace `run()` with
real logic in a later phase without changing how it's registered or
called — that's the point of the Agent contract (docs/agents.md).
"""

from __future__ import annotations

from core.registry import default_registry
from core.stub_agent import StubAgent

NAME = "knowledge_agent"
NEXT_EVENT = 'source.ingested'

agent = StubAgent(name=NAME, next_event=NEXT_EVENT)

default_registry.register(NAME, lambda: agent)
