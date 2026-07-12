# API Reference

Living reference for `apps/api`'s external contract and the internal
event flow. Update in the same PR that changes a route or adds an event
type (see `CONTRIBUTING.md`).

## REST — core routes

```
POST   /api/projects                     create a project from a source
GET    /api/projects/{id}
GET    /api/projects/{id}/timeline       all agent_events, chronological
POST   /api/projects/{id}/run            v0 synchronous graph run — done (Phase 3.4.5), see
                                          apps/api/app/services/orchestrator.py's module docstring.
                                          Runs the full studio graph in-request (LangGraph +
                                          MemorySaver, no queue/retry — ADR-001 permits embedding
                                          directly in apps/api; this is not the eventual
                                          services/orchestrator-worker). Persists a ResearchNote
                                          and, if the idea passed scoring, a Script. Returns
                                          ProjectRunOut: run_id, events, rejected, interrupted,
                                          idea_score, research_note_id, script_id, script.

POST   /api/agents/{agent_name}/run      manual/debug run of a single agent
GET    /api/agent-runs/{id}

POST   /api/approvals/{id}/approve
POST   /api/approvals/{id}/reject
POST   /api/approvals/{id}/request-edit  {notes}

GET    /api/knowledge/search?q=...       semantic search — done (Phase 2.9), currently returns Qdrant's
                                          own payload, not yet Postgres-hydrated (no sources rows persisted
                                          yet — see docs/agents.md's Knowledge Agent section)
POST   /api/prompt-library
POST   /api/style-profile                create a new version (Phase 3.1's questionnaire) — done
GET    /api/style-profile/current        highest version, 404 if none created yet — done
```

Auth: `STUDIO_API_KEY` header (see ADR-006). No OAuth/session layer in
the MVP.

## WebSocket

```
WS /ws/projects/{id}/events
→ real-time stream of agent_events (drives the Studio UI progress bar:
  "Research Agent: reading README... 40%")
```

## Internal Agent envelope (Orchestrator ↔ Agent)

Always `AgentInput` in, `AgentOutput` out — see `docs/agents.md` for the
exact schema. The Orchestrator is the only component that knows the graph
order; an individual Agent never knows "what comes after it."

## Event types

On Redis Streams, also persisted to `agent_events` (see
`docs/database.md`). This is the canonical list — every event an Agent
emits must appear here.

```
trend.discovered         → Trend Agent — not part of the per-project pipeline below, see docs/agents.md
source.ingested          → Knowledge Agent — chunks/embeds/upserts into Qdrant, see docs/agents.md
research.completed
idea.scored              → below threshold: idea.rejected (stops here, see ADR-003)
script.drafted
script.approved          → Approval Gate #1 (optional, skippable)
storyboard.ready
assets.ready
recording.requested → recording.completed   (or avatar.requested → avatar.completed)
voice.completed
video.rendered
captions.generated
thumbnail.generated
caption.text.ready
final_review.requested   → Approval Gate #2 (mandatory)
publish.approved         → export folder + preview marked ready (ADR-011)
publish.completed        → Oren manually confirms he uploaded it (not an API callback)
```

On any `*.failed` event, the Orchestrator applies retry policy
(exponential backoff, capped) before surfacing the failure in the Ops
view — see `docs/standards.md` section 8 (error handling).

## Approval state machine

```
draft → pending_approval → approved → published
                        ↘ rejected (returns to the previous stage with notes)
```

Enforced at the database level (`docs/database.md`,
`publications.published_at` requires `approved_at`), not only in
application code. As of ADR-011, `published` is set by Oren himself
after he manually uploads via the platform's own app — there is no
publish API call in v1 (see ADR-005 for the original automated-publish
design, kept as a documented future option).
