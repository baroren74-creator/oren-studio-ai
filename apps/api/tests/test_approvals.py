"""app.services.approvals + /api/approvals + GET /api/projects/{id}/
approvals — Phase 3.6's Approval Gate #1. See
app.services.approvals's module docstring for why this is a standalone
DB-backed gate rather than a LangGraph interrupt()."""

from __future__ import annotations

from app.models import Project
from app.services.approvals import (
    ApprovalNotFoundError,
    create_approval,
    decide_approval,
    get_approval,
    list_approvals_for_project,
)


def _make_project(db) -> Project:
    project = Project(title="Test project", status="draft", source_type="github", source_url="https://github.com/x/y")
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def test_create_approval_starts_pending(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        approval = create_approval(db, project_id=project.id, stage="script")
        assert approval.status == "pending"
        assert approval.decided_at is None
        assert approval.notes is None
    finally:
        db.close()


def test_decide_approval_approve_sets_status_and_decided_at(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        approval = create_approval(db, project_id=project.id, stage="script")

        decided = decide_approval(db, approval.id, status="approved")
        assert decided.status == "approved"
        assert decided.decided_at is not None
    finally:
        db.close()


def test_decide_approval_reject(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        approval = create_approval(db, project_id=project.id, stage="script")

        decided = decide_approval(db, approval.id, status="rejected")
        assert decided.status == "rejected"
    finally:
        db.close()


def test_decide_approval_request_edit_sets_notes(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project = _make_project(db)
        approval = create_approval(db, project_id=project.id, stage="script")

        decided = decide_approval(db, approval.id, status="edited", notes="make the hook punchier")
        assert decided.status == "edited"
        assert decided.notes == "make the hook punchier"
    finally:
        db.close()


def test_decide_approval_raises_for_missing_id(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        try:
            decide_approval(db, "does-not-exist", status="approved")
            assert False, "expected ApprovalNotFoundError"
        except ApprovalNotFoundError:
            pass
    finally:
        db.close()


def test_list_approvals_for_project_scopes_correctly(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        project_a = _make_project(db)
        project_b = _make_project(db)
        create_approval(db, project_id=project_a.id, stage="script")
        create_approval(db, project_id=project_b.id, stage="script")

        approvals_a = list_approvals_for_project(db, project_a.id)
        assert len(approvals_a) == 1
        assert approvals_a[0].project_id == project_a.id
    finally:
        db.close()


def test_get_approval_returns_none_for_missing_id(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        assert get_approval(db, "does-not-exist") is None
    finally:
        db.close()


def test_post_approve_route(client):
    resp = client.post("/api/projects", json={"source_type": "github", "source_url": "https://github.com/x/y"})
    project_id = resp.json()["id"]

    from app.db import SessionLocal

    db = SessionLocal()
    try:
        approval = create_approval(db, project_id=project_id, stage="script")
    finally:
        db.close()

    resp = client.post(f"/api/approvals/{approval.id}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"


def test_post_reject_route(client):
    resp = client.post("/api/projects", json={"source_type": "github", "source_url": "https://github.com/x/y"})
    project_id = resp.json()["id"]

    from app.db import SessionLocal

    db = SessionLocal()
    try:
        approval = create_approval(db, project_id=project_id, stage="script")
    finally:
        db.close()

    resp = client.post(f"/api/approvals/{approval.id}/reject")
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_post_request_edit_route_carries_notes(client):
    resp = client.post("/api/projects", json={"source_type": "github", "source_url": "https://github.com/x/y"})
    project_id = resp.json()["id"]

    from app.db import SessionLocal

    db = SessionLocal()
    try:
        approval = create_approval(db, project_id=project_id, stage="script")
    finally:
        db.close()

    resp = client.post(f"/api/approvals/{approval.id}/request-edit", json={"notes": "shorten the hook"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "edited"
    assert body["notes"] == "shorten the hook"


def test_approve_route_returns_404_for_missing_id(client):
    resp = client.post("/api/approvals/does-not-exist/approve")
    assert resp.status_code == 404


def test_get_project_approvals_route(client):
    resp = client.post("/api/projects", json={"source_type": "github", "source_url": "https://github.com/x/y"})
    project_id = resp.json()["id"]

    from app.db import SessionLocal

    db = SessionLocal()
    try:
        create_approval(db, project_id=project_id, stage="script")
    finally:
        db.close()

    resp = client.get(f"/api/projects/{project_id}/approvals")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["stage"] == "script"
    assert body[0]["status"] == "pending"


def test_get_project_approvals_route_404_for_missing_project(client):
    resp = client.get("/api/projects/does-not-exist/approvals")
    assert resp.status_code == 404


def test_approvals_require_api_key(client):
    client.headers.pop("X-Studio-Api-Key")
    resp = client.post("/api/approvals/does-not-exist/approve")
    assert resp.status_code == 401
