"""app.services.agent_runs — persisting workflows/graph.py's
StudioState.agent_costs as real agent_runs rows. See that module's
docstring for the gap this closes (real Agent cost was already
computed, never persisted; the Ops page always showed "No agent runs
yet")."""

from __future__ import annotations

from app.models import Project
from app.services.agent_runs import persist_agent_runs


def _make_project(db) -> Project:
    project = Project(title="Test project", status="draft", source_type="github", source_url="https://github.com/x/y")
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def test_persist_agent_runs_creates_one_row_per_entry(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        agent_costs = [
            {"agent_name": "research_agent", "status": "success", "tokens_used": 500, "cost_usd": 0.01, "provider": "anthropic"},
            {"agent_name": "idea_scoring", "status": "success", "tokens_used": 200, "cost_usd": 0.002, "provider": None},
        ]

        runs = persist_agent_runs(db, project_id=project.id, agent_costs=agent_costs)

        assert len(runs) == 2
        assert runs[0].agent_name == "research_agent"
        assert float(runs[0].cost_usd) == 0.01
        assert runs[0].tokens_used == 500
        assert runs[1].agent_name == "idea_scoring"
    finally:
        db.close()


def test_persist_agent_runs_empty_list_creates_nothing(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        runs = persist_agent_runs(db, project_id=project.id, agent_costs=[])
        assert runs == []
    finally:
        db.close()


def test_persist_agent_runs_defaults_missing_fields(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        runs = persist_agent_runs(db, project_id=project.id, agent_costs=[{}])
        assert runs[0].agent_name == "unknown"
        assert runs[0].status == "success"
        assert float(runs[0].cost_usd) == 0.0
        assert runs[0].tokens_used == 0
    finally:
        db.close()


def test_persisted_runs_are_visible_via_agent_runs_route(client):
    resp = client.post("/api/projects", json={"source_type": "github", "source_url": "https://github.com/x/y"})
    project_id = resp.json()["id"]

    from app.db import SessionLocal

    db = SessionLocal()
    try:
        persist_agent_runs(
            db,
            project_id=project_id,
            agent_costs=[{"agent_name": "research_agent", "status": "success", "tokens_used": 100, "cost_usd": 0.005}],
        )
    finally:
        db.close()

    resp = client.get("/api/agent-runs")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["agent_name"] == "research_agent"
    assert body[0]["cost_usd"] == 0.005
