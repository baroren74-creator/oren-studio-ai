"""MemoryStore — the ~300-line chunk -> embed -> upsert -> query layer
mandated by docs/decisions.md ADR-002 (explicitly NOT LlamaIndex/Haystack).

Wraps qdrant-client directly. Two construction modes:
  - MemoryStore(path="/some/dir")   embedded local mode, no server — used
    in tests and verified working standalone (see providers/llm work log).
  - MemoryStore(url="http://...")   talks to a real Qdrant service, e.g.
    the one defined in docker-compose for production/dev.

Default collection is `knowledge_docs` — matches docs/database.md's
Qdrant collection table, whose source table is `sources.id` (Phase 2.8
scope: the Knowledge Agent ingesting `source.ingested` payloads). Other
listed collections (`transcripts`, `personal_style`, `prompt_library`,
`preferences`) are later-phase concerns (Script Agent style matching,
Preference Engine) and can reuse this same class with a different
`collection=` — nothing here is knowledge_docs-specific.

Point IDs, ADR-008 ("every Qdrant point ID = a Postgres row ID", and
"every Qdrant point is rebuildable from Postgres by a deterministic
job"): a single Postgres row (one `sources.id`) chunks into N vectors,
so N points can't all literally equal that one UUID. Instead each
point's ID is `uuid5(source_id, chunk_index)` — deterministic, so
re-ingesting the same source_id always reproduces the same point IDs
(upsert overwrites in place, nothing duplicates), and the payload always
carries the original `source_id` so a hit can be hydrated back to
Postgres. This satisfies ADR-008's actual requirement (deterministic,
rebuildable, traceable) without requiring literal ID equality, which
chunking makes impossible.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

# providers/llm is a sibling package, not installed via the (not-yet-set-up)
# workspace package manager — same sys.path shim as agents/research_agent/agent.py
# and workflows/idea_scoring.py; see docs/roadmap.md for when a proper monorepo
# Python tool (uv/pdm workspaces) replaces this.
_PROVIDERS_LLM = Path(__file__).resolve().parents[3] / "providers" / "llm"
if str(_PROVIDERS_LLM) not in sys.path:
    sys.path.insert(0, str(_PROVIDERS_LLM))

from llm_provider.client import embed as embed_texts

from memory.chunking import chunk_text

DEFAULT_VECTOR_SIZE = 512  # voyage-3-lite output dimension
DEFAULT_COLLECTION = "knowledge_docs"

# Fixed, arbitrary namespace UUID for deriving deterministic point IDs
# from (source_id, chunk_index). Any constant works — it only needs to
# stay constant across runs so the same input always maps to the same
# point ID; changing it would orphan every previously-stored point.
_POINT_ID_NAMESPACE = uuid.UUID("6f2f6f7a-6b0e-4f0a-8c8b-3a9e9d9f7c11")


def _point_id(source_id: str, chunk_index: int) -> str:
    return str(uuid.uuid5(_POINT_ID_NAMESPACE, f"{source_id}:{chunk_index}"))


class MemoryStoreError(Exception):
    """Raised when a qdrant-client operation fails (connect, create
    collection, upsert, delete, query) — mirrors GitHubSourceError /
    YouTubeSourceError / TrendSourceError's per-module typed-error
    convention elsewhere in this repo. Not raised for embedding
    failures — those surface as llm_provider.LLMError directly from
    embed_texts, which callers (e.g. agents/knowledge_agent) already
    know how to handle."""


@dataclass
class SearchResult:
    text: str
    score: float
    payload: dict = field(default_factory=dict)


class MemoryStore:
    """Thin wrapper around qdrant-client for this project's one use case:
    store chunks of text tied to a Postgres source row, and search them
    back by semantic similarity, optionally filtered by project_id.
    """

    def __init__(
        self,
        *,
        path: str | None = None,
        url: str | None = None,
        api_key: str | None = None,
        collection: str = DEFAULT_COLLECTION,
        vector_size: int = DEFAULT_VECTOR_SIZE,
        embedding_model: str | None = None,
    ) -> None:
        if not path and not url:
            raise ValueError("MemoryStore requires either path= (local/embedded) or url= (server)")
        if path and url:
            raise ValueError("MemoryStore accepts only one of path= or url=, not both")

        from qdrant_client import QdrantClient

        self._collection = collection
        self._vector_size = vector_size
        self._embedding_model = embedding_model
        try:
            self._client = QdrantClient(path=path) if path else QdrantClient(url=url, api_key=api_key)
            self._ensure_collection()
        except Exception as exc:
            raise MemoryStoreError(f"failed to connect to Qdrant / ensure collection '{collection}': {exc}") from exc

    def _ensure_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams

        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection not in existing:
            self._client.create_collection(
                self._collection,
                vectors_config=VectorParams(size=self._vector_size, distance=Distance.COSINE),
            )

    def upsert_document(
        self,
        *,
        source_id: str,
        text: str,
        project_id: str,
        source_type: str,
        source_url: str | None = None,
        extra_payload: dict | None = None,
        chunk_words: int | None = None,
    ) -> int:
        """Chunk `text`, embed each chunk, and upsert into the collection.

        `source_id` must be the originating `sources.id` (Postgres row) —
        see the module docstring for how it's used to derive deterministic
        point IDs. Returns the number of chunks stored; empty/whitespace-
        only text stores nothing and returns 0 (mirrors the Research
        Agent's own "skip, don't crash" convention for absent content).
        """
        chunks = chunk_text(text, **({"chunk_words": chunk_words} if chunk_words else {}))
        if not chunks:
            return 0

        embedding = embed_texts(chunks, model=self._embedding_model)

        from qdrant_client.models import PointStruct

        points = []
        for chunk_index, (chunk, vector) in enumerate(zip(chunks, embedding.vectors)):
            payload = {
                "text": chunk,
                "source_id": source_id,
                "chunk_index": chunk_index,
                "project_id": project_id,
                "source_type": source_type,
                "source_url": source_url,
                **(extra_payload or {}),
            }
            points.append(PointStruct(id=_point_id(source_id, chunk_index), vector=vector, payload=payload))

        try:
            self._client.upsert(self._collection, points=points)
        except Exception as exc:
            raise MemoryStoreError(f"qdrant upsert failed for source_id={source_id!r}: {exc}") from exc
        return len(points)

    def delete_source(self, source_id: str) -> None:
        """Remove every point derived from a given source_id. Combined
        with upsert_document's deterministic IDs, this makes a source
        fully rebuildable/re-ingestable from Postgres (ADR-008) — delete
        then re-upsert, or just re-upsert (same IDs overwrite in place).
        """
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        try:
            self._client.delete(
                self._collection,
                points_selector=Filter(must=[FieldCondition(key="source_id", match=MatchValue(value=source_id))]),
            )
        except Exception as exc:
            raise MemoryStoreError(f"qdrant delete failed for source_id={source_id!r}: {exc}") from exc

    def search(
        self,
        query: str,
        *,
        project_id: str | None = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        """Embed `query` and return the top `limit` most similar chunks,
        optionally restricted to a single project_id.
        """
        embedding = embed_texts([query], model=self._embedding_model)
        query_vector = embedding.vectors[0]

        query_filter = None
        if project_id is not None:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            query_filter = Filter(must=[FieldCondition(key="project_id", match=MatchValue(value=project_id))])

        try:
            response = self._client.query_points(
                self._collection,
                query=query_vector,
                limit=limit,
                query_filter=query_filter,
            )
        except Exception as exc:
            raise MemoryStoreError(f"qdrant query failed: {exc}") from exc

        results = []
        for point in response.points:
            payload = point.payload or {}
            results.append(SearchResult(text=payload.get("text", ""), score=point.score, payload=payload))
        return results
