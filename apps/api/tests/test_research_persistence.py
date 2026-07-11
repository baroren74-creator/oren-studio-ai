"""app/services/research.py — docs/roadmap.md Phase 2.3.1: persist a
successful Research Agent run into research_notes (docs/database.md).
"""

from __future__ import annotations

from core.schemas.agent import AgentOutput, CostInfo

from app.models import Project, ResearchNote
from app.services.research import persist_research_note


def _make_project(db) -> Project:
    project = Project(title="Test project", status="draft", source_type="github", source_url="https://github.com/x/y")
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def test_successful_output_is_persisted(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        output = AgentOutput(
            status="success",
            result={
                "source_url": "https://github.com/x/y",
                "repo_summary": "Repository: x/y\n",
                "summary": "A small demo repo.",
                "key_points": ["point one", "point two"],
            },
            cost=CostInfo(tokens_used=150, cost_usd=0.002, provider="anthropic/claude-3-5-sonnet-20241022"),
            next_event="research.completed",
        )

        note = persist_research_note(
            db, project_id=project.id, output=output, agent_name="research_agent", agent_version="0.2.0"
        )

        assert note is not None
        assert note.summary == "A small demo repo."
        assert note.key_points == ["point one", "point two"]
        assert note.scored_by == "research_agent@0.2.0"
        assert note.interest_score is None  # Phase 2.6 fills this in later

        # actually landed in the DB, not just returned in memory
        rows = db.query(ResearchNote).filter(ResearchNote.project_id == project.id).all()
        assert len(rows) == 1
        assert rows[0].id == note.id
    finally:
        db.close()


def test_skipped_output_writes_nothing(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        output = AgentOutput(status="skipped", result={"reason": "source_type 'youtube' not implemented yet"})

        note = persist_research_note(
            db, project_id=project.id, output=output, agent_name="research_agent", agent_version="0.2.0"
        )

        assert note is None
        rows = db.query(ResearchNote).filter(ResearchNote.project_id == project.id).all()
        assert rows == []
    finally:
        db.close()


def test_failed_output_writes_nothing(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        output = AgentOutput(status="failed", result={"reason": "Missing Anthropic API Key"})

        note = persist_research_note(
            db, project_id=project.id, output=output, agent_name="research_agent", agent_version="0.2.0"
        )

        assert note is None
        rows = db.query(ResearchNote).filter(ResearchNote.project_id == project.id).all()
        assert rows == []
    finally:
        db.close()
