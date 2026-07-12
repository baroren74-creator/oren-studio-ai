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
| Knowledge Agent | `agents/knowledge_agent` | Learns documentation/projects, indexes everything to Qdrant, answers from accumulated knowledge. | `source.ingested` |
| Script Agent | `agents/script_agent` | Writes Hook, Body, CTA, Caption, Title, Hashtags — in Oren's style (`style_profile`). | `script.drafted` |
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
registered Agent (no entry in the roster above) — like the future
Storyboard step (Phase 3.7), it's a custom LLM-prompting module wired
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
