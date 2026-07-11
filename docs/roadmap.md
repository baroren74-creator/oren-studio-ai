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

## Phase 0.5 — Publishing API Applications ⏳ Start immediately, run in parallel with everything else

This phase exists because it has the longest, least predictable external
lead time in the entire project (weeks to months) and does not depend on
any code being written. Starting it late turns it into the project's
critical-path bottleneck for no good reason.

0.5.1 Register Meta developer app; begin Instagram + Facebook App Review
      (`instagram_business_basic`, `instagram_business_content_publish`,
      `pages_manage_posts`) — expect 2–6 weeks incl. Business Verification.
0.5.2 Register TikTok developer app; begin Content Posting API
      application (`video.publish` scope) — expect 2–6 weeks for initial
      approval, **then** a second compliance audit before public (non
      SELF_ONLY) posting is allowed. Start this one first — it's the
      longest.
0.5.3 Register Google Cloud project + YouTube Data API v3 — low friction
      at this project's volume (post-Dec-2025 quota pricing), no audit
      needed under ~100 uploads/day.
0.5.4 Register LinkedIn app, add "Share on LinkedIn" product
      (`w_member_social`, self-serve, personal profile only) — low
      friction, immediate.
0.5.5 Decide explicitly: is a LinkedIn **company page** actually required?
      If yes, budget 4 weeks–4 months and expect possible rejection
      (Marketing Developer Platform). If posting to Oren's personal
      profile is sufficient, skip this.
0.5.6 Track all four applications' status in `docs/decisions.md` as they
      progress — this phase can run for months in the background while
      Phases 1–4 proceed.

## Phase 1 — Project Initialization 🔄 In progress (this repo)

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
    `agent_events`, `approvals` (see `docs/database.md`).
1.9 FastAPI skeleton (`apps/api`) + health check + simple API-key auth.
1.10 Next.js skeleton (`apps/web`) + layout (Chat / Projects / Knowledge /
     Prompts / Settings).
1.11 `AgentInput`/`AgentOutput` Pydantic schemas in `packages/core/schemas`
     (see `docs/agents.md`).
1.12 Agent Registry (config-driven, not hardcoded) in `packages/core`.
1.13 LangGraph — empty graph definition in `workflows/` (nodes =
     placeholders, edges = the flow in `docs/api.md` section on Event
     Types), embedded in `apps/api` — not the hosted Platform server.
1.14 WebSocket endpoint for streaming `agent_events`.
1.15 UI: "New Project" screen — URL paste only, no analysis yet.
1.16 UI: Project timeline view (event list).
1.17 Ops view: `agent_runs` table.
1.18 Stub Agent (returns success immediately) to validate the full
     pipeline shape end-to-end.
1.19 End-to-end smoke test: new project → runs through all Stub Agents →
     reaches `published` (faked).

## Phase 2 — Research + Knowledge + Trend Agents

2.1 LiteLLM self-hosted, embedded in `apps/api` — provider abstraction
    (`providers/llm/`), Claude as first configured provider.
2.2 `providers/crawl/`: Crawl4AI (default) + Firecrawl self-hosted
    (JS-heavy/anti-bot fallback).
2.3 `providers/search/`: Tavily (default) + self-hosted SearXNG
    (high-volume/exploratory).
2.4 Research Agent v1: GitHub repo → Gitingest/Repomix digest → LLM
    summary.
2.5 Research Agent v2: YouTube URL → transcript (faster-whisper) →
    summary.
2.6 Idea Scoring rubric written down explicitly (novelty, audience
    relevance, source reliability, visual potential) — not just a
    freeform prompt.
2.7 `interest_score` Gate: below threshold → `idea.rejected`, pipeline
    stops (cost control, see `docs/decisions.md` ADR-003).
2.8 Knowledge Agent: chunking + embedding — **custom thin layer**, not
    LlamaIndex/Haystack (see ADR-002) — writes to Qdrant `knowledge_docs`.
2.9 Knowledge Agent: semantic search endpoint.
2.10 Trend Agent v1–v3: GitHub Trending, Hacker News, Product Hunt (free
     sources first).
2.11 Trend Agent v4 (later): Reddit.
2.12 Trend Agent v5 (deliberately deferred): Twitter/X — cost-gate check
     before building.
2.13 UI: Idea Backlog / Kanban board (`ideas.stage`).
2.14 End-to-end test: real repo → Research → Knowledge indexed → Idea
     scored.

## Phase 3 — Script + Storyboard

3.1 `style_profile` v0 — manual one-time questionnaire (tone, length,
    favorite openers/closers).
3.2–3.4 Script Agent: Hook, Body+CTA, Caption/Title/Hashtags.
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

## Phase 5 — Publishing + Approval

5.1 Adopt Postiz (self-hosted) for OAuth/scheduling plumbing across the
    5 target platforms — do not build this from scratch (see ADR-005).
5.2 Wire Postiz's publish action behind Oren Studio AI's own approval
    gate: content sits as a held/paused item until `approvals.status =
    approved` in Postgres, then the app calls Postiz's API to release it.
5.3 Approval Gate #2 (mandatory): final review screen — video + caption +
    thumbnail together.
5.4 DB constraint: `publications.published_at` cannot be set without
    `approved_at` (enforced at the database level, not just app code).
5.5 Connect Postiz to whichever Phase-0.5 platform credentials are ready
    by this point; platforms not yet approved simply stay disabled.
5.6 Scheduling (not just immediate publish).
5.7 Full end-to-end test: source URL → ... → Oren's approval → real
    publish.

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
