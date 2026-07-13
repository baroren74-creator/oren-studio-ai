"""GET /api/projects — list all projects, most recent first. Added
after a live gap: apps/web's Projects page had no way back to a
project you'd already created, only the New Project form."""

from __future__ import annotations


def test_list_projects_empty(client):
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_projects_returns_created_projects(client):
    client.post("/api/projects", json={"source_type": "github", "source_url": "https://github.com/a/a"})
    client.post("/api/projects", json={"source_type": "youtube", "source_url": "https://youtube.com/b"})

    resp = client.get("/api/projects")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    source_types = {p["source_type"] for p in body}
    assert source_types == {"github", "youtube"}


def test_list_projects_requires_api_key(client):
    client.headers.pop("X-Studio-Api-Key")
    resp = client.get("/api/projects")
    assert resp.status_code == 401
