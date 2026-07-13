# API Reference

Living reference for `apps/api`'s external contract and the internal
event flow. Update in the same PR that changes a route or adds an event
type (see `CONTRIBUTING.md`).

## REST — core routes

```
POST   /api/projects                     create a project from a source
GET    /api/projects                     list all, most recent first — done. apps/web's Projects page
                                          uses this (a real gap found live: previously no way back to
                                          a project you'd already created, only the New Project form)
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
                                          idea_score, research_note_id, script_id, script, approval_id,
                                          total_cost_usd, storyboard_id, storyboard_scenes. A successfully
                                          persisted Script always creates a pending Approval(stage="script")
                                          alongside it — see below. A successfully persisted Script also
                                          gets a Storyboard row (workflows/storyboard.py's
                                          generate_storyboard(), not a registered Agent — see that module's
                                          docstring) linked by script_id; storyboard_scenes is null when
                                          there was no script, or the Storyboard LLM call failed/produced
                                          nothing usable.
                                          Also persists a real agent_runs row per Agent/scoring call made
                                          during the run (apps/api/app/services/agent_runs.py) — this is
                                          what powers GET /api/agent-runs and apps/web's Ops page total.
GET    /api/projects/{id}/approvals      all approvals for a project, still-pending ones first — done
                                          (Phase 3.6)

POST   /api/agents/{agent_name}/run      manual/debug run of a single agent
GET    /api/agent-runs/{id}

POST   /api/approvals/{id}/approve       done (Phase 3.6) — sets status=approved, decided_at=now
POST   /api/approvals/{id}/reject        done — sets status=rejected, decided_at=now
POST   /api/approvals/{id}/request-edit  {notes}  done — sets status=edited, notes, decided_at=now.
                                          See apps/api/app/services/approvals.py's module docstring for
                                          why this is a standalone DB-backed gate (Approval Gate #1) rather
                                          than workflows/graph.py's interrupt()/resume mechanism — the v0
                                          synchronous orchestrator has no persistent checkpointer to
                                          resume a paused run from on a later request, and nothing after
                                          script drafting is real yet (storyboard/recording/video/voice
                                          are still Stub Agents), so there's nothing to meaningfully gate
                                          a resume of.

GET    /api/knowledge/search?q=...       semantic search — done (Phase 2.9), currently returns Qdrant's
                                          own payload, not yet Postgres-hydrated (no sources rows persisted
                                          yet — see docs/agents.md's Knowledge Agent section)
POST   /api/prompt-library                start a new prompt at version 1 — done (Phase 3.5)
GET    /api/prompt-library                 current (highest) version of every prompt — done
GET    /api/prompt-library/{id}            one specific version, any version — done
GET    /api/prompt-library/{id}/history    full version chain for that prompt's family, oldest first — done
POST   /api/prompt-library/{id}/versions   edit = new version (parent_id set), never an in-place update — done
DELETE /api/prompt-library/{id}            removes every version in the family, not just one — done
                                            See apps/api/app/services/prompt_library.py's module docstring
                                            for the versioning model. apps/web's Prompts page renders a diff
                                            between versions per docs/architecture.md section 9.5.
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
