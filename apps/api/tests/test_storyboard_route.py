"""GET /api/projects/{id}/storyboard — docs/roadmap.md Phase 3.8.
"""

from __future__ import annotations


def test_get_storyboard_route_returns_scenes(client):
    from app.db import SessionLocal

    from app.models import Script
    from app.services.storyboard import persist_storyboard

    resp = client.post("/api/projects", json={"source_type": "github", "source_url": "https://github.com/x/y"})
    project = resp.json()

    db = SessionLocal()
    try:
        script = Script(project_id=project["id"], hook="h", body="b", cta="c", caption="cap", title="t", hashtags=[])
        db.add(script)
        db.commit()
        db.refresh(script)
        # Capture before persist_storyboard's own commit() expires every
        # instrumented attribute on every object still attached to this
        # session — script.id would otherwise raise DetachedInstanceError
        # once accessed after db.close() below.
        script_id = script.id
        persist_storyboard(
            db,
            script_id=script_id,
            scenes=[{"order": 1, "description": "d", "duration": 2.5, "caption_cue": "cue", "visual_ref": None}],
        )
    finally:
        db.close()

    resp = client.get(f"/api/projects/{project['id']}/storyboard")

    assert resp.status_code == 200
    body = resp.json()
    assert body["script_id"] == script_id
    assert len(body["scenes"]) == 1
    assert body["scenes"][0]["description"] == "d"


def test_get_storyboard_route_404_when_none_exists(client):
    resp = client.post("/api/projects", json={"source_type": "github", "source_url": "https://github.com/x/y"})
    project = resp.json()

    resp = client.get(f"/api/projects/{project['id']}/storyboard")

    assert resp.status_code == 404


def test_get_storyboard_route_404_for_missing_project(client):
    resp = client.get("/api/projects/does-not-exist/storyboard")
    assert resp.status_code == 404


def test_get_storyboard_route_requires_api_key(client):
    client.headers.pop("X-Studio-Api-Key")
    resp = client.get("/api/projects/does-not-exist/storyboard")
    assert resp.status_code == 401
