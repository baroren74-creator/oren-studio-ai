"""GET /api/knowledge/search — docs/api.md, docs/roadmap.md Phase 2.9.

search_knowledge (the call into packages/memory -> qdrant-client ->
LiteLLM -> Voyage AI) is patched at the router's own imported name
(app.routers.knowledge.search_knowledge — "patch where it's used, not
where it's defined") rather than exercised for real: no Qdrant server
and no embedding API key exist in this sandbox, same reasoning as every
other test in this repo that touches an external provider.
"""

from __future__ import annotations

from unittest.mock import patch

from memory import MemoryStoreError


def test_search_returns_results_from_the_store(client):
    fake_results = [
        {"text": "chunk one", "score": 0.91, "payload": {"source_id": "run-1", "project_id": "proj-1"}},
        {"text": "chunk two", "score": 0.80, "payload": {"source_id": "run-2", "project_id": "proj-1"}},
    ]
    with patch("app.routers.knowledge.search_knowledge", return_value=fake_results) as mock_search:
        resp = client.get("/api/knowledge/search", params={"q": "hello world"})

    assert resp.status_code == 200
    mock_search.assert_called_once_with("hello world", project_id=None, limit=5)
    assert resp.json() == fake_results


def test_search_passes_project_id_and_limit_through(client):
    with patch("app.routers.knowledge.search_knowledge", return_value=[]) as mock_search:
        resp = client.get(
            "/api/knowledge/search", params={"q": "hello", "project_id": "proj-9", "limit": 10}
        )

    assert resp.status_code == 200
    mock_search.assert_called_once_with("hello", project_id="proj-9", limit=10)


def test_search_requires_q_param(client):
    resp = client.get("/api/knowledge/search")
    assert resp.status_code == 422


def test_search_returns_503_when_store_unavailable(client):
    with patch(
        "app.routers.knowledge.search_knowledge", side_effect=MemoryStoreError("qdrant connection refused")
    ):
        resp = client.get("/api/knowledge/search", params={"q": "hello"})

    assert resp.status_code == 503
    assert "qdrant connection refused" in resp.json()["detail"]


def test_search_requires_api_key(client):
    client.headers.pop("X-Studio-Api-Key")
    resp = client.get("/api/knowledge/search", params={"q": "hello"})
    assert resp.status_code == 401
