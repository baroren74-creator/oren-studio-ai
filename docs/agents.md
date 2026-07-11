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
| Trend Agent | `agents/trend_agent` | Discovers new things: GitHub Trending, Hacker News, Product Hunt, Reddit, AI news, Twitter/X (deferred), YouTube, blogs. | feeds the Idea Backlog |
| Knowledge Agent | `agents/knowledge_agent` | Learns documentation/projects, indexes everything to Qdrant, answers from accumulated knowledge. | `source.ingested` |
| Script Agent | `agents/script_agent` | Writes Hook, Body, CTA, Caption, Title, Hashtags — in Oren's style (`style_profile`). | `script.drafted` |
| Recording Agent | `agents/recording_agent` | v0: manual upload. Later: drives an Avatar provider (MuseTalk/LivePortrait). | `recording.completed` |
| Video Agent | `agents/video_agent` | Cuts, zooms, captions, B-roll/screenshot overlay, cursor highlight, thumbnail. | `video.rendered`, `captions.generated`, `thumbnail.generated` |
| Voice Agent | `agents/voice_agent` | Voice enhancement, dubbing, translation, cloning (commercial API by default — ADR-004). | `voice.completed` |
| Publishing Agent | `agents/publishing_agent` | Prepares posts for Instagram/TikTok/YouTube Shorts/Facebook/LinkedIn via Postiz; never publishes without approval. | `publish.completed` |

Each Agent's exact `payload`/`result` schema is defined in its own
`agent.py` alongside its implementation — this table is the map, not the
territory. When an Agent's schema changes, update this table's
"Responsibility" column if the change is behavior-visible.

## Idea scoring rubric (owned by Research/Knowledge Agents, Phase 2.6)

To be filled in when Phase 2.6 is implemented — criteria: novelty,
relevance to Oren's stated interests, source reliability, visual
potential. Do not leave this as a bare LLM prompt without a written
rubric here (see ADR-003).
