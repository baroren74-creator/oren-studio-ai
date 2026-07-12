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

**Status:** Accepted (Phase 0); implemented Phase 2.6/2.7
(`workflows/idea_scoring.py`, `workflows/graph.py`'s
`idea_scoring_node`/`route_after_scoring` — see `docs/agents.md` 'Idea
scoring rubric' for the written criteria this ADR required).

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

**Status:** Superseded by ADR-011 for v1 — kept for the record and as the
documented path back if automated publishing is wanted later.

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

---

## ADR-011 — Publishing: manual upload by Oren, not automated API publishing (supersedes ADR-005 for v1)

**Status:** Accepted (this supersedes ADR-005's Postiz-adoption plan for
the v1 build; ADR-005's reasoning is kept below for the record, but the
decision it reached is no longer what gets built first)

**Context:** ADR-005 planned to self-host Postiz and integrate the
Instagram/TikTok/YouTube/Facebook/LinkedIn publish APIs, gated behind
Oren's approval. Working through the actual platform requirements
(`docs/open-source-landscape.md` section 6) surfaced real friction:
multi-week app review processes, TikTok's two-stage approval, and
ongoing OAuth/token maintenance (directly experienced first-hand getting
even a single GitHub token working end-to-end for this repo). Oren then
raised the obvious question directly: since every publish already
requires his manual review and approval before anything goes out, what
is the automated publish API actually buying beyond saving him the last
step — physically opening the platform's app and tapping "post"?

**Decision:** For v1, the Publishing Agent does not call any platform
publish API at all. Instead it:
1. Assembles the final package (video file, caption text, hashtags,
   thumbnail) exactly as before.
2. Renders a **preview** in the Studio UI showing how the post will look
   on the target platform (video + caption + hashtags together, styled
   like the platform's own post view).
3. Waits for Oren's approval (Approval Gate #2, unchanged — still
   enforced at the database level per `approvals`/`publications`).
4. Once approved, surfaces a simple "ready to upload" state with the
   final files easy to grab (e.g. a per-project export folder). Oren
   opens Instagram/TikTok/YouTube/LinkedIn himself, in his own app, and
   posts it manually.
5. Oren (optionally) marks the project as `published` in the Studio UI
   afterward, optionally pasting the resulting post URL for
   record-keeping in `publications.external_post_id`.

This removes the need for Phase 0.5 (platform API applications) and the
Postiz integration from the v1 build entirely. Both remain documented as
a possible **future upgrade**, not a current requirement — see the
revised `docs/roadmap.md` Phase 5.

**Consequences:**
- Phase 0.5 is no longer on the critical path — the whole "external
  approval lead time" risk that ADR-005/ADR-011's predecessor worried
  about simply disappears for v1.
- No OAuth/token maintenance burden, no AGPL dependency (Postiz), no
  platform ToS exposure for automated posting.
- Costs Oren roughly 30 extra seconds per post (open the app, attach the
  file, paste the caption, tap post) — on top of the review he was
  already doing.
- Lost: one-click "approve and it's live," and any future
  scheduled/timed posting (Phase 5.6 as originally scoped) — both would
  require reintroducing platform API integration later if ever wanted.
- If Oren later wants scheduled/automated posting at higher volume, the
  Postiz-based plan from ADR-005 and the Phase 0.5 application process
  are still fully documented and can be picked back up without
  redesigning anything else — this decision only removes it from the
  v1 critical path, it doesn't delete the option.

---

## ADR-012 — LangGraph interrupts give at-least-once node execution, not exactly-once

**Status:** Accepted (discovered empirically while building `workflows/graph.py`, Phase 1.13)

**Context:** While testing the mandatory approval gate (`final_review_node`,
using LangGraph's native `interrupt()`), event emission originally lived
in a node that ran before the interrupting node, on the assumption that
splitting it out would make it run exactly once. It didn't — LangGraph
replays the entire superstep containing the interrupted node on resume,
which re-ran the "before" node too, producing a duplicate
`final_review.requested` entry in the in-memory graph state's `events`
list (verified with a real `graph.invoke()` / `Command(resume=True)`
round-trip, not by reading LangGraph's docs — see the test in
`apps/api/tests/test_smoke_e2e.py` and the comment in
`workflows/graph.py`).

**Decision:** Treat any code that runs near an `interrupt()` call as
having at-least-once execution semantics, same as Temporal Activities or
any other durable-execution engine's checkpoint boundary. Concretely:
the in-memory `events` list in `StudioState` is a debugging aid only,
not a source of truth. The real `agent_events` table (`docs/database.md`)
is the source of truth, and any write to it from a node adjacent to an
interrupt must be idempotent — e.g. a unique constraint on
`(run_id, event_type)` with `ON CONFLICT DO NOTHING`, or an
application-level check-before-insert — once Phase 2+ wires real DB
writes into graph nodes instead of the test-only persistence step
currently done after `graph.invoke()` completes.

**Consequences:** No architecture change needed — LangGraph remains the
right choice (ADR-001), this is a usage detail, not a flaw. But it would
have been a genuinely confusing silent bug (duplicate events in
production, or a broken `UNIQUE` constraint) if discovered later instead
of now, in a stub-only test. Worth remembering for every future node that
does I/O near an interrupt, not just this one.

---

## ADR-013 — YouTube transcripts via youtube-transcript-api, not faster-whisper

**Status:** Accepted (Phase 2.5, Oren-approved deviation from the
original roadmap wording)

**Context:** `docs/roadmap.md` originally specced Research Agent v2 as
"YouTube URL → transcript (faster-whisper) → summary" — download the
video's audio, run a local Whisper model to transcribe it. Two problems
surfaced while implementing this: (1) YouTube already serves a
transcript — human-written or auto-generated captions — for the large
majority of videos worth summarizing, retrievable directly from
YouTube's own timedtext API, with no audio processing at all; (2) this
sandbox's network allowlist (`github.com`, `registry.npmjs.org`,
`pypi.org`, `files.pythonhosted.org`) doesn't include `youtube.com` or
any CDN/model-hosting domain faster-whisper would need, so a
faster-whisper approach couldn't even be verified from here, let alone
run without a GPU for reasonable speed.

**Decision:** `agents/research_agent/youtube_source.py` fetches an
existing transcript via `youtube-transcript-api` (MIT) instead. Flagged
to Oren directly rather than silently implemented differently from the
roadmap's wording — approved.

**Consequences:** Videos with no transcript available at all (rare, but
exists — e.g. a channel that disabled captions entirely) aren't
supported by this v1; `fetch_video_transcript` raises
`YouTubeSourceError` and the Agent returns `status="failed"` cleanly for
that case, same as any other fetch failure (no silent wrong answer).
faster-whisper remains the documented fallback for that specific gap if
it turns out to matter in practice — not implemented now, since it would
be solving a problem that hasn't actually shown up yet.
