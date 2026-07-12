"""Persistence for Research Agent output — docs/database.md's
`research_notes` table.

There's no orchestrator-worker service running the LangGraph graph in
production yet (docs/roadmap.md — that's a later phase); today,
workflows/graph.py is only ever invoked directly (currently from tests).
This module is deliberately small and decoupled from the graph itself so
that whichever caller eventually runs the graph for real — an API route,
a background worker, a test — persists Research Agent output the exact
same way, rather than duplicating this logic at each call site.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import ResearchNote
from core.schemas.agent import AgentOutput


def persist_research_note(
    db: Session, *, project_id: str, output: AgentOutput, agent_name: str, agent_version: str
) -> ResearchNote | None:
    """Write a `research_notes` row for a successful Research Agent run.

    Returns None (and writes nothing) for any non-"success" status —
    "skipped" (unsupported source_type, Phase 2.4+) and "failed" (fetch/
    LLM errors) runs have nothing worth keeping in research_notes; what
    happened is already captured in agent_runs/agent_events for
    debugging (docs/database.md), and re-running the Research Agent for
    the same project is the recovery path, not editing a partial note.

    `interest_score`/`scored_by`'s score half is left NULL here on
    purpose — Phase 2.3's Research Agent doesn't score ideas, Phase 2.6's
    idea-scoring rubric (docs/agents.md) does, as a later UPDATE of this
    same row rather than a new one.
    """
    if output.status != "success":
        return None

    note = ResearchNote(
        project_id=project_id,
        summary=output.result.get("summary"),
        key_points=output.result.get("key_points"),
        scored_by=f"{agent_name}@{agent_version}",
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def update_idea_score(db: Session, *, research_note_id: str, score) -> ResearchNote | None:
    """Fill in `interest_score`/`scored_by` on an existing research_notes
    row (docs/database.md) — the Phase 2.6/2.7 UPDATE this module's
    `persist_research_note` docstring said would come later.

    `score` is a `workflows.idea_scoring.IdeaScore` (typed loosely here,
    not imported, to avoid apps/api depending on workflows/ just for a
    type hint — the same "Agents never import each other" spirit applied
    one layer up: this module only needs `.total` and `.scored_by`).
    `scored_by` is overwritten to the idea-scoring module's version
    rather than kept as the Research Agent's — the score's provenance
    matters more here than the summary's, and they're allowed to differ
    (docs/database.md's `scored_by` is "agent version", singular, but
    doesn't mandate which agent when more than one touches a row).

    Returns None (writes nothing) if the row doesn't exist — the caller
    is responsible for having a valid research_note_id; this function
    doesn't create one implicitly."""
    note = db.get(ResearchNote, research_note_id)
    if note is None:
        return None

    note.interest_score = score.total
    note.scored_by = score.scored_by
    db.commit()
    db.refresh(note)
    return note
