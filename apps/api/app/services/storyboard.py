"""Persistence for the Storyboard module's output — docs/database.md's
`storyboards` table. Same decoupled-from-the-graph shape as
apps/api/app/services/script.py: there's no orchestrator-worker running
workflows/graph.py in production yet, so this is written to be called by
whichever caller eventually does, consistently.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Storyboard


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
