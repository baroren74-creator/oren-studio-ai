# packages/memory

The custom chunking/embedding/retrieval layer (ADR-002 — deliberately
*not* LlamaIndex or Haystack). Talks to Qdrant for vectors; every Qdrant
point ID is derived deterministically from a Postgres row ID (ADR-008 —
see `memory/store.py`'s module docstring for why chunking makes literal
ID equality impossible, and how the derivation still satisfies ADR-008's
actual requirement). See `docs/database.md` for the Qdrant collection
list and `docs/agents.md`'s Knowledge Agent section for the full picture.

**Implemented (Phase 2.8):** `chunking.py`'s `chunk_text()`, `store.py`'s
`MemoryStore` (`upsert_document()` / `search()` / `delete_source()`),
used by `agents/knowledge_agent`. Embeddings via `providers/llm`'s
`embed()` (Voyage AI through LiteLLM).

**Not yet built:** Postgres hydration (no `sources` rows persisted yet —
search results currently return Qdrant's own payload directly, see
`apps/api/app/services/knowledge.py`), the Preference Engine (Phase 6),
and Prompt Library access code — those will land in this same package
when their phases start.
