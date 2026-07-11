# Architecture Decision Log (ADRs)

Short-form ADRs. Add a new entry for every decision that would be
expensive to silently reverse. Never edit a past entry's Decision once
accepted — if circumstances change, add a new ADR that supersedes it and
say so explicitly.

---

## ADR-001 — Orchestrator: LangGraph, embedded (not the hosted Platform server)

**Status:** Accepted (Phase 0)

**Context:** Needed a stateful, resumable graph runner with native
human-in-the-loop support, evaluated against CrewAI, AutoGen/AG2, Temporal,
Prefect, n8n, Mastra (`docs/open-source-landscape.md` section 1).

**Decision:** Use LangGraph's core library (MIT), embedded directly inside
`apps/api` / `services/orchestrator-worker`. Explicitly do **not** use
`langgraph-api` / LangGraph Platform, which carries separate commercial
licensing terms.

**Consequences:** Checkpointing persists to Postgres, no extra
infrastructure. Team of one must self-manage graph versioning/upgrades
(no managed platform). Revisit if video rendering proves failure-prone
enough to need Temporal-grade durability for that one step only.

---

## ADR-002 — Vector DB: Qdrant; no RAG framework, custom thin index layer

**Status:** Accepted (Phase 0)

**Context:** Qdrant vs. Chroma/Weaviate/Milvus for the vector index;
LlamaIndex/Haystack evaluated as RAG frameworks
(`docs/open-source-landscape.md` sections 2 and 3).

**Decision:** Qdrant (Apache-2.0, no relicensing history) as the vector
index, with every point ID equal to the corresponding Postgres row ID —
Postgres remains the only source of truth. Do **not** adopt LlamaIndex or
Haystack as the retrieval runtime; build a ~300-line chunk→embed→upsert→
query module in `packages/memory` instead. Ingestion *ideas* may be
borrowed from LlamaIndex's MIT-licensed loaders as reference, not as a
dependency.

**Consequences:** More upfront code than "just install LlamaIndex," but
no framework abstraction fighting the Postgres-as-truth rule, and no
company-driven roadmap risk on a core dependency.

---

## ADR-003 — Idea scoring is a hard cost gate, not just a data field

**Status:** Accepted (Phase 0)

**Context:** No cost/budget control existed in the original PRD; a
Research→Script→Video pipeline run on every idea would be expensive.

**Decision:** `interest_score` (Phase 2.6–2.7) gates progression — below
threshold emits `idea.rejected` and the pipeline stops before any
expensive (Script/Video/Voice) stage runs.

**Consequences:** Requires writing a real scoring rubric early
(Phase 2.6) instead of deferring it to Phase 3 as originally planned.

---

## ADR-004 — Voice/TTS: commercial API default, not self-hosted cloning

**Status:** Accepted (Phase 0) — supersedes the PRD's "no vendor lock-in
for voice" aspiration for this specific capability

**Context:** The two highest-quality open voice-cloning models (Coqui/
XTTS, Fish Speech/OpenAudio) both carry non-commercial licenses — Coqui's
issuing company no longer exists to sell a commercial license, and Fish
Audio requires a separate paid agreement. OpenVoice (MIT) is the only
cloning-capable option with an unambiguous commercial license, but its
Hebrew output quality is unverified by any source found
(`docs/open-source-landscape.md` section 5).

**Decision:** Default to a commercial API (e.g. ElevenLabs) for Hebrew
voice cloning/voiceover in Phase 4. Treat OpenVoice as a parallel,
non-blocking cost-reduction experiment — only migrate if a hands-on
Hebrew quality test passes.

**Consequences:** This is a genuine, acknowledged deviation from "no
vendor lock-in." Revisit if OpenVoice's Hebrew quality proves acceptable,
or if a cleanly-licensed alternative emerges.

---

## ADR-005 — Publishing: adopt Postiz, build only the approval gate

**Status:** Accepted (Phase 0)

**Context:** Building OAuth + token refresh + chunked upload handling for
5 platforms from scratch is exactly the kind of already-solved problem
this project should not rebuild (`docs/open-source-landscape.md`
section 6).

**Decision:** Self-host Postiz (AGPL-3.0) for OAuth/scheduling plumbing.
Build only the human-approval gate as custom code: content sits held in
Postiz until `approvals.status = approved` in Postgres, then Oren Studio
AI's own code calls Postiz's API to release it.

**Consequences:** AGPL-3.0 is acceptable for a non-redistributed,
personal-use deployment; revisit if the code is ever redistributed or
offered to others. Mixpost (MIT core + one-time paid Pro tier) is the
documented fallback if AGPL becomes a real concern later.

---

## ADR-006 — Auth: simple API key for MVP, not Clerk/Auth.js

**Status:** Accepted (Phase 0)

**Context:** The original PRD listed Clerk/Auth.js as "future"
authentication. For a genuinely single-user system with no multi-tenant
requirement, full auth-as-a-service is unused surface area.

**Decision:** `STUDIO_API_KEY` (see `.env.example`) gates `apps/api` in
the MVP. Revisit only if multi-device login with real session management
becomes a practical need (not just a "nice to have").

**Consequences:** Less initial complexity; no external auth dependency;
would need real work to retrofit multi-user support later — acceptable
given the project's explicit single-user premise.

---

## ADR-007 — n8n: peripheral trigger layer only, never core orchestration

**Status:** Accepted (Phase 0)

**Context:** n8n's license (Sustainable Use License) is source-available,
not OSI-approved open source — it restricts commercial redistribution/
resale (`docs/open-source-landscape.md` section 1).

**Decision:** If used at all, n8n is confined to peripheral
triggers/webhooks (e.g. "new video from channel X"), never the core
Orchestrator (that's LangGraph, ADR-001).

**Consequences:** Avoids building core infrastructure on a license that
would complicate any future commercialization, per the PRD's own
long-term ambiguity about SaaS potential ("ואינה מוצר מסחרי **בשלב
הראשון**" implies that could change).

---

## ADR-008 — Postgres is the only source of truth; Qdrant is an index, never authoritative

**Status:** Accepted (Phase 0)

**Context:** Running two "databases" invites drift if either can be
authoritative for the same fact.

**Decision:** Every Qdrant point is rebuildable from Postgres by a
deterministic job. Nothing is ever written to Qdrant that doesn't also
exist in Postgres. No Agent queries Qdrant and treats the result as
ground truth without hydrating the actual row from Postgres by ID.

**Consequences:** Reindexing Qdrant from scratch is always possible and
cheap; slight overhead of always doing a second lookup after a vector
search.

---

## ADR-009 — License posture: proprietary for now, explicitly revisit before any public release

**Status:** Accepted (Phase 1)

**Context:** The PRD is explicit this is not a SaaS/commercial product
"in its first phase," leaving the door open for later.

**Decision:** `LICENSE` = all rights reserved / proprietary. Third-party
OSS dependencies keep their own licenses regardless (tracked in
`docs/open-source-landscape.md`).

**Consequences:** If Oren Studio AI is ever open-sourced or productized,
this file — and every AGPL/Sustainable-Use-License dependency adopted
under ADR-005/ADR-007 — needs a fresh legal review before that happens.

---

## ADR-010 — Hebrew RTL caption rendering: pending, resolved in Phase 3.5

**Status:** Open — decision deferred to a scheduled spike, not skipped

**Context:** A confirmed, open MoviePy GitHub issue shows RTL text
rendering mirrored/broken; ffmpeg+libass can work correctly but only
under specific build flags; Remotion (Chromium-based) is untested for
Hebrew by any source found.

**Decision:** Do not choose a captioning approach by assumption. Phase
3.5 runs a concrete side-by-side test before any Video Agent captioning
code is written; the result gets recorded here as ADR-010a once decided.

**Consequences:** Adds a small, explicit phase before Phase 4 rather than
discovering the problem mid-implementation.
