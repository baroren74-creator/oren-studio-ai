"""app/services/orchestrator.py — the first real caller of
workflows/graph.py's build_graph() outside of a test. See that module's
docstring for why this is a deliberate v0 (synchronous, in-process,
MemorySaver-checkpointed) shortcut, not the eventual services/
orchestrator-worker.

Real Agent .run methods are mocked (same "patch where it's used"
convention as apps/api/tests/test_smoke_e2e.py) — no real network/LLM
calls in this suite. A live, unmocked smoke check (real gitingest fetch,
graceful failure with no API key configured) was run manually against a
throwaway SQLite DB via `uvicorn` during development; not part of the
automated suite since it depends on github.com being reachable.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import agents.research_agent.agent
import agents.script_agent.agent
from core.registry import AgentRegistry
from core.schemas.agent import AgentOutput, CostInfo
from core.stub_agent import StubAgent

from app.models import AgentRun, Approval, Project, ResearchNote, Script, Storyboard
from app.services.orchestrator import ProjectNotFoundError, run_project
from app.services.style_profile import create_style_profile
from workflows.storyboard import StoryboardResult

_STUB_NEXT_EVENTS = {
    "knowledge_agent": "source.ingested",
    "recording_agent": "recording.completed",
    "video_agent": "video.rendered",
    "voice_agent": "voice.completed",
    "publishing_agent": "final_review.requested",
}


def _make_project(db, **kwargs) -> Project:
    defaults = dict(title="Test project", status="draft", source_type="github", source_url="https://github.com/x/y")
    defaults.update(kwargs)
    project = Project(**defaults)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _registry_with_real_research_and_script() -> AgentRegistry:
    """Every node stubbed except research_agent/script_agent, which use
    the real modules (their .run methods get monkeypatched per-test) —
    mirrors apps/api/tests/test_smoke_e2e.py's `_all_stub_registry`."""
    registry = AgentRegistry()
    for name, next_event in _STUB_NEXT_EVENTS.items():
        stub = StubAgent(name=name, next_event=next_event)
        registry.register(name, lambda stub=stub: stub)
    registry.register("research_agent", lambda: agents.research_agent.agent.agent)
    registry.register("script_agent", lambda: agents.script_agent.agent.agent)
    return registry


def test_run_project_raises_for_missing_project(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        try:
            run_project(db, "does-not-exist")
            assert False, "expected ProjectNotFoundError"
        except ProjectNotFoundError:
            pass
    finally:
        db.close()


def test_run_project_persists_research_and_script(client, monkeypatch):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)

        monkeypatch.setattr(
            "agents.research_agent.agent.ResearchAgent.run",
            AsyncMock(
                return_value=AgentOutput(
                    status="success",
                    result={"summary": "A demo repo.", "key_points": ["one", "two"], "raw_text": "digest"},
                    next_event="research.completed",
                    cost=CostInfo(tokens_used=500, cost_usd=0.01, provider="anthropic"),
                )
            ),
        )
        monkeypatch.setattr(
            "agents.script_agent.agent.ScriptAgent.run",
            AsyncMock(
                return_value=AgentOutput(
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
                    cost=CostInfo(tokens_used=300, cost_usd=0.02, provider="anthropic"),
                )
            ),
        )
        monkeypatch.setattr("workflows.graph.score_idea", lambda **kwargs: __import__("types").SimpleNamespace(
            total=100.0, cost_usd=0.001, tokens_used=150, breakdown={"novelty": 25, "audience_relevance": 25, "source_reliability": 25, "visual_potential": 25}
        ))
        # Phase 3.7: storyboard_node calls this directly (not a
        # registered Agent — see workflows/storyboard.py's docstring),
        # so it's mocked the same way score_idea is above, not via the
        # registry.
        monkeypatch.setattr(
            "workflows.graph.generate_storyboard",
            lambda **kwargs: StoryboardResult(
                scenes=[
                    {"order": 1, "description": "Terminal running install.", "duration": 4.5, "caption_cue": "npm install", "visual_ref": None},
                    {"order": 2, "description": "App running in browser.", "duration": 6.0, "caption_cue": None, "visual_ref": None},
                ],
                generated_by="storyboard@0.1.0:test",
                cost_usd=0.003,
                tokens_used=200,
            ),
        )

        result = run_project(db, project.id, registry=_registry_with_real_research_and_script())

        assert result["rejected"] is False
        assert result["idea_score"] == 100.0
        assert result["script"]["hook"] == "h"
        assert result["research_note_id"] is not None
        assert result["script_id"] is not None
        assert result["approval_id"] is not None
        assert result["storyboard_id"] is not None
        assert len(result["storyboard_scenes"]) == 2
        assert result["storyboard_scenes"][0]["description"] == "Terminal running install."

        note = db.get(ResearchNote, result["research_note_id"])
        assert note.summary == "A demo repo."
        assert note.interest_score == 100.0

        script = db.get(Script, result["script_id"])
        assert script.hook == "h"
        assert script.hashtags == ["#tag"]

        # Phase 3.6: persisting a script always creates a pending
        # Approval Gate #1 row alongside it (app.services.orchestrator).
        approval = db.get(Approval, result["approval_id"])
        assert approval.project_id == project.id
        assert approval.stage == "script"
        assert approval.status == "pending"

        # Phase 3.7: a storyboard row is linked to the script it was
        # generated from.
        storyboard = db.get(Storyboard, result["storyboard_id"])
        assert storyboard.script_id == script.id
        assert len(storyboard.scenes) == 2

        # Cost tracking: every real Agent/scoring call in this run
        # (research_agent, idea_scoring, script_agent, storyboard — the
        # stubbed knowledge/recording/video/voice/publishing nodes
        # contribute $0 rows too) should now be a real agent_runs row.
        assert abs(result["total_cost_usd"] - 0.034) < 1e-9
        runs = db.query(AgentRun).filter(AgentRun.project_id == project.id).all()
        run_names = {r.agent_name for r in runs}
        assert "research_agent" in run_names
        assert "idea_scoring" in run_names
        assert "script_agent" in run_names
        assert "storyboard" in run_names
        research_run = next(r for r in runs if r.agent_name == "research_agent")
        assert float(research_run.cost_usd) == 0.01
        assert research_run.tokens_used == 500
    finally:
        db.close()


def test_run_project_rejected_idea_persists_research_but_no_script(client, monkeypatch):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)

        monkeypatch.setattr(
            "agents.research_agent.agent.ResearchAgent.run",
            AsyncMock(
                return_value=AgentOutput(
                    status="success",
                    result={"summary": "A demo repo.", "key_points": [], "raw_text": "digest"},
                    next_event="research.completed",
                )
            ),
        )
        monkeypatch.setattr("workflows.graph.score_idea", lambda **kwargs: __import__("types").SimpleNamespace(
            total=10.0, cost_usd=0.0, tokens_used=0, breakdown={"novelty": 5, "audience_relevance": 5, "source_reliability": 0, "visual_potential": 0}
        ))

        result = run_project(db, project.id, registry=_registry_with_real_research_and_script())

        assert result["rejected"] is True
        assert result["idea_score"] == 10.0
        assert result["script"] is None
        assert result["script_id"] is None
        assert result["approval_id"] is None
        assert result["research_note_id"] is not None
    finally:
        db.close()


def test_run_project_seeds_style_profile_into_script_payload(client, monkeypatch):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        profile = create_style_profile(
            db, tone_notes="energetic", opening_patterns=["הי חברים"], avg_length_seconds=37.5
        )

        monkeypatch.setattr(
            "agents.research_agent.agent.ResearchAgent.run",
            AsyncMock(
                return_value=AgentOutput(
                    status="success", result={"summary": "A demo repo.", "key_points": []}, next_event="research.completed"
                )
            ),
        )
        monkeypatch.setattr("workflows.graph.score_idea", lambda **kwargs: __import__("types").SimpleNamespace(
            total=100.0, cost_usd=0.0, tokens_used=0, breakdown={}
        ))
        # Same reasoning as test_run_project_persists_research_and_script:
        # this test's script succeeds, so storyboard_node would otherwise
        # reach the real (unmocked) generate_storyboard() and attempt a
        # real LLM call.
        monkeypatch.setattr(
            "workflows.graph.generate_storyboard",
            lambda **kwargs: StoryboardResult(scenes=[{"order": 1, "description": "d", "duration": 1.0, "caption_cue": None, "visual_ref": None}]),
        )

        received = []

        async def _fake_script_run(self, input):
            received.append(input)
            return AgentOutput(
                status="success",
                result={"hook": "h", "body": "b", "cta": "c", "caption": "cap", "title": "t", "hashtags": []},
                next_event="script.drafted",
            )

        monkeypatch.setattr("agents.script_agent.agent.ScriptAgent.run", _fake_script_run)

        result = run_project(db, project.id, registry=_registry_with_real_research_and_script())

        assert len(received) == 1
        assert received[0].payload["style_tone_notes"] == "energetic"
        assert received[0].payload["style_opening_patterns"] == ["הי חברים"]
        assert received[0].payload["style_avg_length_seconds"] == 37.5

        script = db.get(Script, result["script_id"])
        assert script.style_profile_id == profile.id
    finally:
        db.close()


def test_run_route_returns_200_and_persists(client, monkeypatch):
    resp = client.post(
        "/api/projects", json={"source_type": "github", "source_url": "https://github.com/x/y"}
    )
    project = resp.json()

    monkeypatch.setattr(
        "agents.research_agent.agent.ResearchAgent.run",
        AsyncMock(
            return_value=AgentOutput(
                status="success", result={"summary": "A demo repo.", "key_points": []}, next_event="research.completed"
            )
        ),
    )
    monkeypatch.setattr(
        "agents.script_agent.agent.ScriptAgent.run",
        AsyncMock(
            return_value=AgentOutput(
                status="success",
                result={"hook": "h", "body": "b", "cta": "c", "caption": "cap", "title": "t", "hashtags": []},
                next_event="script.drafted",
            )
        ),
    )
    monkeypatch.setattr("workflows.graph.score_idea", lambda **kwargs: __import__("types").SimpleNamespace(
        total=100.0, cost_usd=0.0, tokens_used=0, breakdown={}
    ))
    monkeypatch.setattr(
        "workflows.graph.generate_storyboard",
        lambda **kwargs: StoryboardResult(scenes=[{"order": 1, "description": "d", "duration": 1.0, "caption_cue": None, "visual_ref": None}]),
    )
    # The route uses the real default_registry, which agents/*/agent.py
    # modules populate as an import side-effect when apps.api.app.main
    # loads (see that module's comment) — the client fixture already
    # imports app.main, so the registry is populated by the time this
    # request runs. This deliberately does NOT swap in an isolated
    # registry, unlike the direct-service tests above: it's exercising
    # exactly what a real request would hit.
    resp = client.post(f"/api/projects/{project['id']}/run")

    assert resp.status_code == 200
    body = resp.json()
    assert body["idea_score"] == 100.0
    assert body["script"]["hook"] == "h"
    assert body["approval_id"] is not None


def test_run_route_returns_404_for_missing_project(client):
    resp = client.post("/api/projects/does-not-exist/run")
    assert resp.status_code == 404
