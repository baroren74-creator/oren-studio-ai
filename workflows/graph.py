"""The Orchestrator — a single LangGraph StateGraph implementing the
studio workflow from docs/api.md's Event Types list.

This is the ONE place in the codebase that knows what order Agents run
in (docs/agents.md 'Hard rule'). It is embedded directly in apps/api /
services/orchestrator-worker as a Python library — this deliberately
does NOT use the hosted LangGraph Platform server (see
docs/decisions.md ADR-001).

Phase 1 (docs/roadmap.md 1.13) built this with every node calling a Stub
Agent via the Agent Registry, so the graph shape — including the
idea-rejection short-circuit (ADR-003) and the mandatory human approval
gate before publish (ADR-011) — could be validated end-to-end before any
node had real logic. Phase 2.3/2.4/2.6/2.7 replaced research_node and
idea_scoring_node with real logic without changing this file's
structure — that was the point. Remaining nodes (knowledge, script,
recording, video, voice, publishing) are still Stub Agents.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, TypedDict
from operator import add

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from core.registry import AgentRegistry, default_registry
from core.schemas.agent import AgentContext, AgentInput
from workflows.idea_scoring import IdeaScoringError, score_idea


class StudioState(TypedDict, total=False):
    """Graph state — deliberately thin. Node-level detail (full Agent
    input/output) lives in agent_runs/agent_events (docs/database.md),
    not duplicated into graph state."""

    project_id: str
    run_id: str
    source_type: str | None
    source_url: str | None
    research_summary: str | None
    research_key_points: list[str] | None
    research_raw_text: str | None
    events: Annotated[list[str], add]
    idea_score: float
    idea_score_breakdown: dict[str, int] | None
    rejected: bool
    approved: bool
    # Style profile fields (Phase 3.1, docs/database.md's style_profile
    # table) — deliberately flat scalars here, not fetched by the graph
    # itself (workflows/graph.py never touches the DB — see knowledge_node's
    # comment for the established reasoning). Whatever eventually calls
    # graph.invoke() for real is responsible for looking up the current
    # style_profile (apps/api/app/services/style_profile.py's
    # get_current_style_profile()) and seeding these into the initial
    # state, same as source_type/source_url today.
    style_tone_notes: str | None
    style_opening_patterns: list[str] | None
    style_closing_patterns: list[str] | None
    style_avg_length_seconds: float | None
    # Script Agent output (Phase 3.2-3.4) — promoted into state the same
    # way research_summary/research_key_points are, for downstream nodes
    # (Storyboard Agent, Phase 3.7, not built yet) and test visibility.
    script_hook: str | None
    script_body: str | None
    script_cta: str | None
    script_caption: str | None
    script_title: str | None
    script_hashtags: list[str] | None


IDEA_SCORE_THRESHOLD = 50.0  # ADR-003: below this, idea.rejected — stops before expensive stages


def _run_agent_sync(
    registry: AgentRegistry, agent_name: str, state: StudioState, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Helper: fetch an agent from the registry and run it against the
    current graph state. Agents are async (core.schemas.agent.Agent);
    LangGraph nodes here are sync wrappers around asyncio.run for
    simplicity in this skeleton — real nodes may want async node
    functions instead once agents do real (I/O-bound) work.

    `payload` defaults to {} (Phase 1 stub behavior, still correct for
    nodes whose Agent doesn't read anything from it yet). Nodes whose
    real Agent branches on payload contents (e.g. research_node /
    ResearchAgent's source_type check) must build and pass their own —
    see the ADR-012-adjacent lesson learned wiring in the real Research
    Agent (docs/roadmap.md Phase 2.3): a Stub Agent ignoring its input
    can silently hide a graph wiring gap that only breaks once real
    logic depends on that input."""
    import asyncio

    agent = registry.get(agent_name)
    agent_input = AgentInput(
        run_id=uuid.UUID(state["run_id"]),
        project_id=uuid.UUID(state["project_id"]),
        payload=payload or {},
        context=AgentContext(),
    )
    output = asyncio.run(agent.run(agent_input))
    return output.model_dump()


def _agent_event(
    registry: AgentRegistry, agent_name: str, state: StudioState, payload: dict[str, Any] | None = None
) -> dict:
    """Run an Agent and turn its next_event into a graph state update.
    Centralized so every node handles a `None` next_event (Agent status
    "skipped"/"failed") the same way: no event appended, rather than
    letting `None` leak into the `events` list — see research_node for
    the case this was written for (a "skipped" ResearchAgent run)."""
    out = _run_agent_sync(registry, agent_name, state, payload=payload)
    return {"events": [out["next_event"]] if out["next_event"] else []}


def build_graph(registry: AgentRegistry | None = None):
    """Build (but do not compile) the studio graph. Pass a custom
    registry in tests to swap in fakes without touching module-level
    global state."""

    reg = registry or default_registry

    def research_node(state: StudioState) -> dict:
        # Only real node so far whose Agent branches on payload contents
        # (ResearchAgent checks source_type/source_url — agents/
        # research_agent/agent.py) — everything else is still a Stub
        # Agent that ignores payload, so still gets {} via _agent_event's
        # default.
        payload = {"source_type": state.get("source_type"), "source_url": state.get("source_url")}
        out = _run_agent_sync(reg, "research_agent", state, payload=payload)
        update: dict[str, Any] = {"events": [out["next_event"]] if out["next_event"] else []}
        # Only set research_summary/key_points when the Agent's result
        # actually has them (a real, successful ResearchAgent run) —
        # deliberately does NOT overwrite with None on every run, so a
        # Stub Agent registered under "research_agent" (whose result has
        # no "summary" key, see core.stub_agent.StubAgent) can't clobber
        # a value a caller pre-seeded in the initial graph state, e.g.
        # for graph-shape tests that stub every Agent but still want
        # idea_scoring_node to see a summary (apps/api/tests/
        # test_smoke_e2e.py).
        result = out.get("result") or {}
        if "summary" in result:
            update["research_summary"] = result.get("summary")
            update["research_key_points"] = result.get("key_points")
            update["research_raw_text"] = result.get("raw_text")
        return update

    def knowledge_node(state: StudioState) -> dict:
        # Phase 2.8: Knowledge Agent indexes the Research Agent's raw
        # digest/transcript text into Qdrant (packages/memory). `source_id`
        # is `run_id` (agent_runs.id, a real Postgres row) as a pragmatic
        # stand-in for `sources.id` — there's no live orchestrator-worker
        # persisting a `sources` row yet (same gap noted in apps/api/app/
        # services/research.py's docstring), and MemoryStore's deterministic
        # point-ID scheme (ADR-008, packages/memory/memory/store.py) only
        # needs a stable, traceable ID, not specifically that table. Revisit
        # once Source persistence is wired to a real orchestrator.
        payload = {
            "source_id": state["run_id"],
            "text": state.get("research_raw_text"),
            "project_id": state["project_id"],
            "source_type": state.get("source_type"),
            "source_url": state.get("source_url"),
        }
        return _agent_event(reg, "knowledge_agent", state, payload=payload)

    def idea_scoring_node(state: StudioState) -> dict:
        # Phase 2.6/2.7 (docs/agents.md 'Idea scoring rubric', ADR-003):
        # a real rubric-based score gates progression — no Research Agent
        # output to score means nothing to base a decision on, so this
        # can't clear the gate (score 0.0, same as an explicit rubric
        # failure below). route_after_scoring/idea_rejected_node handle
        # the actual "stop here" branching — this node's only job is to
        # produce a score, not to decide what to do with it.
        summary = state.get("research_summary")
        if not summary:
            return {"idea_score": 0.0, "events": ["idea.scored"]}
        try:
            score = score_idea(summary=summary, key_points=state.get("research_key_points"))
        except IdeaScoringError:
            return {"idea_score": 0.0, "events": ["idea.scored"]}
        return {
            "idea_score": score.total,
            "idea_score_breakdown": score.breakdown,
            "events": ["idea.scored"],
        }

    def route_after_scoring(state: StudioState) -> str:
        if state.get("idea_score", 0) < IDEA_SCORE_THRESHOLD:
            return "rejected"
        return "continue"

    def idea_rejected_node(state: StudioState) -> dict:
        return {"rejected": True, "events": ["idea.rejected"]}

    def script_node(state: StudioState) -> dict:
        # Phase 3.2-3.4: Script Agent writes Hook/Body/CTA/Caption/Title/
        # Hashtags from research_summary/research_key_points, in Oren's
        # voice per whatever style_profile fields the caller seeded into
        # the initial state (see StudioState's comment above).
        payload = {
            "research_summary": state.get("research_summary"),
            "research_key_points": state.get("research_key_points"),
            "style_tone_notes": state.get("style_tone_notes"),
            "style_opening_patterns": state.get("style_opening_patterns"),
            "style_closing_patterns": state.get("style_closing_patterns"),
            "style_avg_length_seconds": state.get("style_avg_length_seconds"),
        }
        out = _run_agent_sync(reg, "script_agent", state, payload=payload)
        update: dict[str, Any] = {"events": [out["next_event"]] if out["next_event"] else []}
        # Same "only promote on an actual successful real-Agent result"
        # guard as research_node — a Stub Agent's result has no "hook"
        # key, so this can't clobber a value a test pre-seeded.
        result = out.get("result") or {}
        if "hook" in result:
            update["script_hook"] = result.get("hook")
            update["script_body"] = result.get("body")
            update["script_cta"] = result.get("cta")
            update["script_caption"] = result.get("caption")
            update["script_title"] = result.get("title")
            update["script_hashtags"] = result.get("hashtags")
        return update

    def storyboard_node(state: StudioState) -> dict:
        # No dedicated Storyboard Agent in the registry (docs/roadmap.md
        # 3.7: a custom LLM-prompting module, not a registered Agent) —
        # this node marks the milestone event directly.
        return {"events": ["storyboard.ready"]}

    def recording_node(state: StudioState) -> dict:
        return _agent_event(reg, "recording_agent", state)

    def video_node(state: StudioState) -> dict:
        return _agent_event(reg, "video_agent", state)

    def voice_node(state: StudioState) -> dict:
        return _agent_event(reg, "voice_agent", state)

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
