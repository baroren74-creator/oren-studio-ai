"""Semantic search over indexed knowledge — docs/api.md's
`GET /api/knowledge/search?q=...` (Phase 2.9), backed by packages/memory's
MemoryStore over the `knowledge_docs` Qdrant collection the Knowledge
Agent writes to (Phase 2.8, agents/knowledge_agent/agent.py).

docs/api.md's route comment says "semantic search (Qdrant + Postgres
hydrate)" — full hydration means resolving each hit back to its
`sources` row (ADR-008: Qdrant is an index, never authoritative). That
table isn't persisted yet (no live orchestrator-worker writes `sources`
rows — see agents/knowledge_agent/agent.py's and workflows/graph.py's
knowledge_node comments on `source_id` currently being `run_id`, a
pragmatic stand-in). Until it is, this returns Qdrant's own payload
directly (text/source_type/source_url/score) rather than pretending to
hydrate from a table with nothing in it — revisit this module the same
day Source persistence lands.

Deliberately duplicates a small amount of MemoryStore-construction logic
from agents/knowledge_agent/agent.py's `_build_store` rather than
importing that module directly — apps/api is the API layer, not an
Agent, and Agents/services here don't import each other's internals
(the same "Agents never import each other" spirit applied one layer up,
as apps/api/app/services/research.py's docstring already notes for
`workflows.idea_scoring`)."""

from __future__ import annotations

import os
import sys
from dataclasses import asdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
for _p in (_REPO_ROOT / "providers" / "llm", _REPO_ROOT / "packages" / "memory"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from memory import MemoryStore  # noqa: E402

DEFAULT_QDRANT_URL = "http://localhost:6333"


def _build_store() -> MemoryStore:
    path = os.environ.get("QDRANT_PATH")
    if path:
        return MemoryStore(path=path)
    return MemoryStore(
        url=os.environ.get("QDRANT_URL", DEFAULT_QDRANT_URL),
        api_key=os.environ.get("QDRANT_API_KEY") or None,
    )


def search_knowledge(query: str, *, project_id: str | None = None, limit: int = 5) -> list[dict]:
    """Run a semantic search and return plain dicts (not a MemoryStore
    dataclass) so this module has no leaking dependency for callers —
    app.routers.knowledge only needs to hand these to a Pydantic
    response model."""
    store = _build_store()
    results = store.search(query, project_id=project_id, limit=limit)
    return [asdict(r) for r in results]
