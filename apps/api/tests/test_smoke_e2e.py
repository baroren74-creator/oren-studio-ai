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

Phase 2.6/2.7 update: idea_scoring_node is also real now
(workflows/idea_scoring.py) and is NOT behind the Agent Registry (it's a
plain graph node, like storyboard_node), so `_all_stub_registry()` alone
can no longer make a run "fully stubbed" — idea_scoring_node will always
call the real (LLM-backed) `score_idea()` unless a test also mocks
`workflows.graph.score_idea` and seeds a `research_summary` in the
initial state (idea_scoring_node short-circuits to a 0.0 rejection
before ever calling score_idea if there's no summary to score — see
`_mock_passing_score` below). `test_rejecting_final_review_does_not_publish`
was rewritten for the same reason: a "youtube" project now gets
correctly rejected at the *scoring* gate (no Research Agent support yet
-> no summary -> score 0.0) before ever reaching final_review, which is
new-and-correct behavior, not a bug — see
`test_low_score_idea_is_rejected_before_final_review` for a test that
protects it explicitly. `test_rejecting_final_review_does_not_publish`
itself now uses a mocked passing score so it can actually reach
final_review and test rejection *there*, which was always its point.
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
from workflows.idea_scoring import IdeaScore
from workflows.storyboard import StoryboardResult


def _mock_passing_score(monkeypatch, total: float = 100.0) -> None:
    """Stub out the real (LLM-backed) idea scorer with a fixed passing
    score, for tests whose focus is graph shape / later gates, not the
    rubric itself (that's workflows/tests/test_idea_scoring.py's job)."""
    fake_score = IdeaScore(total=total, breakdown={"novelty": 25, "audience_relevance": 25, "source_reliability": 25, "visual_potential": 25})
    monkeypatch.setattr("workflows.graph.score_idea", lambda **kwargs: fake_score)

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


def test_new_project_reaches_published_via_stub_pipeline(client, monkeypatch):
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
    #    voice -> mandatory approval gate -> publish. idea_scoring_node
    #    isn't Agent-Registry-based (see module docstring), so it needs
    #    its own mock + a seeded research_summary to clear the gate.
    _mock_passing_score(monkeypatch)
    graph = build_graph(registry=_all_stub_registry()).compile(checkpointer=MemorySaver())
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}

    state = graph.invoke(
        {
            "project_id": project["id"],
            "run_id": run_id,
            "source_type": project["source_type"],
            "source_url": project["source_url"],
            "research_summary": "Stub research summary for the pipeline-shape test.",
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


def test_rejecting_final_review_does_not_publish(client, monkeypatch):
    """The other half of the approval-gate contract: saying no must not
    leave any path to a published state. Uses the all-stub registry plus
    a mocked passing score (same reasoning as
    test_new_project_reaches_published_via_stub_pipeline) so the run
    actually reaches final_review — this test is specifically about
    rejection *there*, not at the earlier scoring gate (see
    test_low_score_idea_is_rejected_before_final_review for that)."""

    resp = client.post(
        "/api/projects",
        json={"source_type": "github", "source_url": "https://github.com/x/y"},
    )
    project = resp.json()

    _mock_passing_score(monkeypatch)
    graph = build_graph(registry=_all_stub_registry()).compile(checkpointer=MemorySaver())
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}
    graph.invoke(
        {
            "project_id": project["id"],
            "run_id": run_id,
            "source_type": project["source_type"],
            "source_url": project["source_url"],
            "research_summary": "Stub research summary for the rejection test.",
            "events": [],
        },
        config=config,
    )

    final_state = graph.invoke(Command(resume=False), config=config)

    assert final_state["approved"] is False
    assert "publish.approved" not in final_state["events"]
    assert None not in final_state["events"]

    # project status in the DB must remain untouched — no code path here
    # ever set it to "published".
    refreshed = client.get(f"/api/projects/{project['id']}").json()
    assert refreshed["status"] == "draft"


def test_low_score_idea_is_rejected_before_final_review(client):
    """New real behavior from Phase 2.6/2.7 (ADR-003's cost gate):
    a project whose source type Research Agent doesn't support at all
    (articles/tweets — Research Agent currently handles github/youtube
    only, see SUPPORTED_SOURCE_TYPES) produces no research_summary,
    which idea_scoring_node treats as an automatic 0.0 — below
    IDEA_SCORE_THRESHOLD, so the pipeline stops at idea_rejected and
    never reaches the expensive stages, let alone final_review. Uses
    `build_graph()`'s default registry deliberately: this is exactly the
    real Research Agent's real "skipped" path, no mocking needed, no
    network touched. (A malformed/unfetchable YouTube URL hits a
    different real path — status="failed", not "skipped" — covered by
    agents/research_agent/tests/test_youtube_source.py instead; both
    produce idea_score=0.0 the same way, so either is a valid "nothing to
    score" case here.)

    Phase 2.8: the real Knowledge Agent also skips (no next_event) here —
    Research Agent's "skipped" run leaves research_raw_text unset, so
    knowledge_node's payload has no text to index (agents/knowledge_agent/
    agent.py's own "nothing to index" skip path). Same lesson as Research
    Agent going real: a Stub Agent ignoring its input can hide a graph
    wiring gap that only shows up once real logic depends on that input —
    "source.ingested" no longer fires unconditionally."""

    resp = client.post(
        "/api/projects",
        json={"source_type": "article", "source_url": "https://example.com/some-post"},
    )
    project = resp.json()

    graph = build_graph().compile(checkpointer=MemorySaver())
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}
    final_state = graph.invoke(
        {
            "project_id": project["id"],
            "run_id": run_id,
            "source_type": project["source_type"],
            "source_url": project["source_url"],
            "events": [],
        },
        config=config,
    )

    assert not final_state.get("__interrupt__"), "must not reach final_review — rejected earlier, at scoring"
    assert final_state["rejected"] is True
    assert final_state["idea_score"] == 0.0
    assert final_state["events"] == ["idea.scored", "idea.rejected"]
    # Neither research_node nor knowledge_node may leak a bare `None`
    # into events when their real Agent returns status="skipped"
    # (next_event=None) — see workflows/graph.py's _agent_event.
    assert None not in final_state["events"]

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


def test_knowledge_node_passes_research_output_to_real_agent(client, monkeypatch):
    """Phase 2.8 counterpart to the research_node regression test above:
    knowledge_node must forward research_node's raw_text (threaded through
    StudioState as research_raw_text) into the Knowledge Agent's payload,
    keyed as source_id=run_id (see workflows/graph.py's knowledge_node
    comment for why run_id stands in for a real sources.id row). Mocks
    ResearchAgent.run (network-free) and patches
    agents.knowledge_agent.agent._build_store so the real KnowledgeAgent
    runs its actual logic without touching Qdrant/embeddings."""

    resp = client.post(
        "/api/projects",
        json={"source_type": "github", "source_url": "https://github.com/octocat/Hello-World"},
    )
    project = resp.json()

    async def _fake_research_run(self, input):
        return AgentOutput(
            status="success",
            result={"summary": "A demo repo.", "key_points": ["one"], "raw_text": "full digest text here"},
            next_event="research.completed",
        )

    monkeypatch.setattr("agents.research_agent.agent.ResearchAgent.run", _fake_research_run)

    upsert_calls = []

    class _FakeStore:
        def upsert_document(self, **kwargs):
            upsert_calls.append(kwargs)
            return 2

    monkeypatch.setattr("agents.knowledge_agent.agent._build_store", lambda: _FakeStore())

    registry = _all_stub_registry(exclude=frozenset({"research_agent", "knowledge_agent"}))
    registry.register("research_agent", lambda: agents.research_agent.agent.agent)
    registry.register("knowledge_agent", lambda: agents.knowledge_agent.agent.agent)

    graph = build_graph(registry=registry).compile(checkpointer=MemorySaver())
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}
    final_state = graph.invoke(
        {
            "project_id": project["id"],
            "run_id": run_id,
            "source_type": project["source_type"],
            "source_url": project["source_url"],
            "events": [],
        },
        config=config,
    )

    assert len(upsert_calls) == 1
    assert upsert_calls[0]["source_id"] == run_id
    assert upsert_calls[0]["text"] == "full digest text here"
    assert upsert_calls[0]["project_id"] == project["id"]
    assert upsert_calls[0]["source_type"] == "github"
    assert upsert_calls[0]["source_url"] == "https://github.com/octocat/Hello-World"
    assert "source.ingested" in final_state["events"]


def test_script_node_passes_research_and_style_fields_to_real_agent(client, monkeypatch):
    """Phase 3.2-3.4 counterpart to the research_node/knowledge_node
    wiring regression tests above: script_node must forward
    research_summary/research_key_points (from research_node) and every
    style_* field the caller seeded into the initial state into the
    Script Agent's payload — nothing here should ever silently fall back
    to the empty-payload {} default a Stub Agent would tolerate (see
    _agent_event's docstring for the class of bug this guards against)."""

    resp = client.post(
        "/api/projects",
        json={"source_type": "github", "source_url": "https://github.com/octocat/Hello-World"},
    )
    project = resp.json()

    _mock_passing_score(monkeypatch)

    async def _fake_research_run(self, input):
        return AgentOutput(
            status="success",
            result={"summary": "A demo repo.", "key_points": ["one", "two"], "raw_text": "digest text"},
            next_event="research.completed",
        )

    monkeypatch.setattr("agents.research_agent.agent.ResearchAgent.run", _fake_research_run)

    received_inputs = []

    async def _fake_script_run(self, input):
        received_inputs.append(input)
        return AgentOutput(
            status="success",
            result={
                "hook": "h",
                "body": "b",
                "cta": "c",
                "caption": "cap",
                "title": "t",
                "hashtags": ["#tag"],
            },
            next_event="script.drafted",
        )

    monkeypatch.setattr("agents.script_agent.agent.ScriptAgent.run", _fake_script_run)
    # This test's script succeeds (real hook/body), so storyboard_node
    # would otherwise reach the real (unmocked) generate_storyboard() and
    # attempt a real LLM call — same reasoning as _mock_passing_score for
    # idea_scoring_node above; this test is about script_node's wiring,
    # not the Storyboard module itself (see workflows/tests/
    # test_storyboard.py for that).
    monkeypatch.setattr(
        "workflows.graph.generate_storyboard",
        lambda **kwargs: StoryboardResult(
            scenes=[{"order": 1, "description": "d", "duration": 1.0, "caption_cue": None, "visual_ref": None}]
        ),
    )

    registry = _all_stub_registry(exclude=frozenset({"research_agent", "script_agent"}))
    registry.register("research_agent", lambda: agents.research_agent.agent.agent)
    registry.register("script_agent", lambda: agents.script_agent.agent.agent)

    graph = build_graph(registry=registry).compile(checkpointer=MemorySaver())
    run_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": run_id}}
    final_state = graph.invoke(
        {
            "project_id": project["id"],
            "run_id": run_id,
            "source_type": project["source_type"],
            "source_url": project["source_url"],
            "events": [],
            "style_tone_notes": "energetic and fast",
            "style_opening_patterns": ["הי חברים תראו מה מצאתי"],
            "style_closing_patterns": ["אהבתם, רוצים עוד? תעקבו"],
            "style_avg_length_seconds": 37.5,
        },
        config=config,
    )

    assert len(received_inputs) == 1
    payload = received_inputs[0].payload
    assert payload["research_summary"] == "A demo repo."
    assert payload["research_key_points"] == ["one", "two"]
    assert payload["style_tone_notes"] == "energetic and fast"
    assert payload["style_opening_patterns"] == ["הי חברים תראו מה מצאתי"]
    assert payload["style_closing_patterns"] == ["אהבתם, רוצים עוד? תעקבו"]
    assert payload["style_avg_length_seconds"] == 37.5

    assert "script.drafted" in final_state["events"]
    assert final_state["script_hook"] == "h"
    assert final_state["script_hashtags"] == ["#tag"]
