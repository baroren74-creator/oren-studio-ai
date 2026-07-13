"""Manual synchronous graph-run trigger — `POST /api/projects/{id}/run`.

This is the first place anything actually invokes `workflows/graph.py`'s
`build_graph()` outside of a test. ADR-001 explicitly allows LangGraph to
be "embedded directly inside `apps/api` / `services/orchestrator-worker`"
— `services/orchestrator-worker` (a separate Redis Streams consumer, so a
slow video render never blocks an HTTP request) is still "not
implemented yet" per its own README, and building that is real, separate
scope. This module is a deliberate, documented v0 shortcut: run the
graph synchronously, inside the request, using an in-memory
(`MemorySaver`) checkpointer. Good enough for a single-user studio where
"click run, wait a few seconds, see the result" is an acceptable UX for
now — revisit (background worker + Postgres-backed checkpointer) once a
run is slow enough, or once resuming an interrupted run from a *later*
request actually matters (`MemorySaver` doesn't survive past this
process's lifetime, so nothing can resume the mandatory approval gate
this way yet — that's Phase 3.6/5's dedicated scope, not this module's).

Persistence reuses the exact same decoupled service functions
(`persist_research_note`, `update_idea_score`, `persist_script`) that
already have their own test coverage — this module's only new
responsibility is reconstructing a synthetic `AgentOutput` from the
graph's final state to hand to them, since `workflows/graph.py` itself
never returns raw `AgentOutput`s to its caller (only the merged
`StudioState`).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from core.registry import AgentRegistry
from core.schemas.agent import AgentOutput
from workflows.graph import build_graph

from app.models import Project
from app.services.agent_runs import persist_agent_runs
from app.services.approvals import create_approval
from app.services.research import persist_research_note, update_idea_score
from app.services.script import persist_script
from app.services.storyboard import persist_storyboard
from app.services.style_profile import get_current_style_profile


class ProjectNotFoundError(Exception):
    """Raised when run_project() is given a project_id that doesn't
    exist — the route layer turns this into a 404."""


@dataclass
class _FinalScore:
    """Duck-types workflows.idea_scoring.IdeaScore's `.total`/`.scored_by`
    for update_idea_score() — same reasoning as apps/api/tests/
    test_research_persistence.py's _FakeIdeaScore: this module reads the
    score back out of graph state (a plain float), not the IdeaScore
    object itself, which workflows/graph.py's idea_scoring_node doesn't
    return to its caller either."""

    total: float
    scored_by: str = "idea_scoring@0.1.0 (via workflows/graph.py run)"


def run_project(db: Session, project_id: str, *, registry: AgentRegistry | None = None) -> dict:
    """Run the full studio graph for `project_id` once, synchronously,
    and persist whatever real Agent output resulted. Returns a plain
    dict (not an ORM object) — see app.schemas.ProjectRunOut for the
    matching API response shape.

    `registry` lets tests swap in an isolated all-stub/mocked registry
    (same escape hatch as `build_graph`'s own `registry` param) — the
    default (`None`) uses whichever Agents are registered on
    `core.registry.default_registry`, i.e. every real `agents/*/agent.py`
    module `apps/api/app/main.py` imports for its registration
    side-effect."""
    project = db.get(Project, project_id)
    if project is None:
        raise ProjectNotFoundError(project_id)

    style_profile = get_current_style_profile(db)

    run_id = str(uuid.uuid4())
    initial_state: dict = {
        "project_id": project.id,
        "run_id": run_id,
        "source_type": project.source_type,
        "source_url": project.source_url,
        "events": [],
    }
    if style_profile is not None:
        initial_state["style_tone_notes"] = style_profile.tone_notes
        initial_state["style_opening_patterns"] = style_profile.opening_patterns
        initial_state["style_closing_patterns"] = style_profile.closing_patterns
        initial_state["style_avg_length_seconds"] = style_profile.avg_length_seconds

    from langgraph.checkpoint.memory import MemorySaver

    graph = build_graph(registry=registry).compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": run_id}}
    final_state = graph.invoke(initial_state, config=config)

    research_note_id = None
    if final_state.get("research_summary"):
        research_output = AgentOutput(
            status="success",
            result={
                "summary": final_state["research_summary"],
                "key_points": final_state.get("research_key_points"),
            },
        )
        note = persist_research_note(
            db,
            project_id=project.id,
            output=research_output,
            agent_name="research_agent",
            agent_version="graph-run",
        )
        if note is not None:
            research_note_id = note.id
            if final_state.get("idea_score") is not None:
                update_idea_score(db, research_note_id=note.id, score=_FinalScore(total=final_state["idea_score"]))

    script_id = None
    script_result = None
    approval_id = None
    if final_state.get("script_hook"):
        script_result = {
            "hook": final_state.get("script_hook"),
            "body": final_state.get("script_body"),
            "cta": final_state.get("script_cta"),
            "caption": final_state.get("script_caption"),
            "title": final_state.get("script_title"),
            "hashtags": final_state.get("script_hashtags"),
        }
        script_output = AgentOutput(status="success", result=script_result)
        script = persist_script(
            db,
            project_id=project.id,
            output=script_output,
            style_profile_id=style_profile.id if style_profile else None,
        )
        if script is not None:
            script_id = script.id
            # Phase 3.6, Approval Gate #1: a drafted script always needs
            # a human decision before the studio treats it as final —
            # see app.services.approvals's module docstring for why this
            # is a plain DB row rather than a graph interrupt().
            approval = create_approval(db, project_id=project.id, stage="script")
            approval_id = approval.id

    # Phase 3.7: storyboard_node (workflows/graph.py) already skips
    # itself when there's no script_hook/script_body to work from
    # (rejected idea, or its own StoryboardError) — persist_storyboard
    # mirrors that same "nothing to keep" no-op for an empty scenes list,
    # so this call is safe even when script is None or storyboard_scenes
    # is empty.
    storyboard_id = None
    storyboard_scenes = final_state.get("storyboard_scenes")
    if script_id is not None:
        storyboard = persist_storyboard(db, script_id=script_id, scenes=storyboard_scenes)
        if storyboard is not None:
            storyboard_id = storyboard.id

    # Cost tracking (found live to be a real gap: every real Agent
    # already computes its own cost, but nothing previously persisted
    # it — see app.services.agent_runs's module docstring).
    agent_runs = persist_agent_runs(db, project_id=project.id, agent_costs=final_state.get("agent_costs", []))
    # AgentRun.cost_usd is a SQLAlchemy Numeric column — reads back as
    # decimal.Decimal, not float, on at least some backends. Cast
    # explicitly: Decimal + float raises TypeError, and this needs to be
    # a plain JSON-serializable number for ProjectRunOut anyway.
    total_cost_usd = sum(float(run.cost_usd or 0.0) for run in agent_runs)

    return {
        "run_id": run_id,
        "events": list(final_state.get("events", [])),
        "rejected": bool(final_state.get("rejected")),
        "interrupted": bool(final_state.get("__interrupt__")),
        "idea_score": final_state.get("idea_score"),
        "research_note_id": research_note_id,
        "script_id": script_id,
        "script": script_result,
        "approval_id": approval_id,
        "total_cost_usd": total_cost_usd,
        "storyboard_id": storyboard_id,
        "storyboard_scenes": storyboard_scenes,
    }
