"""Persistence for the Storyboard module's output — docs/database.md's
`storyboards` table. Same decoupled-from-the-graph shape as
apps/api/app/services/script.py: there's no orchestrator-worker running
workflows/graph.py in production yet, so this is written to be called by
whichever caller eventually does, consistently.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Script, Storyboard


def persist_storyboard(db: Session, *, script_id: str, scenes: list[dict] | None) -> Storyboard | None:
    """Write a `storyboards` row for a successful Storyboard run.

    Returns None (and writes nothing) if `scenes` is empty/None — same
    reasoning as `persist_script`: a run with no script to storyboard
    (rejected idea) or a failed/unparseable Storyboard LLM call
    (workflows/storyboard.py's StoryboardError) has nothing worth keeping
    here; re-running is the recovery path, not editing a partial row.

    Unlike `persist_script`/`persist_research_note`, this doesn't take a
    raw `AgentOutput` — the Storyboard module isn't a registered Agent
    (see workflows/storyboard.py's module docstring), so
    workflows/graph.py's storyboard_node already hands back a plain
    `scenes` list rather than an AgentOutput-shaped result."""
    if not scenes:
        return None

    storyboard = Storyboard(script_id=script_id, scenes=scenes)
    db.add(storyboard)
    db.commit()
    db.refresh(storyboard)
    return storyboard


def get_latest_storyboard_for_project(db: Session, project_id: str) -> Storyboard | None:
    """Phase 3.8's Storyboard view needs to survive a page reload — the
    only place `storyboard_scenes` existed before this was
    `ProjectRunOut`, an ephemeral response to `POST .../run` that's gone
    the moment the browser tab refreshes. This walks project -> its most
    recently created Script -> that script's most recently created
    Storyboard (both "most recent" since neither is updated in place —
    same re-run convention as everywhere else in this file/module), so
    `GET /api/projects/{id}/storyboard` has something real to serve."""
    latest_script = db.scalar(
        select(Script).where(Script.project_id == project_id).order_by(Script.created_at.desc()).limit(1)
    )
    if latest_script is None:
        return None
    return db.scalar(
        select(Storyboard)
        .where(Storyboard.script_id == latest_script.id)
        .order_by(Storyboard.created_at.desc())
        .limit(1)
    )
