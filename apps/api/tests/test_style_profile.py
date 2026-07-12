"""app.services.style_profile + POST/GET /api/style-profile — Phase 3.1's
manual one-time questionnaire (docs/database.md's style_profile table,
docs/agents.md's Script Agent section)."""

from __future__ import annotations

from app.services.style_profile import create_style_profile, get_current_style_profile


def test_get_current_returns_none_when_no_profile_exists(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        assert get_current_style_profile(db) is None
    finally:
        db.close()


def test_create_starts_at_version_1(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        profile = create_style_profile(db, tone_notes="energetic")
        assert profile.version == 1
    finally:
        db.close()


def test_create_increments_version_on_each_call(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        create_style_profile(db, tone_notes="v1")
        second = create_style_profile(db, tone_notes="v2")
        third = create_style_profile(db, tone_notes="v3")

        assert second.version == 2
        assert third.version == 3
    finally:
        db.close()


def test_get_current_returns_highest_version(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        create_style_profile(db, tone_notes="old")
        latest = create_style_profile(db, tone_notes="new")

        current = get_current_style_profile(db)
        assert current.id == latest.id
        assert current.tone_notes == "new"
    finally:
        db.close()


def test_create_defaults_pattern_lists_to_empty(client):
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        profile = create_style_profile(db)
        assert profile.opening_patterns == []
        assert profile.closing_patterns == []
    finally:
        db.close()


def test_post_style_profile_creates_a_row(client):
    resp = client.post(
        "/api/style-profile",
        json={
            "tone_notes": "energetic and fast, professional, friendly",
            "opening_patterns": ["הי חברים תראו מה מצאתי", "ידעתם שיש כזה דבר?"],
            "closing_patterns": ["אהבתם, רוצים עוד? תעקבו", "ללינק כתבו לי בתגובות"],
            "avg_length_seconds": 37.5,
        },
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["version"] == 1
    assert body["opening_patterns"] == ["הי חברים תראו מה מצאתי", "ידעתם שיש כזה דבר?"]


def test_get_current_returns_404_when_none_created(client):
    resp = client.get("/api/style-profile/current")
    assert resp.status_code == 404


def test_get_current_returns_latest_after_two_posts(client):
    client.post("/api/style-profile", json={"tone_notes": "first pass"})
    client.post("/api/style-profile", json={"tone_notes": "second pass"})

    resp = client.get("/api/style-profile/current")
    assert resp.status_code == 200
    assert resp.json()["version"] == 2
    assert resp.json()["tone_notes"] == "second pass"


def test_style_profile_requires_api_key(client):
    client.headers.pop("X-Studio-Api-Key")
    resp = client.get("/api/style-profile/current")
    assert resp.status_code == 401
