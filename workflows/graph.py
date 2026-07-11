"""The Orchestrator — a single LangGraph StateGraph implementing the
studio workflow from docs/api.md's Event Types list.

This is the ONE place in the codebase that knows what order Agents run
in (docs/agents.md 'Hard rule'). It is embedded directly in apps/api /
services/orchestrator-worker as a Python library — this deliberately
does NOT use the hosted LangGraph Platform server (see
docs/decisions.md ADR-001).

Phase 1 (docs/roadmap.md 1.13): every node below calls a Stub Agent via
the Agent Registry, so the graph shape — including the idea-rejection
short-circuit (ADR-003) and the mandatory human approval gate before
publish (ADR-011) — can be validated end-to-end before any node has real
logic. Swap in real Agent implementations later without changing this
file's structure.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, TypedDict
from operator import add

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from core.registry import AgentRegistry, default_registry
from core.schemas.agent import AgentContext, AgentInput


class StudioState(TypedDict, total=False):
    """Graph state — deliberately thin. Node-level detail (full Agent
    input/output) lives in agent_runs/agent_events (docs/database.md),
    not duplicated into graph state."""

    project_id: str
    run_id: str
    events: Annotated[list[str], add]
    idea_score: float
    rejected: bool
    approved: bool


IDEA_SCORE_THRESHOLD = 50.0  # ADR-003: below this, idea.rejected — stops before expensive stages


def _run_agent_sync(registry: AgentRegistry, agent_name: str, state: StudioState) -> dict[str, Any]:
    """Helper: fetch an agent from the registry and run it against the
    current graph state. Agents are async (core.schemas.agent.Agent);
    LangGraph nodes here are sync wrappers around asyncio.run for
    simplicity in this skeleton — real nodes may want async node
    functions instead once agents do real (I/O-bound) work."""
    import asyncio

    agent = registry.get(agent_name)
    agent_input = AgentInput(
        run_id=uuid.UUID(state["run_id"]),
        project_id=uuid.UUID(state["project_id"]),
        payload={},
        context=AgentContext(),
    )
    output = asyncio.run(agent.run(agent_input))
    return output.model_dump()


def build_graph(registry: AgentRegistry | None = None):
    """Build (but do not compile) the studio graph. Pass a custom
    registry in tests to swap in fakes without touching module-level
    global state."""

    reg = registry or default_registry

    def research_node(state: StudioState) -> dict:
        out = _run_agent_sync(reg, "research_agent", state)
        return {"events": [out["next_event"]]}

    def knowledge_node(state: StudioState) -> dict:
        out = _run_agent_sync(reg, "knowledge_agent", state)
        return {"events": [out["next_event"]]}

    def idea_scoring_node(state: StudioState) -> dict:
        # Phase 1 stub: always scores above threshold. Phase 2.6 replaces
        # this with the real rubric (docs/agents.md 'Idea scoring rubric').
        return {"idea_score": 100.0, "events": ["idea.scored"]}

    def route_after_scoring(state: StudioState) -> str:
        if state.get("idea_score", 0) < IDEA_SCORE_THRESHOLD:
            return "rejected"
        return "continue"

    def idea_rejected_node(state: StudioState) -> dict:
        return {"rejected": True, "events": ["idea.rejected"]}

    def script_node(state: StudioState) -> dict:
        out = _run_agent_sync(reg, "script_agent", state)
        return {"events": [out["next_event"]]}

    def storyboard_node(state: StudioState) -> dict:
        # No dedicated Storyboard Agent in the registry (docs/roadmap.md
        # 3.7: a custom LLM-prompting module, not a registered Agent) —
        # this node marks the milestone event directly.
        return {"events": ["storyboard.ready"]}

    def recording_node(state: StudioState) -> dict:
        out = _run_agent_sync(reg, "recording_agent", state)
        return {"events": [out["next_event"]]}

    def video_node(state: StudioState) -> dict:
        out = _run_agent_sync(reg, "video_agent", state)
        return {"events": [out["next_event"]]}

    def voice_node(state: StudioState) -> dict:
        out = _run_agent_sync(reg, "voice_agent", state)
        return {"events": [out["next_event"]]}

    def final_review_node(state: StudioState) -> dict:
        # Approval Gate #2 (mandatory, docs/api.md) — pauses the graph
        # via LangGraph's native interrupt() until resumed with
        # Command(resume=True/False). This is ADR-001's reason for
        # choosing LangGraph: this primitive maps directly onto "nothing
        # publishes without Oren's approval."
        #
        # IMPORTANT, verified empirically while building this skeleton:
        # LangGraph replays a whole superstep on resume, not just the
        # interrupted node — splitting event emission into a node "before"
        # this one does NOT make it exactly-once; it still re-runs. This
        # is the same "at-least-once" execution guarantee Temporal and
        # most durable-execution engines give around checkpoints/retries.
        # Conclusion for this codebase: the in-memory `events` list here
        # is a debugging aid, not the source of truth — the real
        # `agent_events` table (docs/database.md) is, and any code that
        # writes to it from inside a node that sits near an interrupt
        # MUST be idempotent (e.g. INSERT ... ON CONFLICT DO NOTHING
        # keyed on (run_id, event_type)), not assume single execution.
        approved = interrupt({"reason": "final_review", "run_id": state["run_id"]})
        return {"approved": bool(approved), "events": ["final_review.requested"]}

    def route_after_review(state: StudioState) -> str:
        return "approved" if state.get("approved") else "rejected"

    def publishing_node(state: StudioState) -> dict:
        # ADR-011: prepares the export package + preview only. No
        # publish API call — Oren uploads manually and marks it
        # published himself (apps/api route, not this graph).
        out = _run_agent_sync(reg, "publishing_agent", state)
        return {"events": [out["next_event"], "publish.approved"]}

    graph = StateGraph(StudioState)

    graph.add_node("research", research_node)
    graph.add_node("knowledge", knowledge_node)
    graph.add_node("idea_scoring", idea_scoring_node)
    graph.add_node("idea_rejected", idea_rejected_node)
    graph.add_node("script", script_node)
    graph.add_node("storyboard", storyboard_node)
    graph.add_node("recording", recording_node)
    graph.add_node("video", video_node)
    graph.add_node("voice", voice_node)
    graph.add_node("final_review", final_review_node)
    graph.add_node("publishing", publishing_node)

    graph.add_edge(START, "research")
    graph.add_edge("research", "knowledge")
    graph.add_edge("knowledge", "idea_scoring")
    graph.add_conditional_edges(
        "idea_scoring",
        route_after_scoring,
        {"continue": "script", "rejected": "idea_rejected"},
    )
    graph.add_edge("idea_rejected", END)
    graph.add_edge("script", "storyboard")
    graph.add_edge("storyboard", "recording")
    graph.add_edge("recording", "video")
    graph.add_edge("video", "voice")
    graph.add_edge("voice", "final_review")
    graph.add_conditional_edges(
        "final_review",
        route_after_review,
        {"approved": "publishing", "rejected": END},
    )
    graph.add_edge("publishing", END)

    return graph


__all__ = ["StudioState", "build_graph", "IDEA_SCORE_THRESHOLD"]
