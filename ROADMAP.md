# Roadmap (pointer)

The full, granular roadmap lives at
[`docs/roadmap.md`](docs/roadmap.md) (Phases 0–6, broken into ~70 small
steps). This file is a high-level index so `git log`/GitHub browsing shows
progress at a glance.

| Phase | Name | Status |
|---|---|---|
| 0 | Architecture + Open Source Research | ✅ Done — see `docs/architecture.md`, `docs/open-source-landscape.md` |
| 0.5 | Publishing API applications (Instagram/Facebook/TikTok) | ⏸ Deferred — not needed for v1, see ADR-011 |
| 1 | Project Initialization (this repo skeleton) | ✅ Done — repo, infra config, and a tested code skeleton (API + web + orchestrator graph + 8 stub agents) all pushed to GitHub |
| 2 | Research + Knowledge + Trend Agents | 🟡 In progress — Research Agent v1/v2 (GitHub + YouTube), real Idea Scoring gate, Knowledge Agent (chunk/embed/index + semantic search), Trend Agent v1 (GitHub Trending) done, see `docs/roadmap.md` 2.4/2.5/2.6/2.7/2.8/2.9/2.10 |
| 3 | Script + Storyboard | 🟡 In progress — style_profile v0 (3.1), real Script Agent (3.2-3.4), orchestrator wiring + apps/web "Run" button (3.4.5), Prompt Library CRUD + versioning (3.5), Approval Gate #1 (3.6), and the Storyboard module (3.7) done, see `docs/roadmap.md` |
| 3.5 | Hebrew RTL caption rendering spike | ⬜ Not started |
| 4 | Production (Recording / Avatar / Video / Voice) | ⬜ Not started |
| 5 | Publishing + Approval (manual upload, see ADR-011) | ⬜ Not started |
| 6 | Self Learning | ⬜ Not started |

Update this table's status column as phases complete — it's the fastest
way to answer "where are we" without opening `docs/roadmap.md`.
