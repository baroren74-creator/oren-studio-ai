# Agents Reference

Living reference for every Agent in the system. Update this file in the
same PR that adds or changes an Agent (see `CONTRIBUTING.md`).

## The Agent contract

Every Agent, without exception, implements the same interface — defined
once in `packages/core/schemas`:

```python
class AgentInput(BaseModel):
    run_id: UUID
    project_id: UUID
    payload: dict          # schema specific to each agent, validated separately
    context: AgentContext  # memory refs, style guide refs, budget remaining

class AgentOutput(BaseModel):
    status: Literal["success", "failed", "needs_approval", "skipped"]
    result: dict
    artifacts: list[ArtifactRef]
    cost: CostInfo
    next_event: str | None

class Agent(Protocol):
    name: str
    version: str
    input_schema: type[BaseModel]
    output_schema: type[BaseModel]
    async def run(self, input: AgentInput) -> AgentOutput: ...
```

**Hard rule:** an Agent never imports another Agent's module. All
communication is via events (see `docs/api.md`) and the database. The
Orchestrator (LangGraph, `workflows/`) is the only thing that knows the
order agents run in.

## Agent Registry

A config-driven mapping of `agent_name → implementation + provider
config`, read by the Orchestrator at runtime — not hardcoded into the
graph. Adding a new Agent means adding a registry entry, not editing
Orchestrator code.

## Agent roster

| Agent | Folder | Responsibility | Emits (on success) |
|---|---|---|---|
| Research Agent | `agents/research_agent` | Finds sources, reads documentation, summarizes, understands the underlying technology, finds the *original* source. | `research.completed` |
| Trend Agent | `agents/trend_agent` | Discovers new things: GitHub Trending (v1, done), Hacker News, Product Hunt, Reddit, AI news, Twitter/X (deferred), YouTube, blogs. Not a `workflows/graph.py` node — runs independent of any project (`ideas.project_id` is nullable), triggered separately, not per-project. | `trend.discovered`, feeds the Idea Backlog |
| Knowledge Agent | `agents/knowledge_agent` | Chunks + embeds + indexes the Research Agent's raw digest/transcript text into Qdrant's `knowledge_docs` collection via `packages/memory` (Phase 2.8, done — see the section below). Semantic search (`GET /api/knowledge/search`) is a separate `apps/api` route, not this Agent (Phase 2.9, done). | `source.ingested` |
| Script Agent | `agents/script_agent` | Writes Hook, Body, CTA, Caption, Title, Hashtags together (one structured LLM call, not three) — in Oren's style (`style_profile`, Phase 3.1/3.2-3.4, done — see the section below). | `script.drafted` |
| Recording Agent | `agents/recording_agent` | v0: manual upload. Later: drives an Avatar provider (MuseTalk/LivePortrait). | `recording.completed` |
| Video Agent | `agents/video_agent` | Cuts, zooms, captions, B-roll/screenshot overlay, cursor highlight, thumbnail. | `video.rendered`, `captions.generated`, `thumbnail.generated` |
| Voice Agent | `agents/voice_agent` | Voice enhancement, dubbing, translation, cloning (commercial API by default — ADR-004). | `voice.completed` |
| Publishing Agent | `agents/publishing_agent` | Assembles the final package (video, caption, hashtags, thumbnail) and a platform-style preview; never marks anything published without approval. Oren uploads manually — no publish API call (ADR-011). | `final_review.requested`, `publish.completed` (set by Oren, not an API response) |

Each Agent's exact `payload`/`result` schema is defined in its own
`agent.py` alongside its implementation — this table is the map, not the
territory. When an Agent's schema changes, update this table's
"Responsibility" column if the change is behavior-visible.

## Idea scoring rubric (Phase 2.6/2.7 — implemented)

Implementation: `workflows/idea_scoring.py`'s `score_idea()`. Not a
registered Agent (no entry in the roster above) — like the Storyboard
module below (Phase 3.7), it's a custom LLM-prompting module wired
directly into `workflows/graph.py`'s `idea_scoring_node`, run right after
Research + Knowledge and before any expensive stage (ADR-003).

Four criteria, each scored 0-25 by the LLM, summed in code (not asked of
the LLM as a single number — see `score_idea`'s docstring for why that
distinction matters):

| Criterion | What it judges |
|---|---|
| `novelty` | Fresh/uncommon, or already covered extensively elsewhere? |
| `audience_relevance` | Fits a tech-focused short-video channel (dev tools, AI, open source, practical demos)? |
| `source_reliability` | Does the source look mature and credible (real docs, apparent real-world usage), not a toy/abandoned project? |
| `visual_potential` | Lends itself to a short, visual, demo-able video, rather than being purely abstract/textual? |

Total (0-100) is compared against `workflows/graph.py`'s
`IDEA_SCORE_THRESHOLD` (50.0); below it, the graph routes to
`idea_rejected` and stops before Script/Storyboard/Recording/Video/Voice
ever run. A project with no Research Agent output to score (unsupported
source type, fetch/LLM failure) is scored 0.0 automatically — there's
nothing to judge, so it can't clear the gate (`idea_scoring_node`'s
docstring).

`audience_relevance` is currently judged only against "is this a
tech-content channel fit" in general, not Oren's specific stated
interests — there's no `style_profile` yet (Phase 3.1) to ground that in.
Revisit this criterion's prompt once `style_profile` exists.

The score is persisted onto the `research_notes` row the Research Agent
already wrote (`interest_score`/`scored_by` columns,
`apps/api/app/services/research.py`'s `update_idea_score()`) — not a new
row, per that module's original note that this UPDATE would come later.

## Storyboard module (Phase 3.7 — implemented)

Implementation: `workflows/storyboard.py`'s `generate_storyboard()`. Not
a registered Agent (no entry in the roster above), same reasoning as the
idea scoring rubric above — a custom LLM-prompting module wired directly
into `workflows/graph.py`'s `storyboard_node`, which runs right after
Script drafting. `docs/open-source-landscape.md` section 4 found no
mature OSS library for "turn a script into a shot list," so this is a
real implementation, not a wrapper.

One LLM call turns the drafted script (hook/body/cta) into a small,
ordered sequence of scenes (typically 3-8 for a short-form video), each:

| Field | What it holds |
|---|---|
| `order` | Position in the sequence, renumbered sequentially in code (1, 2, 3, ...) regardless of what the LLM stated — same "don't trust the model with an invariant code can enforce" reasoning as idea scoring's criterion clamping. |
| `description` | The visual instruction — what should be shown on screen for this scene. |
| `duration` | Estimated seconds this scene takes, a positive number. |
| `caption_cue` | Short on-screen text/caption for this scene, or `null`. |
| `visual_ref` | Always `null` for now — no asset library/B-roll search is wired up yet (Recording/Video Agent territory, still Stub Agents); a human or a later phase fills this in. |

`storyboard_node` skips itself — no LLM call, `storyboard_scenes` stays
unset, `agent_costs` gets no entry — when there's no `script_hook`/
`script_body` to work from (a rejected idea never reaches this node
anyway; a graph-shape test that never populated a script is the other
case). A `StoryboardError` (LLM failure, non-JSON response, empty/
malformed scenes) is caught the same way and treated as "no scenes
produced," never a crash — the graph still emits `storyboard.ready`
either way, same as `idea_scoring_node` always emitting `idea.scored`
even on a scoring failure.

Persisted onto a new `storyboards` row (`docs/database.md`,
`apps/api/app/models.py`'s `Storyboard`) linked to the `scripts` row it
was generated from via `script_id` — a fresh row per run, same
"re-running is the recovery path, not editing in place" convention as
`Script`/`ResearchNote`.

## Knowledge Agent (Phase 2.8/2.9 — implemented)

`packages/memory` is the ADR-002-mandated "custom thin layer" (chunk ->
embed -> upsert -> query, not LlamaIndex/Haystack): `chunking.py`'s
`chunk_text()` splits on word count with overlap (no tokenizer
dependency — good enough for this project's known source types), and
`store.py`'s `MemoryStore` wraps `qdrant-client` directly (embedded local
mode via `path=`, or a real server via `url=`/`api_key=`).

Embeddings go through `providers/llm`'s `embed()` — Voyage AI
(`voyage/voyage-3-lite` by default), routed through LiteLLM the same way
completions are. No prior doc specified an embedding provider; Voyage
was chosen with Oren's explicit approval as Anthropic's recommended RAG
embedding partner.

`agents/knowledge_agent/agent.py` expects `payload.text` (the source's
full raw content), `payload.source_id`, `payload.project_id`,
`payload.source_type`, `payload.source_url`. No text -> `status="skipped"`,
`next_event=None` (same convention as Research Agent: an unsupported
source type or an upstream fetch/LLM failure means there's nothing to
index, not a failure of this Agent). `workflows/graph.py`'s
`knowledge_node` builds that payload from `StudioState.research_raw_text`
— Research Agent's result now includes `raw_text` (the full digest/
transcript) alongside its LLM `summary`, specifically so Knowledge Agent
has something to index that isn't just the human-facing summary.

**Point IDs and `source_id` (ADR-008):** every Qdrant point should map to
a Postgres row ID. Chunking makes that literal for one row impossible (N
chunks, one row), so `MemoryStore` derives each point's ID deterministically
as `uuid5(source_id, chunk_index)` — re-ingesting the same `source_id`
always reproduces the same point IDs (upsert overwrites in place, nothing
duplicates), and the payload always carries `source_id` for tracing a hit
back to its origin. Separately, `source_id` itself is currently `run_id`
(`agent_runs.id`), not a real `sources.id` — there's no live orchestrator-
worker persisting `sources` rows yet (the same "not built yet" gap
`apps/api/app/services/research.py` already notes for `research_notes`).
Both of these are pragmatic, documented stand-ins to revisit together
once Source persistence exists — see `packages/memory/memory/store.py`'s
module docstring and `workflows/graph.py`'s `knowledge_node` comment.

**Semantic search** (`GET /api/knowledge/search?q=...&project_id=...&limit=...`,
`apps/api/app/routers/knowledge.py`) returns Qdrant's own payload
(text/score/source metadata) directly, not the "Qdrant + Postgres
hydrate" version `docs/api.md`'s route comment describes — hydration
needs a real `sources` row to hydrate *from*, which doesn't exist yet
(same gap as above). Returns 503 (not 500/4xx) when the store is
unreachable — a dependency failure, not something the client can fix by
retrying differently.

## Style profile (Phase 3.1 — implemented)

`docs/database.md`'s `style_profile` table (`apps/api/app/models.py`'s
`StyleProfile`), filled in via a manual one-time questionnaire — asked
in chat, not a UI (Prompt Library UI, Phase 3.5, doesn't exist yet).
Versioned rather than updated in place (`app/services/style_profile.py`):
`POST /api/style-profile` always inserts at `max(version) + 1`;
`GET /api/style-profile/current` reads the highest version (404 if the
questionnaire has never been run). `opening_patterns`/`closing_patterns`
are stored as JSON lists in code even though docs/database.md shows
`TEXT[]` — the same SQLite/Postgres-agnostic simplification
`ResearchNote.key_points` already uses.

Oren's actual v0 answers (2026-07-12): tone is a mix of energetic/fast,
professional/precise, and friendly/conversational — deliberately not one
single register; videos run 30-45 seconds; opening patterns `"הי חברים
תראו מה מצאתי"` / `"ידעתם שיש כזה דבר?"`; closing patterns `"אהבתם, רוצים
עוד? תעקבו"` / `"ללינק כתבו לי בתגובות"`. Seeded via
`scripts/seed_style_profile.py` (idempotent-ish: safe to re-run, just
creates another version rather than corrupting anything) — not yet run
against a real Postgres instance since none is live from this sandbox;
verified end-to-end against a throwaway SQLite DB, including the Hebrew
text round-tripping correctly through JSON storage.

## Script Agent (Phase 3.2-3.4 — implemented)

`agents/script_agent/agent.py`: one structured LLM call producing all
six fields at once (`hook`/`body`/`cta`/`caption`/`title`/`hashtags`) —
the roadmap's 3.2/3.3/3.4 split (Hook generator / Body+CTA /
Caption+Title+Hashtags) was planning granularity, not three separate
Agents or LLM calls; the fields aren't independent (a caption references
the hook, hashtags follow the body's topic) and `docs/database.md`'s
`scripts` row stores them together. Same architectural choice as
`workflows/idea_scoring.py` combining four rubric criteria into one call.

Payload (built by `workflows/graph.py`'s `script_node`): `research_summary`/
`research_key_points` (from Research Agent, via `StudioState`) plus
whatever `style_tone_notes`/`style_opening_patterns`/
`style_closing_patterns`/`style_avg_length_seconds` the caller seeded
into the initial graph state (the graph itself never queries the DB —
see `knowledge_node`'s comment for the established reasoning; a real
orchestrator-worker would call `get_current_style_profile()` before
invoking the graph). No `research_summary` -> `status="skipped"`
(mirrors Research Agent). Missing/malformed JSON response ->
`status="failed"` (same `_extract_json` markdown-fence-stripping pattern
as `workflows/idea_scoring.py`).

Writes in Hebrew — Research Agent's summary/key_points stay English on
purpose (see that Agent's system prompts: "Script Agent handles Hebrew
translation later"); this is where that translation actually happens.
Style guide is `docs/vision.md`'s baseline (short, fast, clear,
technical, not exhausting, hook within 3 seconds) plus Oren's actual
style_profile fields when available — the Agent still produces a
reasonable script with the baseline alone if the questionnaire has never
been run, since it's one-time but not mandatory-before-first-use.

Persistence: `apps/api/app/models.py`'s `Script` (table `scripts`) via
`apps/api/app/services/script.py`'s `persist_script()` — the first
Phase-3 persistence function that can actually link a real
`style_profile_id`, now that Phase 3.1's questionnaire exists.
`style_profile_id` is nullable (a script written before the
questionnaire ever ran has nothing to point at).
