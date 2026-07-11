"""Shared pytest fixtures. A fresh SQLite DB per test session — the same
models/migrations run against Postgres in production (docs/decisions.md
ADR-008 doesn't change based on which engine is behind DATABASE_URL)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = API_ROOT.parents[1]
for p in (API_ROOT, REPO_ROOT / "packages" / "core", REPO_ROOT / "workflows", REPO_ROOT):
    sys.path.insert(0, str(p))

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_oren_studio.db")
os.environ.setdefault("STUDIO_API_KEY", "test-key-123")


@pytest.fixture()
def db_path(tmp_path):
    path = tmp_path / "test_oren_studio.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{path}"
    return path


@pytest.fixture()
def client(db_path):
    # Re-import app fresh per test so it picks up the per-test DB URL —
    # simplest way to get isolation without a full DI rewrite in this
    # Phase 1 skeleton.
    for mod in list(sys.modules):
        if mod.startswith("app"):
            del sys.modules[mod]

    from app.db import Base, engine
    from app.main import app

    Base.metadata.create_all(bind=engine)

    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        c.headers.update({"X-Studio-Api-Key": "test-key-123"})
        yield c
