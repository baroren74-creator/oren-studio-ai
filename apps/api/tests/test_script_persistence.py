"""app/services/script.py — docs/roadmap.md Phase 3.2-3.4: persist a
successful Script Agent run into `scripts` (docs/database.md).
"""

from __future__ import annotations

from core.schemas.agent import AgentOutput, CostInfo

from app.models import Project, Script
from app.services.script import persist_script
from app.services.style_profile import create_style_profile


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
                "hook": "ידעתם שיש כזה דבר?",
                "body": "תיאור הכלי כאן.",
                "cta": "אהבתם, רוצים עוד? תעקבו",
                "caption": "כיתוב לפוסט",
                "title": "כותרת קצרה",
                "hashtags": ["#opensource", "#devtools"],
            },
            cost=CostInfo(tokens_used=350, cost_usd=0.004, provider="anthropic/claude-3-5-sonnet-20241022"),
            next_event="script.drafted",
        )

        script = persist_script(db, project_id=project.id, output=output)

        assert script is not None
        assert script.hook == "ידעתם שיש כזה דבר?"
        assert script.hashtags == ["#opensource", "#devtools"]
        assert script.style_profile_id is None

        row = db.get(Script, script.id)
        assert row is not None
        assert row.project_id == project.id
    finally:
        db.close()


def test_style_profile_id_is_linked_when_provided(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        profile = create_style_profile(db, tone_notes="energetic")
        output = AgentOutput(
            status="success",
            result={"hook": "h", "body": "b", "cta": "c", "caption": "cap", "title": "t", "hashtags": []},
        )

        script = persist_script(db, project_id=project.id, output=output, style_profile_id=profile.id)

        assert script.style_profile_id == profile.id
    finally:
        db.close()


def test_skipped_output_writes_nothing(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        output = AgentOutput(status="skipped", result={"reason": "no research_summary"}, next_event=None)

        result = persist_script(db, project_id=project.id, output=output)

        assert result is None
        assert db.query(Script).count() == 0
    finally:
        db.close()


def test_failed_output_writes_nothing(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        output = AgentOutput(status="failed", result={"reason": "LLM call failed"})

        result = persist_script(db, project_id=project.id, output=output)

        assert result is None
        assert db.query(Script).count() == 0
    finally:
        db.close()
