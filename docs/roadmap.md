# Roadmap

Granular, phase-by-phase. This supersedes the roadmap section in
`docs/architecture.md` (which is left intact for historical context) by
folding in the changes from `docs/open-source-landscape.md`. Update the
status table in the root `ROADMAP.md` as phases complete.

## Phase 0 — Architecture + Open Source Research ✅ Done

- CTO-style architecture review of the PRD (`docs/architecture.md`).
- Live research across 17 tool categories, ~60 projects
  (`docs/open-source-landscape.md`).
- Architecture revised based on findings (5 substantive changes — see
  `docs/decisions.md` ADR-001 through ADR-005).

## Phase 0.5 — Publishing API Applications ⏸ Deferred — not needed for v1 (see ADR-011)

**Superseded by ADR-011.** v1 uses manual publishing: the Publishing
Agent prepares a final package and a preview, Oren approves, then uploads
it himself through each platform's own app. None of the platform API
applications below are required for that flow. This phase stays fully
documented and ready to resume — unchanged from the original research —
in case scheduled/automated posting is wanted later.

0.5.1 (deferred) Register Meta developer app; begin Instagram + Facebook
      App Review (`instagram_business_basic`,
      `instagram_business_content_publish`, `pages_manage_posts`) —
      expect 2–6 weeks incl. Business Verification.
0.5.2 (deferred) Register TikTok developer app; begin Content Posting API
      application (`video.publish` scope) — expect 2–6 weeks for initial
      approval, **then** a second compliance audit before public (non
      SELF_ONLY) posting is allowed.
0.5.3 (deferred) Register Google Cloud project + YouTube Data API v3 —
      low friction at this project's volume (post-Dec-2025 quota
      pricing), no audit needed under ~100 uploads/day.
0.5.4 (deferred) Register LinkedIn app, add "Share on LinkedIn" product
      (`w_member_social`, self-serve, personal profile only) — low
      friction, immediate, would be the cheapest one to pick up first if
      automation is ever revisited.
0.5.5 (deferred) Decide explicitly: is a LinkedIn **company page**
      actually required? If yes, budget 4 weeks–4 months and expect
      possible rejection (Marketing Developer Platform).
0.5.6 (deferred) Track application status in `docs/decisions.md` if/when
      this phase is resumed.

## Phase 1 — Project Initialization ✅ Done

1.1 Monorepo skeleton (`docs/`, `apps/`, `packages/`, `services/`,
    `agents/`, `providers/`, `workflows/`, `prompts/`, `scripts/`,
    `docker/`, `.github/`) — done.
1.2 Repository standard files (README, CONTRIBUTING, ARCHITECTURE,
    ROADMAP, CHANGELOG, LICENSE, CODEOWNERS) — done.
1.3 `docker-compose.yml`: Postgres + Redis + Qdrant + MinIO + self-hosted
    SearXNG — done.
1.4 `.env.example`, `.editorconfig`, `.gitignore`, pre-commit config
    (ruff, prettier, gitleaks) — done.
1.5 CI hygiene workflow (compose validation, secret scanning, markdown
    lint); Python/web test jobs stubbed, commented until real code lands
    — done.
1.6 `docs/standards.md` — done.
1.7 `docs/` populated with vision/prd/architecture/open-source-landscape/
    roadmap/decisions/agents/api/database — done (this batch).
1.8 Alembic migrations: `projects`, `sources`, `agent_runs`,
    `agent_events`, `approvals` (see `docs/database.md`) — done, tested
    against SQLite (portable — same models run against Postgres via
    `DATABASE_URL`).
1.9 FastAPI skeleton (`apps/api`) + health check + simple API-key auth —
    done, tested (auth rejection + happy path both covered).
1.10 Next.js skeleton (`apps/web`) + layout (Chat / Projects / Knowledge /
     Prompts / Settings, plus Ops) — done, `npm run build` passes clean
     on Next.js 16.
1.11 `AgentInput`/`AgentOutput` Pydantic schemas in `packages/core/schemas`
     (see `docs/agents.md`) — done.
1.12 Agent Registry (config-driven, not hardcoded) in `packages/core` —
     done.
1.13 LangGraph graph in `workflows/graph.py`, embedded in `apps/api` —
     not the hosted Platform server — done. Full stage sequence wired
     (research → knowledge → idea-scoring gate → script → storyboard →
     recording → video → voice → mandatory approval gate → publish),
     using LangGraph's native `interrupt()`/`Command(resume=...)` for the
     approval gate. **Gotcha discovered and documented in-code:**
     LangGraph replays the whole superstep around an interrupt on
     resume (at-least-once, not exactly-once) — the real `agent_events`
     writes in Phase 2+ must be idempotent (e.g. `ON CONFLICT DO
     NOTHING` keyed on `(run_id, event_type)`), not assume single
     execution. See `workflows/graph.py` `final_review_node` comment.
1.14 WebSocket endpoint for streaming `agent_events` — done (in-process
     broadcaster for now; swap for real Redis Streams pub/sub once
     `services/orchestrator-worker` exists).
1.15 UI: "New Project" screen — URL paste only, no analysis yet — done.
1.16 UI: Project timeline view (event list) — done.
1.17 Ops view: `agent_runs` table — done.
1.18 Stub Agent (returns success immediately) to validate the full
     pipeline shape end-to-end — done, all 8 agents registered.
1.19 End-to-end smoke test: new project → runs through all Stub Agents →
     reaches `published` (faked) — done
     (`apps/api/tests/test_smoke_e2e.py`, 2 tests, both passing: the
     approval path reaching `published`, and the rejection path
     confirming nothing publishes without approval).

## Phase 2 — Research + Knowledge + Trend Agents

2.1 LiteLLM self-hosted, embedded in `apps/api` — provider abstraction
    (`providers/llm/`), Claude as first configured provider — **done**
    (`providers/llm/llm_provider/client.py`; `<provider>/<model>` naming
    convention required by LiteLLM's router, e.g.
    `anthropic/claude-3-5-sonnet-20241022`).
2.2 `providers/crawl/`: Crawl4AI (default) + Firecrawl self-hosted
    (JS-heavy/anti-bot fallback).
2.3 `providers/search/`: Tavily (default) + self-hosted SearXNG
    (high-volume/exploratory).
2.4 Research Agent v1: GitHub repo → Gitingest/Repomix digest → LLM
    summary — **done**
    (`agents/research_agent/agent.py`, `agents/research_agent/
    github_source.py`; Gitingest's async `ingest_async()` required —
    its sync wrapper calls `asyncio.run()` internally and breaks inside
    an Agent's already-running event loop, see the comment in
    `github_source.py`). Output persisted to the `research_notes` table
    (`apps/api/app/services/research.py`, migration
    `7f805ed657bb_add_research_notes_table.py`). `workflows/graph.py`'s
    `research_node` updated to forward `project.source_type`/
    `source_url` into the Agent's payload — the Stub Agent it replaced
    never read its input, which hid this wiring gap until the real Agent
    needed it (see `_agent_event`'s docstring in `workflows/graph.py`).
    Tests: `agents/research_agent/tests/` (unit, mocked LLM + digest,
    plus one `@pytest.mark.integration` live-network check),
    `apps/api/tests/test_smoke_e2e.py` (graph wiring),
    `apps/api/tests/test_research_persistence.py` (DB persistence).
2.5 Research Agent v2: YouTube URL → transcript → summary — **done**,
    revised approach (`docs/decisions.md` ADR-013): fetches YouTube's
    own captions via `youtube-transcript-api`
    (`agents/research_agent/youtube_source.py`) instead of the
    originally-specced faster-whisper (audio download + local STT model)
    — no audio processing, no local model, no GPU, works for the
    overwhelming majority of videos. `agents/research_agent/agent.py`'s
    `run()` now branches on `source_type` (`SUPPORTED_SOURCE_TYPES =
    ("github", "youtube")`); summarization logic shared via `_summarize()`
    rather than duplicated per source type. Tests:
    `agents/research_agent/tests/test_youtube_source.py` (URL parsing,
    transcript fetch, mocked), `test_agent.py`'s youtube-path tests. No
    live-network integration test exists for this one — this sandbox's
    network allowlist doesn't include youtube.com at all (unlike
    github.com for the Gitingest case), see `youtube_source.py`'s
    docstring.
2.6 Idea Scoring rubric written down explicitly (novelty, audience
    relevance, source reliability, visual potential) — not just a
    freeform prompt — **done**
    (`workflows/idea_scoring.py`, rubric text in `docs/agents.md` 'Idea
    scoring rubric'; 4 criteria scored 0-25 each by the LLM, summed in
    code rather than asked of the LLM as one number).
2.7 `interest_score` Gate: below threshold → `idea.rejected`, pipeline
    stops (cost control, see `docs/decisions.md` ADR-003) — **done**
    (`workflows/graph.py`'s `idea_scoring_node`/`route_after_scoring`,
    unchanged threshold logic — only what feeds it is now real. A
    project with no Research Agent output to score is scored 0.0
    automatically, same as an explicit rubric failure. Score persisted
    onto the existing `research_notes` row via
    `apps/api/app/services/research.py`'s `update_idea_score()`.
    Tests: `workflows/tests/test_idea_scoring.py` (rubric parsing/
    errors, mocked LLM), `apps/api/tests/test_smoke_e2e.py` (gate
    routing), `apps/api/tests/test_research_persistence.py` (score
    persistence)).
2.8 Knowledge Agent: chunking + embedding — **custom thin layer**, not
    LlamaIndex/Haystack (see ADR-002) — writes to Qdrant `knowledge_docs`.
    **Done.** `packages/memory` (`chunking.py`'s `chunk_text()` — word-
    count chunks with overlap, no tokenizer dependency; `store.py`'s
    `MemoryStore` — thin qdrant-client wrapper, `upsert_document()`/
    `search()`/`delete_source()`). Embeddings via `providers/llm`'s new
    `embed()` (Voyage AI, Oren-approved — no prior doc specified an
    embedding provider; paired through LiteLLM same as the LLM provider).
    `agents/knowledge_agent/agent.py` replaces its Phase 1.18 stub: reads
    `payload.text`/`source_id`/`project_id`/`source_type`/`source_url`,
    chunks + embeds + upserts, emits `source.ingested`; skips (no event)
    when there's no text to index, same "skip, don't crash" convention as
    Research Agent. `workflows/graph.py`'s `knowledge_node` now builds
    that payload from `StudioState.research_raw_text` (a new field —
    Research Agent's result now includes `raw_text`, the full digest/
    transcript, not just the LLM summary) — this is the same class of fix
    as 2.3's research_node payload bug: a Stub Agent ignoring its input
    hid a wiring gap that only broke once real logic depended on it, so
    `source.ingested` no longer fires unconditionally.

    `source_id` is currently `run_id` (`agent_runs.id`, a real Postgres
    row) rather than a real `sources.id` — there's no live orchestrator-
    worker persisting `sources` rows yet (same "not built yet" gap noted
    in `apps/api/app/services/research.py`'s docstring for
    `research_notes`). ADR-008's point-ID requirement is satisfied via a
    deterministic derivation (`uuid5(source_id, chunk_index)`, since one
    row chunks into N vectors) rather than literal ID equality — see
    `packages/memory/memory/store.py`'s module docstring. Revisit once
    Source persistence is wired to a real orchestrator.

    Tests: `packages/memory/tests/` (chunking edge cases; store round-
    trip/project_id filtering/idempotent re-upsert/delete, against real
    qdrant-client embedded-mode, embeddings mocked), `providers/llm/
    tests/test_client.py` (`embed()`, mocked at the litellm boundary),
    `agents/knowledge_agent/tests/test_agent.py` (skip/fail/success paths,
    `_build_store` mocked), `apps/api/tests/test_smoke_e2e.py`'s
    `test_knowledge_node_passes_research_output_to_real_agent` (payload
    wiring end-to-end) and updated
    `test_low_score_idea_is_rejected_before_final_review` (event list no
    longer includes `source.ingested` for a skipped run).
2.9 Knowledge Agent: semantic search endpoint. **Done.**
    `GET /api/knowledge/search?q=...&project_id=...&limit=...`
    (`apps/api/app/routers/knowledge.py`, `app/services/knowledge.py`).
    Returns Qdrant's own payload (text/score/source metadata) directly
    rather than the "Qdrant + Postgres hydrate" full version `docs/
    api.md` describes — hydration needs a real `sources` table row to
    hydrate *from*, which doesn't exist yet (see 2.8's note above); this
    is the same incremental-persistence pattern as `research_notes`,
    just further along the "not built yet" chain. Revisit this route the
    same day Source persistence lands. 503 (not 500/4xx) on a down/
    unreachable Qdrant — a service dependency failure, not a client
    error. Tests: `apps/api/tests/test_knowledge_search.py`.
2.10 Trend Agent v1–v3: GitHub Trending, Hacker News, Product Hunt (free
     sources first). **v1 (GitHub Trending) done** —
     `agents/trend_agent/github_trending_source.py` scrapes
     `github.com/trending` directly with BeautifulSoup (no official
     trending API exists, and github.com is the one external domain
     this project's sandbox network allowlist actually includes — see
     that module's docstring); `agents/trend_agent/agent.py` returns a
     list of candidate ideas (title, source_url, description, language
     tag, star counts). Unlike every other Agent so far, Trend Agent is
     **not** a `workflows/graph.py` node — it discovers ideas independent
     of any project (`docs/database.md`'s `ideas.project_id` is nullable
     for exactly this), so it's triggered separately (a scheduler or a
     manual "scan now" route, neither built yet). No `ideas` table row is
     written yet either — same incremental-persistence call as
     `research_notes` (2.4): land the discovery logic first, wire it to a
     table once the Idea Backlog UI (2.13) exists to shape that schema
     around. Hacker News (v2) and Product Hunt (v3) not started. Tests:
     `agents/trend_agent/tests/` (parser + agent, mocked HTML, plus one
     `@pytest.mark.integration` live fetch against the real page).
2.11 Trend Agent v4 (later): Reddit.
2.12 Trend Agent v5 (deliberately deferred): Twitter/X — cost-gate check
     before building.
2.13 UI: Idea Backlog / Kanban board (`ideas.stage`).
2.14 End-to-end test: real repo → Research → Knowledge indexed → Idea
     scored.

## Phase 3 — Script + Storyboard

3.1 `style_profile` v0 — manual one-time questionnaire (tone, length,
    favorite openers/closers). **Done.** `apps/api/app/models.py`'s
    `StyleProfile` (table `style_profile`, matching docs/database.md;
    `opening_patterns`/`closing_patterns` stored as JSON lists rather
    than Postgres `TEXT[]` — same engine-agnostic simplification
    `ResearchNote.key_points` already uses). Versioned, not updated in
    place — `app/services/style_profile.py`'s `create_style_profile()`
    always inserts at `max(version) + 1`; `get_current_style_profile()`
    reads the highest version. Routes: `POST /api/style-profile`
    (create), `GET /api/style-profile/current` (404 if none exists yet)
    — the GET was already in docs/api.md's route list; POST is a
    symmetric addition documented alongside it.

    Oren's actual v0 answers (collected via chat, 2026-07-12): tone is a
    mix of energetic/fast, professional/precise, and friendly/
    conversational — not one single register; length 30-45 seconds;
    opening patterns `"הי חברים תראו מה מצאתי"` / `"ידעתם שיש כזה דבר?"`;
    closing patterns `"אהבתם, רוצים עוד? תעקבו"` / `"ללינק כתבו לי
    בתגובות"`. Seeded via `scripts/seed_style_profile.py` — run once
    against a migrated database (not yet run against a real Postgres
    instance, since none is live from this sandbox; verified end-to-end
    against a throwaway SQLite DB instead, Hebrew text round-tripping
    correctly through JSON storage).

    Migration: `apps/api/alembic/versions/c3a9f1d8e2b4_add_style_profile_
    table.py`. Tests: `apps/api/tests/test_style_profile.py` (9 cases —
    versioning, current-lookup, both routes, 404, auth).
3.2–3.4 Script Agent: Hook, Body+CTA, Caption/Title/Hashtags. **Done —
    implemented as one Agent, one structured LLM call**, not three
    separate steps: the six fields aren't independent (caption
    references the hook, hashtags follow the body's topic), and
    docs/agents.md's roster already describes this as one Agent's job;
    `docs/database.md`'s `scripts` row stores all six together too. Same
    architectural choice as `workflows/idea_scoring.py` combining four
    rubric criteria into one call rather than four.

    `agents/script_agent/agent.py`: strict-JSON response (same
    `_extract_json` markdown-fence-stripping pattern as
    `workflows/idea_scoring.py`), all six fields required
    (`hook`/`body`/`cta`/`caption`/`title`/`hashtags`); missing/malformed
    response -> `status="failed"`, no `research_summary` in payload ->
    `status="skipped"` (mirrors Research Agent's own convention). Writes
    in Hebrew — Research Agent's summary/key_points stay English on
    purpose (see that Agent's system prompts), translation happens here.
    Folds in whatever `style_*` fields the caller provides
    (`style_tone_notes`/`style_opening_patterns`/`style_closing_patterns`/
    `style_avg_length_seconds`) alongside `docs/vision.md`'s baseline
    style guide (short, fast, clear, technical, hook within 3 seconds);
    works with the baseline alone if no style_profile exists yet — the
    questionnaire (3.1) is one-time but not mandatory-before-first-use.

    `workflows/graph.py`: `StudioState` gained `style_tone_notes`/
    `style_opening_patterns`/`style_closing_patterns`/
    `style_avg_length_seconds` (seeded by whichever caller invokes the
    graph — the graph itself never touches the DB, same reasoning as
    `knowledge_node`'s `source_id` comment) and `script_hook`/`script_body`/
    `script_cta`/`script_caption`/`script_title`/`script_hashtags`
    (promoted from a successful run, for the future Storyboard Agent and
    test visibility). `script_node` now builds a real payload instead of
    the empty-`{}` default every Stub Agent got.

    Persistence: `apps/api/app/models.py`'s `Script` (table `scripts`,
    matching docs/database.md; `hashtags` stored as JSON, same
    simplification as `style_profile`'s pattern fields).
    `apps/api/app/services/script.py`'s `persist_script()` — same
    decoupled-from-the-graph shape as `persist_research_note`, and (a
    first) actually links `style_profile_id` to a real row now that
    Phase 3.1 exists. Migration:
    `apps/api/alembic/versions/f4b1e6c8a9d3_add_scripts_table.py`.

    Tests: `agents/script_agent/tests/test_agent.py` (10 cases),
    `apps/api/tests/test_script_persistence.py` (4 cases),
    `apps/api/tests/test_smoke_e2e.py`'s
    `test_script_node_passes_research_and_style_fields_to_real_agent`
    (payload wiring end-to-end, including style_* fields). Full suite:
    106 tests passing (`make test`).
3.5 Prompt Library UI (CRUD + versioning).
3.6 Approval Gate #1: review/edit script before continuing.
3.7 Storyboard Agent: **custom LLM-prompting module** (structured JSON:
    scene, duration, visual instruction, caption cue) — no mature OSS
    library exists for this (see `docs/open-source-landscape.md` section
    4), budget real implementation time here.
3.8 UI: Storyboard view (scene list + preview).
3.9 Approved scripts feed `personal_style` in Qdrant.
3.10 End-to-end test: approved idea → script → storyboard shown for
     approval.

## Phase 3.5 — Hebrew RTL Caption Rendering Spike ⚠️ New, mandatory gate before Phase 4

A confirmed, open MoviePy bug mangles RTL text; ffmpeg+libass can work but
only if compiled with `--enable-libfribidi`, unverified by default.

3.5.1 Render a test caption (mixed Hebrew/English/digits) through
      ffmpeg+libass+fribidi.
3.5.2 Render the same test caption through a Remotion caption component
      (Chromium-based, native Unicode bidi).
3.5.3 Compare visually. Pick a winner based on evidence, not on a
      README's claims.
3.5.4 Record the decision in `docs/decisions.md` before writing any
      Video Agent caption code.

## Phase 4 — Production (Recording / Avatar / Video / Voice)

4.1 Recording Agent v0 (**manual**): upload screen for self-filmed video.
4.2 Video Agent v1: Auto-Editor for dead-air/silence trimming.
4.3 Video Agent v2: FFmpeg-based trim/concat per storyboard timing.
4.4 Video Agent v3: captions, burned in using whichever renderer won
    Phase 3.5.
4.5 Video Agent v4: B-roll/screenshot overlay, zoom, cursor highlight
    (FFmpeg filters).
4.6 Thumbnail Agent: FFmpeg frame extraction + Pillow/Remotion text
    overlay (no mature dedicated OSS tool exists — see landscape doc).
4.7 STT: faster-whisper + `ivrit-ai` Hebrew fine-tuned checkpoint —
    adopted as-is, no further evaluation needed.
4.8 OCR (for screenshot/tweet-image sources): Tesseract with `heb`
    trained data.
4.9 Voice Agent v1: **commercial API default** (e.g. ElevenLabs) for
    Hebrew voiceover/cloning — see ADR-004. Do not build on XTTS/Fish
    Speech (non-commercial licenses, one issuer defunct).
4.10 Voice Agent v1b (cost-reduction side project, not blocking): test
     OpenVoice (MIT) on a real Hebrew sample; only pursue self-hosting if
     quality is acceptable.
4.11 Recording Agent v1 (optional, later): MuseTalk (MIT) +
     LivePortrait (MIT code, replace the non-commercial InsightFace
     `buffalo_l` face-detection dependency first) for an avatar
     alternative to filming. Explicitly deferred — not a Phase 4 blocker.
4.12 Cost tracking middleware on every expensive Agent (Video/Voice/
     Avatar) — ties into LiteLLM's built-in cost tracking plus a custom
     wrapper for non-LLM provider costs.
4.13 LangGraph checkpointing verified against a real long-running render
     step (crash mid-render → resume without redoing work).
4.14 End-to-end test: approved storyboard → final video with captions and
     thumbnail.

## Phase 5 — Publishing + Approval (manual upload — see ADR-011)

5.1 Publishing Agent: assemble the final package for a project — video
    file, caption text, title, hashtags, thumbnail — into one clearly
    labeled per-project export folder.
5.2 UI: **preview screen** showing the post roughly as it will appear on
    the target platform (video + caption + hashtags together), so Oren
    reviews it in context, not as separate raw files.
5.3 Approval Gate #2 (mandatory): final review screen — video + caption +
    thumbnail together. Unchanged from the original plan.
5.4 DB constraint: `publications.published_at` cannot be set without
    `approved_at` (enforced at the database level, not just app code) —
    unchanged; still applies even though "published" now means "Oren
    uploaded it himself," not "the API call succeeded."
5.5 UI: after approval, a simple "ready to upload" state — one-click
    "open export folder," and a "mark as published" action Oren clicks
    once he's posted it manually (optionally pasting the resulting post
    URL into `publications.external_post_id` for record-keeping).
5.6 Full end-to-end test: source URL → ... → Oren's approval → export
    folder ready → Oren uploads manually → marked published.
5.7 (deferred, optional future upgrade) If/when automated scheduled
    posting is wanted: resume Phase 0.5 (platform API applications) and
    the Postiz integration from ADR-005 — nothing else in the
    architecture needs to change to add this later.

## Phase 6 — Self Learning

6.1 Define signals to collect (Like/Save/Share/what was filmed/what was
    edited in a proposed script).
6.2 Monthly batch job: analyze signals → propose a new `style_profile`
    version.
6.3 UI: Diff view to approve/reject the style update (PR-style, not
    silent auto-apply).
6.4 Recommendation Engine: daily idea suggestions from Trend + Preference
    signals.
6.5 Feedback loop: pull basic analytics (views/likes) from platforms
    post-publish.
6.6 Feed analytics into the Preference Engine as an additional signal.
6.7 Dashboard: "what the system learned about me this month" — full
    transparency, not a black box.
