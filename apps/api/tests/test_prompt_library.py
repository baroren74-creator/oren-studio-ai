"""app.services.prompt_library + /api/prompt-library — Phase 3.5's CRUD
+ versioning Prompt Library (docs/database.md's prompt_library table,
docs/architecture.md section 9.5's "Diff between versions, not just an
update" requirement)."""

from __future__ import annotations

from app.services.prompt_library import (
    PromptNotFoundError,
    create_new_version,
    create_prompt,
    delete_prompt_family,
    get_prompt,
    get_prompt_history,
    list_current_prompts,
)


def test_create_starts_at_version_1_with_no_parent(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        entry = create_prompt(db, name="hook-generator", category="script", prompt_text="Write a hook about {topic}")
        assert entry.version == 1
        assert entry.parent_id is None
    finally:
        db.close()


def test_new_version_increments_and_sets_parent(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        v1 = create_prompt(db, name="hook-generator", prompt_text="v1 text")
        v2 = create_new_version(db, parent_id=v1.id, prompt_text="v2 text")

        assert v2.version == 2
        assert v2.parent_id == v1.id
        assert v2.name == "hook-generator"
    finally:
        db.close()


def test_new_version_inherits_category_when_not_overridden(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        v1 = create_prompt(db, name="p", category="script", prompt_text="a")
        v2 = create_new_version(db, parent_id=v1.id, prompt_text="b")
        assert v2.category == "script"
    finally:
        db.close()


def test_new_version_can_override_category(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        v1 = create_prompt(db, name="p", category="script", prompt_text="a")
        v2 = create_new_version(db, parent_id=v1.id, prompt_text="b", category="research")
        assert v2.category == "research"
    finally:
        db.close()


def test_new_version_raises_for_missing_parent(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        try:
            create_new_version(db, parent_id="does-not-exist", prompt_text="x")
            assert False, "expected PromptNotFoundError"
        except PromptNotFoundError:
            pass
    finally:
        db.close()


def test_list_current_returns_only_the_latest_version_per_name(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        v1 = create_prompt(db, name="hook-generator", prompt_text="v1")
        v2 = create_new_version(db, parent_id=v1.id, prompt_text="v2")
        create_prompt(db, name="caption-writer", prompt_text="only version")

        current = list_current_prompts(db)
        names = {c.name: c for c in current}

        assert len(current) == 2
        assert names["hook-generator"].id == v2.id
        assert names["hook-generator"].version == 2
        assert names["caption-writer"].version == 1
    finally:
        db.close()


def test_get_prompt_history_returns_full_chain_oldest_first(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        v1 = create_prompt(db, name="hook-generator", prompt_text="v1")
        v2 = create_new_version(db, parent_id=v1.id, prompt_text="v2")
        v3 = create_new_version(db, parent_id=v2.id, prompt_text="v3")

        history = get_prompt_history(db, v3.id)
        assert [h.id for h in history] == [v1.id, v2.id, v3.id]
        # asking from any version in the chain returns the same full history
        assert [h.id for h in get_prompt_history(db, v1.id)] == [v1.id, v2.id, v3.id]
    finally:
        db.close()


def test_get_prompt_history_raises_for_missing_id(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        try:
            get_prompt_history(db, "does-not-exist")
            assert False, "expected PromptNotFoundError"
        except PromptNotFoundError:
            pass
    finally:
        db.close()


def test_delete_prompt_family_removes_every_version(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        v1 = create_prompt(db, name="hook-generator", prompt_text="v1")
        v2 = create_new_version(db, parent_id=v1.id, prompt_text="v2")

        delete_prompt_family(db, v2.id)

        assert get_prompt(db, v1.id) is None
        assert get_prompt(db, v2.id) is None
    finally:
        db.close()


def test_delete_prompt_family_raises_for_missing_id(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        try:
            delete_prompt_family(db, "does-not-exist")
            assert False, "expected PromptNotFoundError"
        except PromptNotFoundError:
            pass
    finally:
        db.close()


def test_post_prompt_library_creates_a_row(client):
    resp = client.post(
        "/api/prompt-library",
        json={"name": "hook-generator", "category": "script", "prompt_text": "Write a hook about {topic}"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["version"] == 1
    assert body["parent_id"] is None


def test_get_prompt_library_lists_only_current_versions(client):
    created = client.post("/api/prompt-library", json={"name": "hook-generator", "prompt_text": "v1"}).json()
    client.post(f"/api/prompt-library/{created['id']}/versions", json={"prompt_text": "v2"})
    client.post("/api/prompt-library", json={"name": "caption-writer", "prompt_text": "only"})

    resp = client.get("/api/prompt-library")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    by_name = {p["name"]: p for p in body}
    assert by_name["hook-generator"]["version"] == 2
    assert by_name["hook-generator"]["prompt_text"] == "v2"


def test_get_single_prompt_returns_404_for_missing_id(client):
    resp = client.get("/api/prompt-library/does-not-exist")
    assert resp.status_code == 404


def test_post_versions_returns_404_for_missing_parent(client):
    resp = client.post("/api/prompt-library/does-not-exist/versions", json={"prompt_text": "x"})
    assert resp.status_code == 404


def test_get_history_returns_full_chain(client):
    created = client.post("/api/prompt-library", json={"name": "hook-generator", "prompt_text": "v1"}).json()
    v2 = client.post(f"/api/prompt-library/{created['id']}/versions", json={"prompt_text": "v2"}).json()

    resp = client.get(f"/api/prompt-library/{v2['id']}/history")
    assert resp.status_code == 200
    body = resp.json()
    assert [p["version"] for p in body] == [1, 2]


def test_delete_prompt_returns_204_and_removes_it(client):
    created = client.post("/api/prompt-library", json={"name": "hook-generator", "prompt_text": "v1"}).json()

    resp = client.delete(f"/api/prompt-library/{created['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/api/prompt-library/{created['id']}")
    assert resp.status_code == 404


def test_delete_prompt_returns_404_for_missing_id(client):
    resp = client.delete("/api/prompt-library/does-not-exist")
    assert resp.status_code == 404


def test_prompt_library_requires_api_key(client):
    client.headers.pop("X-Studio-Api-Key")
    resp = client.get("/api/prompt-library")
    assert resp.status_code == 401
