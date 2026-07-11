"""End-to-end smoke test — docs/roadmap.md Phase 1.19.

"new project -> runs through all Stub Agents -> reaches published (faked)"

This is deliberately the first test that exercises apps/api, packages/core,
workflows/graph.py, and every agents/*/agent.py stub together — proving
the full pipeline *shape* (including the mandatory approval gate, ADR-011)
works before any Agent has real logic.

Phase 2.3 update: Research Agent now has real logic (agents/research_agent/
agent.py) and is registered on `default_registry` as a side effect of
importing it below. That means this file's "pipeline shape" test can no
longer rely on `default_registry` and expect an all-stub run — a real
ResearchAgent given a fake `https://github.com/x/y` URL would either hang
on a real network call or fail outright, which is not what this test is
for. `test_new_project_reaches_published_via_stub_pipeline` therefore
builds its own isolated all-stub `AgentRegistry` (see `_all_stub_registry`
below) and passes it to `build_graph(registry=...)` — exactly the escape
hatch `build_graph`'s docstring describes. This keeps the test's original
contract (event order, approval gate) intact and network-free, and also
makes it immune to every future stub-to-real swap, not just this one.

A second test, `test_research_node_passes_source_fields_to_real_agent`,
covers the thing that broke when Research Agent went from stub to real:
workflows/graph.py's research_node must forward project.source_type /
source_url into the Agent's payload (previously it always sent `{}` —
harmless for a Stub Agent that ignores its input, silently wrong for a
real one that branches on it, see `_agent_event`'s docstring).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

# Import every agent module so it registers itself (see agents/*/agent.py)
import agents.knowledge_agent.agent  # noqa: F401
import agents.publishing_agent.agent  # noqa: F401
import agents.recording_agent.agent  # noqa: F401
import agents.research_agent.agent  # noqa: F401
import agents.script_agent.agent  # noqa: F401
import agents.trend_agent.agent  # noqa: F401
import agents.video_agent.agent  # noqa: F401
import agents.voice_agent.agent  # noqa: F401
from core.registry import AgentRegistry
from core.schemas.agent import AgentOutput
from core.stub_agent import StubAgent
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from workflows.graph import build_graph

# Mirrors the NEXT_EVENT each agents/*/agent.py stub is registered with
# (Phase 1.18) — kept here, not imported, so this test independently
# pins down the event-order contract instead of trusting whatever each
# module currently does.
_STUB_NEXT_EVENTS = {
    "research_agent": "research.completed",
    "knowledge_agent": "source.ingested",
    "script_agent": "script.drafted",
    "recording_agent": "recording.completed",
    "video_agent": "video.rendered",
    "voice_agent": "voice.completed",
    "publishing_agent": "final_review.requested",
}


def _all_stub_registry(exclude: frozenset[str] = frozenset()) -> AgentRegistry:
    """A fresh registry of pure Stub Agents — the Phase 1.19 pipeline-shape
    test's actual dependency, decoupled from whatever `default_registry`
    happens to contain as real Agents land phase by phase. `exclude` lets
    a caller register everything-but-one as a stub and wire in a real (or
    mocked) Agent for the rest, e.g. the research_node wiring test below."""
    registry = AgentRegistry()
    for name, next_event in _STUB_NEXT_EVENTS.items():
        if name in exclude:
            continue
        stub = StubAgent(name=name, next_event=next_event)
        registry.register(name, lambda stub=stub: stub)
    return registry


def test_new_project_reaches_published_via_stub_pipeline(client):
    # 1. Create the project through the real HTTP API (proves apps/api +
    #    the DB layer work, not just the graph in isolation).
    resp = client.post(
        "/api/projects",
        json={"title": "Test: awesome-oss-repo", "source_type": "github", "source_url": "https://github.com/x/y"},
    )
    assert resp.status_code == 201
    project = resp.json()
    assert project["status"] == "draft"

    # 2. Run the Orchestrator graph for this project against an isolated
    #    all-stub registry (see module docstring) — every node is a Stub
    #    Agent, but the graph *shape* is real: research -> knowledge ->
    #    idea scoring gate -> script -> storyboard -> recording -> video ->
    #    voice -> mandatory approval gate -> publish.
    graph = build_graph(registry=_all_stub_registry()).compile(checkpointer=MemorySaver())
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}

    state = graph.invoke(
        {
            "project_id": project["id"],
            "run_id": run_id,
            "source_type": project["source_type"],
            "source_url": project["source_url"],
            "events": [],
        },
        config=config,
    )

    # 3. Confirm it actually paused for human approval — ADR-011/ADR-001:
    #    nothing reaches "published" without this gate, even in a stub run.
    assert state.get("__interrupt__"), "pipeline must pause for approval before publishing"
    assert "publish.approved" not in state["events"]

    # 4. Simulate Oren approving in the Studio UI (Approval Gate #2).
    final_state = graph.invoke(Command(resume=True), config=config)
    assert final_state["approved"] is True
    assert final_state["events"][-1] == "publish.approved"

    expected_order = [
        "research.completed",
        "source.ingested",
        "idea.scored",
        "script.drafted",
        "storyboard.ready",
        "recording.completed",
        "video.rendered",
        "voice.completed",
    ]
    # first N events (pre-interrupt) must be in the exact order the graph
    # defines — this is the part of the contract most worth protecting
    # against accidental reordering later.
    assert final_state["events"][: len(expected_order)] == expected_order

    # 5. Persist the run to the DB the way services/orchestrator-worker
    #    will in Phase 2+ (docs/architecture.md), then mark the project
    #    published ("faked" per docs/roadmap.md 1.19 — no real publish
    #    API call, ADR-011).
    from app.db import SessionLocal
    from app.models import AgentEvent, AgentRun, Project

    db = SessionLocal()
    try:
        run = AgentRun(
            project_id=project["id"],
            agent_name="orchestrator",
            status="success",
            input={"run_id": run_id},
            output={"events": final_state["events"]},
        )
        db.add(run)
        db.flush()
        for event_type in final_state["events"]:
            db.add(AgentEvent(run_id=run.id, event_type=event_type, payload={}))

        db_project = db.get(Project, project["id"])
        db_project.status = "published"
        db.commit()
    finally:
        db.close()

    # 6. Confirm it's all visible through the real API — a human (Oren)
    #    looking at the Studio UI would see exactly this.
    timeline = client.get(f"/api/projects/{project['id']}/timeline").json()
    assert [e["event_type"] for e in timeline] == final_state["events"]

    refreshed = client.get(f"/api/projects/{project['id']}").json()
    assert refreshed["status"] == "published"

    runs = client.get("/api/agent-runs").json()
    assert len(runs) == 1
    assert runs[0]["agent_name"] == "orchestrator"


def test_rejecting_final_review_does_not_publish(client):
    """The other half of the approval-gate contract: saying no must not
    leave any path to a published state.

    Uses `build_graph()`'s default registry (not the all-stub one above)
    deliberately: source_type="youtube" drives the *real* Research Agent
    into its "skipped" path (agents/research_agent/agent.py — YouTube
    isn't implemented yet, Phase 2.4+), which is itself a real code path
    worth covering and touches no network. See
    test_research_node_passes_source_fields_to_real_agent below for the
    github/happy-path wiring check."""

    resp = client.post(
        "/api/projects",
        json={"source_type": "youtube", "source_url": "https://youtube.com/watch?v=abc"},
    )
    project = resp.json()

    graph = build_graph().compile(checkpointer=MemorySaver())
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}
    graph.invoke(
        {
            "project_id": project["id"],
            "run_id": run_id,
            "source_type": project["source_type"],
            "source_url": project["source_url"],
            "events": [],
        },
        config=config,
    )

    final_state = graph.invoke(Command(resume=False), config=config)

    assert final_state["approved"] is False
    assert "publish.approved" not in final_state["events"]
    # research_node must not leak a bare `None` into events when the real
    # Research Agent returns status="skipped" (next_event=None) — see
    # workflows/graph.py's _agent_event.
    assert None not in final_state["events"]

    # project status in the DB must remain untouched — no code path here
    # ever set it to "published".
    refreshed = client.get(f"/api/projects/{project['id']}").json()
    assert refreshed["status"] == "draft"


def test_research_node_passes_source_fields_to_real_agent(client, monkeypatch):
    """Regression test for the exact bug found while wiring the real
    Research Agent into the graph (Phase 2.3): research_node used to call
    _run_agent_sync with an empty payload no matter what, so
    ResearchAgent.run() always saw source_type=None and returned
    status="skipped" even for a real GitHub project — the Stub Agent it
    replaced never noticed because it ignored its input entirely.

    Verifies the fix end-to-end through the graph (not just by calling
    the Agent directly, which agents/research_agent/tests/test_agent.py
    already covers) by mocking ResearchAgent.run itself and asserting on
    the AgentInput.payload it actually received."""

    resp = client.post(
        "/api/projects",
        json={"source_type": "github", "source_url": "https://github.com/octocat/Hello-World"},
    )
    project = resp.json()

    received_inputs = []

    async def _fake_run(self, input):
        received_inputs.append(input)
        return AgentOutput(status="success", result={}, next_event="research.completed")

    monkeypatch.setattr("agents.research_agent.agent.ResearchAgent.run", _fake_run)

    registry = _all_stub_registry(exclude=frozenset({"research_agent"}))
    registry.register("research_agent", lambda: agents.research_agent.agent.agent)

    graph = build_graph(registry=registry).compile(checkpointer=MemorySaver())
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}
    graph.invoke(
        {
            "project_id": project["id"],
            "run_id": run_id,
            "source_type": project["source_type"],
            "source_url": project["source_url"],
            "events": [],
        },
        config=config,
    )

    assert len(received_inputs) == 1
    assert received_inputs[0].payload == {
        "source_type": "github",
        "source_url": "https://github.com/octocat/Hello-World",
    }
