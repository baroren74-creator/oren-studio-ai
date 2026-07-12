"""memory.store.MemoryStore, against a real qdrant-client in embedded
local mode (QdrantClient(path=...), no server needed — verified working
standalone before this module was written). embed_texts (the call into
providers/llm -> LiteLLM -> Voyage AI) is mocked: no API key exists in
this sandbox for any provider, same reasoning as
providers/llm/tests/test_client.py's module docstring.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from memory.store import MemoryStore

VECTOR_SIZE = 4


def _fake_embed(vector_map):
    def _embed(texts, model=None):
        return SimpleNamespace(vectors=[vector_map[t] for t in texts])

    return _embed


@pytest.fixture()
def store(tmp_path):
    return MemoryStore(path=str(tmp_path / "qdrant_test"), vector_size=VECTOR_SIZE)


def test_requires_either_path_or_url():
    with pytest.raises(ValueError, match="requires either"):
        MemoryStore()


def test_rejects_both_path_and_url():
    with pytest.raises(ValueError, match="only one of"):
        MemoryStore(path="/tmp/x", url="http://localhost:6333")


def test_upsert_empty_text_stores_nothing(store):
    with patch("memory.store.embed_texts", _fake_embed({})):
        count = store.upsert_document(
            source_id="src-empty", text="   ", project_id="proj-1", source_type="github"
        )
    assert count == 0


def test_upsert_and_search_round_trip(store):
    vector_map = {
        "alpha content": [1.0, 0.0, 0.0, 0.0],
        "find alpha": [1.0, 0.0, 0.0, 0.0],
    }
    with patch("memory.store.embed_texts", _fake_embed(vector_map)):
        count = store.upsert_document(
            source_id="src-a",
            text="alpha content",
            project_id="proj-1",
            source_type="github",
            source_url="https://github.com/example/repo",
        )
        assert count == 1

        results = store.search("find alpha", limit=5)

    assert len(results) == 1
    assert results[0].text == "alpha content"
    assert results[0].payload["source_id"] == "src-a"
    assert results[0].payload["project_id"] == "proj-1"
    assert results[0].payload["chunk_index"] == 0
    assert results[0].score == pytest.approx(1.0, abs=1e-4)


def test_search_filters_by_project_id(store):
    vector_map = {
        "alpha content": [1.0, 0.0, 0.0, 0.0],
        "beta content": [0.0, 1.0, 0.0, 0.0],
        "find alpha": [1.0, 0.0, 0.0, 0.0],
    }
    with patch("memory.store.embed_texts", _fake_embed(vector_map)):
        store.upsert_document(source_id="src-a", text="alpha content", project_id="proj-1", source_type="github")
        store.upsert_document(source_id="src-b", text="beta content", project_id="proj-2", source_type="youtube")

        unfiltered = store.search("find alpha", limit=5)
        filtered_to_proj2 = store.search("find alpha", project_id="proj-2", limit=5)

    assert {r.payload["source_id"] for r in unfiltered} == {"src-a", "src-b"}
    assert unfiltered[0].payload["source_id"] == "src-a"  # closer match ranks first

    assert len(filtered_to_proj2) == 1
    assert filtered_to_proj2[0].payload["source_id"] == "src-b"  # only proj-2 point, despite lower similarity


def test_reupserting_same_source_id_overwrites_not_duplicates(store):
    vector_map = {"alpha content": [1.0, 0.0, 0.0, 0.0]}
    with patch("memory.store.embed_texts", _fake_embed(vector_map)):
        store.upsert_document(source_id="src-a", text="alpha content", project_id="proj-1", source_type="github")
        first_count = store._client.count(store._collection, exact=True).count

        store.upsert_document(source_id="src-a", text="alpha content", project_id="proj-1", source_type="github")
        second_count = store._client.count(store._collection, exact=True).count

    assert first_count == 1
    assert second_count == 1  # deterministic point ID (ADR-008) means this overwrites, not duplicates


def test_delete_source_removes_its_points(store):
    vector_map = {"alpha content": [1.0, 0.0, 0.0, 0.0]}
    with patch("memory.store.embed_texts", _fake_embed(vector_map)):
        store.upsert_document(source_id="src-a", text="alpha content", project_id="proj-1", source_type="github")
        assert store._client.count(store._collection, exact=True).count == 1

        store.delete_source("src-a")

    assert store._client.count(store._collection, exact=True).count == 0
