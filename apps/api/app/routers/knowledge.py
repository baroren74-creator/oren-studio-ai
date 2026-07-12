"""Knowledge routes — docs/api.md's `GET /api/knowledge/search?q=...`
(Phase 2.9). See app.services.knowledge's module docstring for what
"semantic search" means at this stage (Qdrant payload directly, no
Postgres hydration yet)."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import require_api_key
from app.schemas import KnowledgeSearchResultOut
from app.services.knowledge import search_knowledge

# Explicit (not relying on import order elsewhere) — same shim as
# app.services.knowledge, idempotent either way.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_MEMORY_PKG = _REPO_ROOT / "packages" / "memory"
if str(_MEMORY_PKG) not in sys.path:
    sys.path.insert(0, str(_MEMORY_PKG))

from memory import MemoryStoreError  # noqa: E402

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"], dependencies=[Depends(require_api_key)])


@router.get("/search", response_model=list[KnowledgeSearchResultOut])
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    project_id: str | None = Query(default=None),
    limit: int = Query(default=5, ge=1, le=50),
) -> list[dict]:
    try:
        return search_knowledge(q, project_id=project_id, limit=limit)
    except MemoryStoreError as exc:
        # A down/unreachable Qdrant is a service dependency failure, not
        # a client error — 503, not 500 (nothing wrong with the request
        # itself) and not 4xx (the client can't fix this by retrying
        # differently).
        raise HTTPException(status_code=503, detail=f"knowledge store unavailable: {exc}") from exc
