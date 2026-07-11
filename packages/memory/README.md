# packages/memory

The custom chunking/embedding/retrieval layer (ADR-002 — deliberately
*not* LlamaIndex or Haystack). Talks to Qdrant for vectors and Postgres
for hydration; every Qdrant point ID equals a Postgres row ID (ADR-008).
Also home to the Preference Engine (Phase 6) and Prompt Library access
code. See `docs/database.md` for the Qdrant collection list.
