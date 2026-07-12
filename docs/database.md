# Database Reference

PostgreSQL is the single source of truth for the entire system (ADR-008).
Qdrant holds vector embeddings only, indexed by the same IDs used here —
never authoritative on its own. Update this file in the same PR as any
migration (see `CONTRIBUTING.md`).

## Content core

```sql
projects (
  id UUID PK,
  title TEXT,
  status TEXT,              -- draft|researching|scripting|producing|review|published|archived
  source_type TEXT,         -- github|youtube|reel|post|tweet|website|idea
  source_url TEXT,
  created_at, updated_at
)

sources (
  id UUID PK,
  project_id FK,
  type TEXT,                 -- repo|video|article|post
  raw_url TEXT,
  fetched_content JSONB,      -- transcript / README / scraped text
  fetched_at TIMESTAMPTZ
)

research_notes (
  id UUID PK,
  project_id FK,
  summary TEXT,
  key_points JSONB,
  interest_score NUMERIC,     -- gates progression, see ADR-003
  scored_by TEXT,              -- agent version
  created_at
)

ideas (
  id UUID PK,
  project_id FK NULL,
  title TEXT,
  stage TEXT,                  -- new|researched|scored|approved|scripted|produced|published|archived|rejected
  virality_score NUMERIC,
  tags TEXT[],
  created_at
)

scripts (                    -- implemented Phase 3.2-3.4, apps/api/app/models.py's Script
  id UUID PK,
  project_id FK,
  hook TEXT,
  body TEXT,
  cta TEXT,
  caption TEXT,
  title TEXT,
  hashtags TEXT[],           -- stored as JSON in code, same simplification as style_profile
  style_profile_id FK,       -- nullable: Script Agent works even with no style_profile yet
  version INT,
  created_at
)

storyboards (
  id UUID PK,
  script_id FK,
  scenes JSONB                   -- [{order, description, visual_ref, duration}]
)

assets (
  id UUID PK,
  project_id FK,
  type TEXT,                     -- video_raw|broll|screenshot|thumbnail|voiceover|caption_file
  storage_url TEXT,               -- S3 path
  metadata JSONB,
  created_at
)

videos (
  id UUID PK,
  project_id FK,
  status TEXT,                    -- rendering|ready|failed
  final_url TEXT,
  duration_seconds NUMERIC,
  provider TEXT,
  created_at
)

publications (
  id UUID PK,
  project_id FK,
  video_id FK,
  platform TEXT,                    -- instagram|tiktok|youtube_shorts|facebook|linkedin
  status TEXT,                       -- pending_approval|approved|scheduled|published|failed
  approved_at TIMESTAMPTZ NULL,      -- NULL = cannot publish, enforced by DB constraint
  approved_by TEXT DEFAULT 'oren',
  published_at TIMESTAMPTZ NULL,
  external_post_id TEXT,
  created_at
)
```

## Agent runtime / observability

```sql
agent_runs (
  id UUID PK,
  project_id FK,
  agent_name TEXT,
  status TEXT,                      -- running|success|failed|needs_approval
  input JSONB,
  output JSONB,
  cost_usd NUMERIC,
  tokens_used INT,
  started_at, finished_at
)

agent_events (
  id UUID PK,
  run_id FK,
  event_type TEXT,                  -- see docs/api.md Event Types
  payload JSONB,
  created_at
)

approvals (
  id UUID PK,
  project_id FK,
  stage TEXT,                        -- script|storyboard|final_video|publish
  status TEXT,                        -- pending|approved|rejected|edited
  notes TEXT,
  decided_at TIMESTAMPTZ
)
```

## Memory / knowledge

```sql
memory_entries (
  id UUID PK,
  type TEXT,                          -- fact|preference|habit|repeated_topic
  content TEXT,
  confidence NUMERIC,
  source_run_id FK NULL,
  created_at, updated_at
)

style_profile (              -- implemented Phase 3.1, apps/api/app/models.py's StyleProfile
  id UUID PK,
  version INT,
  tone_notes TEXT,
  opening_patterns TEXT[],   -- stored as JSON in code (SQLite/Postgres-agnostic), not a native array
  closing_patterns TEXT[],   -- same
  avg_length_seconds NUMERIC,
  vocabulary_notes JSONB,
  updated_at
)

prompt_library (
  id UUID PK,
  name TEXT,
  category TEXT,
  prompt_text TEXT,
  version INT,
  parent_id FK NULL,
  created_at
)

favorite_tools (
  id UUID PK,
  name TEXT,
  category TEXT,
  notes TEXT,
  saved_at
)

brand_assets (
  id UUID PK,
  type TEXT,                           -- logo|font|color_palette|intro_outro
  storage_url TEXT,
  metadata JSONB
)
```

## Qdrant collections (index only — every point ID = a Postgres row ID)

| Collection | Content | Source table |
|---|---|---|
| `knowledge_docs` | Documentation/README/article chunks | `sources.id` |
| `transcripts` | Video/reel transcripts | `sources.id` |
| `personal_style` | Approved script fragments | `scripts.id` |
| `prompt_library` | Semantic search over the prompt library | `prompt_library.id` |
| `preferences` | Summarized Like/Save/Share signals | `memory_entries.id` |

Rebuilding any Qdrant collection from Postgres must always be possible —
if it isn't, that's a bug (ADR-008).

`knowledge_docs` is implemented (Phase 2.8, `packages/memory`). Two notes
on how "every point ID = a Postgres row ID" plays out once chunking is
involved, and while `sources` rows aren't persisted yet — see
`docs/agents.md`'s Knowledge Agent section for the full reasoning:
point IDs are `uuid5(source_id, chunk_index)` (deterministic, since one
row chunks into N vectors, not literal equality), and `source_id` is
currently `agent_runs.id` rather than `sources.id` (no live orchestrator-
worker persists `sources` rows yet). Both are pragmatic stand-ins to
revisit together once Source persistence lands.

## Migrations

Alembic, linear and ordered, one direction. Never edit an already-applied
migration — write a new one. First migration set (Phase 1.8):
`projects`, `sources`, `agent_runs`, `agent_events`, `approvals`.
