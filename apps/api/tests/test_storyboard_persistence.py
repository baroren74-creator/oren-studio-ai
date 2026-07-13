"""app/services/storyboard.py — docs/roadmap.md Phase 3.7: persist a
successful Storyboard run into `storyboards` (docs/database.md).
"""

from __future__ import annotations

from app.models import Project, Script, Storyboard
from app.services.storyboard import persist_storyboard


def _make_script(db) -> Script:
    project = Project(title="Test project", status="draft", source_type="github", source_url="https://github.com/x/y")
    db.add(project)
    db.commit()
    db.refresh(project)

    script = Script(project_id=project.id, hook="h", body="b", cta="c", caption="cap", title="t", hashtags=[])
    db.add(script)
    db.commit()
    db.refresh(script)
    return script


def test_scenes_are_persisted(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        script = _make_script(db)
        scenes = [
            {"order": 1, "description": "Terminal running install.", "duration": 4.5, "caption_cue": "npm install", "visual_ref": None},
            {"order": 2, "description": "App running in browser.", "duration": 6.0, "caption_cue": None, "visual_ref": None},
        ]

        storyboard = persist_storyboard(db, script_id=script.id, scenes=scenes)

        assert storyboard is not None
        assert storyboard.script_id == script.id
        assert storyboard.scenes == scenes

        row = db.get(Storyboard, storyboard.id)
        assert row is not None
        assert row.script_id == script.id
    finally:
        db.close()


def test_empty_scenes_writes_nothing(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        script = _make_script(db)

        result = persist_storyboard(db, script_id=script.id, scenes=[])

        assert result is None
        assert db.query(Storyboard).count() == 0
    finally:
        db.close()


def test_none_scenes_writes_nothing(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        script = _make_script(db)

        result = persist_storyboard(db, script_id=script.id, scenes=None)

        assert result is None
        assert db.query(Storyboard).count() == 0
    finally:
        db.close()
