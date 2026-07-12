"""Persistence for Script Agent output — docs/database.md's `scripts`
table. Same decoupled-from-the-graph shape as
apps/api/app/services/research.py: there's no orchestrator-worker
running workflows/graph.py in production yet, so this is written to be
called by whichever caller eventually does, consistently.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Script
from core.schemas.agent import AgentOutput


def persist_script(
    db: Session, *, project_id: str, output: AgentOutput, style_profile_id: str | None = None
) -> Script | None:
    """Write a `scripts` row for a successful Script Agent run.

    Returns None (and writes nothing) for any non-"success" status —
    same reasoning as `persist_research_note`: a "skipped" (no
    research_summary) or "failed" (LLM/parse error) run has nothing
    worth keeping here; re-running the Script Agent is the recovery
    path, not editing a partial row.

    `style_profile_id` is passed in by the caller rather than looked up
    here — this module doesn't know which style_profile version was
    actually used for a given run (that's workflows/graph.py's
    knowledge, threaded through StudioState), only how to persist the
    result. `None` is valid: agents/script_agent/agent.py works even
    with no style_profile yet."""
    if output.status != "success":
        return None

    script = Script(
        project_id=project_id,
        hook=output.result.get("hook"),
        body=output.result.get("body"),
        cta=output.result.get("cta"),
        caption=output.result.get("caption"),
        title=output.result.get("title"),
        hashtags=output.result.get("hashtags"),
        style_profile_id=style_profile_id,
    )
    db.add(script)
    db.commit()
    db.refresh(script)
    return script
