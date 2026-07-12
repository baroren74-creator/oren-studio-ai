"""Knowledge Agent — see docs/agents.md.

Phase 2.8 (docs/roadmap.md): real logic — chunk + embed + upsert the
Research Agent's raw digest/transcript text into Qdrant via
packages/memory's MemoryStore (ADR-002: a custom thin layer, not
LlamaIndex/Haystack). Expects `workflows/graph.py`'s knowledge_node to
pass `source_id`, `text`, `project_id`, `source_type`, `source_url` in
the payload — see that node's comment for why `source_id` is `run_id`
for now rather than a real `sources.id` row.

This replaces the Stub Agent registration from Phase 1.18 — as with the
Research Agent and Trend Agent before it, nothing about how it's
registered or called changed (core.registry, core.schemas.agent.Agent
contract).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# providers/llm and packages/memory are sibling packages, not installed
# via the (not-yet-set-up) workspace package manager — same sys.path
# shim as agents/research_agent/agent.py and agents/trend_agent/agent.py.
_REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (_REPO_ROOT / "providers" / "llm", _REPO_ROOT / "packages" / "memory"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from core.registry import default_registry
from core.schemas.agent import AgentInput, AgentOutput
from llm_provider import LLMError
from memory import MemoryStore, MemoryStoreError

NAME = "knowledge_agent"
VERSION = "0.1.0"

# .env.example documents QDRANT_URL/QDRANT_API_KEY for the real server
# (docker-compose's qdrant service). QDRANT_PATH is a local/embedded-mode
# override (no server) for dev/test convenience — same idea as providers/
# llm's OREN_STUDIO_EMBEDDING_MODEL env override.
DEFAULT_QDRANT_URL = "http://localhost:6333"


def _build_store() -> MemoryStore:
    """Construct the MemoryStore this agent indexes into. A separate
    function (rather than inlined in run()) so tests can monkeypatch it
    to return a fake store instead of touching real Qdrant — same
    pattern as agents/research_agent/agent.py patching module-level
    fetch_repo_digest/complete."""
    path = os.environ.get("QDRANT_PATH")
    if path:
        return MemoryStore(path=path)
    return MemoryStore(
        url=os.environ.get("QDRANT_URL", DEFAULT_QDRANT_URL),
        api_key=os.environ.get("QDRANT_API_KEY") or None,
    )


class KnowledgeAgent:
    name = NAME
    version = VERSION

    async def run(self, input: AgentInput) -> AgentOutput:
        text = input.payload.get("text")
        source_id = input.payload.get("source_id")
        source_type = input.payload.get("source_type")
        source_url = input.payload.get("source_url")
        project_id = input.payload.get("project_id") or str(input.project_id)

        if not text or not text.strip():
            # Mirrors Research Agent's "skip, don't crash" convention
            # (agents/research_agent/agent.py) — an unsupported
            # source_type, or a fetch/LLM failure upstream, means there's
            # nothing to index. Not a failure of this Agent's own logic.
            return AgentOutput(
                status="skipped",
                result={"reason": "no text to index (payload.text is empty)"},
                next_event=None,
            )

        if not source_id:
            return AgentOutput(status="failed", result={"reason": "payload.source_id is required"})

        try:
            store = _build_store()
            chunks_indexed = store.upsert_document(
                source_id=source_id,
                text=text,
                project_id=project_id,
                source_type=source_type or "unknown",
                source_url=source_url,
            )
        except (MemoryStoreError, LLMError) as exc:
            return AgentOutput(status="failed", result={"reason": str(exc), "source_id": source_id})

        return AgentOutput(
            status="success",
            result={"source_id": source_id, "chunks_indexed": chunks_indexed},
            next_event="source.ingested",
        )


agent = KnowledgeAgent()
default_registry.register(NAME, lambda: agent)
