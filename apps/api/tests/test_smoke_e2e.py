"""End-to-end smoke test — docs/roadmap.md Phase 1.19.

"new project -> runs through all Stub Agents -> reaches published (faked)"

This is deliberately the first test that exercises apps/api, packages/core,
workflows/graph.py, and every agents/*/agent.py stub together — proving
the full pipeline *shape* (including the mandatory approval gate, ADR-011)
works before any Agent has real logic. Phase 2+ agents replace the stub
bodies; this test's assertions about event ORDER and the approval gate
should keep passing unchanged, since that's the contract, not the
implementation.
"""

from __future__ import annotations

import uuid

# Import every agent module so it registers itself (see agents/*/agent.py)
import agents.knowledge_agent.agent  # noqa: F401
import agents.publishing_agent.agent  # noqa: F401
import agents.recording_agent.agent  # noqa: F401
import agents.research_agent.agent  # noqa: F401
import agents.script_agent.agent  # noqa: F401
import agents.trend_agent.agent  # noqa: F401
import agents.video_agent.agent  # noqa: F401
import agents.voice_agent.agent  # noqa: F401
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from workflows.graph import build_graph


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

    # 2. Run the Orchestrator graph for this project — every node is a
    #    Stub Agent (Phase 1), but the graph *shape* is real: research ->
    #    knowledge -> idea scoring gate -> script -> storyboard ->
    #    recording -> video -> voice -> mandatory approval gate -> publish.
    graph = build_graph().compile(checkpointer=MemorySaver())
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}

    state = graph.invoke({"project_id": project["id"], "run_id": run_id, "events": []}, config=config)

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
    leave any path to a published state."""

    resp = client.post(
        "/api/projects",
        json={"source_type": "youtube", "source_url": "https://youtube.com/watch?v=abc"},
    )
    project = resp.json()

    graph = build_graph().compile(checkpointer=MemorySaver())
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}
    graph.invoke({"project_id": project["id"], "run_id": run_id, "events": []}, config=config)

    final_state = graph.invoke(Command(resume=False), config=config)

    assert final_state["approved"] is False
    assert "publish.approved" not in final_state["events"]

    # project status in the DB must remain untouched — no code path here
    # ever set it to "published".
    refreshed = client.get(f"/api/projects/{project['id']}").json()
    assert refreshed["status"] == "draft"
