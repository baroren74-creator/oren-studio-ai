"""agents/knowledge_agent/agent.py — docs/roadmap.md Phase 2.8 (Knowledge
Agent v1: chunk + embed + upsert into Qdrant via packages/memory).

_build_store is patched to return a fake in-memory-recording store
rather than touching real Qdrant/embeddings — the same "patch the
module-level dependency, not the network" convention as
agents/research_agent/tests/test_agent.py and
agents/trend_agent/tests/test_agent.py.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

import agents.knowledge_agent.agent as ka_module
from core.schemas.agent import AgentInput
from llm_provider import LLMError
from memory import MemoryStoreError

AGENT = ka_module.agent


class _FakeStore:
    def __init__(self, *, chunks_to_return: int = 3, raises: Exception | None = None):
        self.chunks_to_return = chunks_to_return
        self.raises = raises
        self.calls: list[dict] = []

    def upsert_document(self, **kwargs):
        self.calls.append(kwargs)
        if self.raises is not None:
            raise self.raises
        return self.chunks_to_return


def _input(payload: dict | None = None) -> AgentInput:
    return AgentInput(run_id=uuid.uuid4(), project_id=uuid.uuid4(), payload=payload or {})


@pytest.mark.asyncio
async def test_run_indexes_text_and_returns_chunk_count():
    fake_store = _FakeStore(chunks_to_return=4)
    with patch.object(ka_module, "_build_store", return_value=fake_store):
        out = await AGENT.run(
            _input(
                {
                    "source_id": "run-123",
                    "text": "some digest content " * 50,
                    "project_id": "proj-1",
                    "source_type": "github",
                    "source_url": "https://github.com/example/repo",
                }
            )
        )

    assert out.status == "success"
    assert out.next_event == "source.ingested"
    assert out.result == {"source_id": "run-123", "chunks_indexed": 4}

    assert len(fake_store.calls) == 1
    call = fake_store.calls[0]
    assert call["source_id"] == "run-123"
    assert call["project_id"] == "proj-1"
    assert call["source_type"] == "github"
    assert call["source_url"] == "https://github.com/example/repo"


@pytest.mark.asyncio
async def test_run_skips_when_text_is_missing():
    with patch.object(ka_module, "_build_store") as mock_build_store:
        out = await AGENT.run(_input({"source_id": "run-123"}))

    mock_build_store.assert_not_called()
    assert out.status == "skipped"
    assert out.next_event is None
    assert "no text to index" in out.result["reason"]


@pytest.mark.asyncio
async def test_run_skips_when_text_is_blank():
    with patch.object(ka_module, "_build_store") as mock_build_store:
        out = await AGENT.run(_input({"source_id": "run-123", "text": "   \n  "}))

    mock_build_store.assert_not_called()
    assert out.status == "skipped"


@pytest.mark.asyncio
async def test_run_fails_cleanly_when_source_id_missing():
    with patch.object(ka_module, "_build_store") as mock_build_store:
        out = await AGENT.run(_input({"text": "some content"}))

    mock_build_store.assert_not_called()
    assert out.status == "failed"
    assert "source_id" in out.result["reason"]


@pytest.mark.asyncio
async def test_run_catches_memory_store_error_cleanly():
    fake_store = _FakeStore(raises=MemoryStoreError("qdrant connection refused"))
    with patch.object(ka_module, "_build_store", return_value=fake_store):
        out = await AGENT.run(_input({"source_id": "run-123", "text": "some content"}))

    assert out.status == "failed"
    assert "qdrant connection refused" in out.result["reason"]
    assert out.next_event is None


@pytest.mark.asyncio
async def test_run_catches_embedding_error_cleanly():
    fake_store = _FakeStore(raises=LLMError("embedding call failed (voyage/voyage-3-lite): 403 Forbidden"))
    with patch.object(ka_module, "_build_store", return_value=fake_store):
        out = await AGENT.run(_input({"source_id": "run-123", "text": "some content"}))

    assert out.status == "failed"
    assert "403 Forbidden" in out.result["reason"]


@pytest.mark.asyncio
async def test_run_defaults_project_id_from_agent_input_when_missing_in_payload():
    fake_store = _FakeStore()
    project_uuid = uuid.uuid4()
    with patch.object(ka_module, "_build_store", return_value=fake_store):
        out = await AGENT.run(
            AgentInput(
                run_id=uuid.uuid4(),
                project_id=project_uuid,
                payload={"source_id": "run-123", "text": "some content"},
            )
        )

    assert out.status == "success"
    assert fake_store.calls[0]["project_id"] == str(project_uuid)
