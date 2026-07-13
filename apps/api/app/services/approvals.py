"""Persistence for human approval gates — docs/database.md's
`approvals` table (already migrated in Phase 1), Phase 3.6's "Approval
Gate #1: review/edit script before continuing."

Deliberately NOT wired through `workflows/graph.py`'s `interrupt()`
mechanism the way Approval Gate #2 (`final_review_node`) is, even
though that would be the more "correct" long-term design per ADR-001.
Two reasons, both explained in full in that node's own comment and in
`app/services/orchestrator.py`:

1. `run_project()`'s v0 shortcut builds a fresh `MemorySaver()` on every
   HTTP request, so a graph paused mid-request by `interrupt()` has
   nowhere to resume *from* on a later request — that checkpoint dies
   with the request. This is a pre-existing gap already latent in
   Approval Gate #2, not something new introduced here.
2. Nothing of real consequence happens after script drafting yet —
   `storyboard_node` (Phase 3.7, not built) and the recording/video/
   voice nodes are all still Stub Agents. Gating a graph resume that
   doesn't do anything meaningful isn't worth solving the harder
   persistent-checkpointer problem for right now.

So Approval Gate #1 is a standalone, DB-backed review step: a `Script`
being persisted (`app/services/orchestrator.py`) creates a `pending`
`Approval` row alongside it; Oren approves/rejects/requests edits via
these functions and the matching routes, independent of the graph.
Revisit once Phase 3.7 makes "continuing past the gate" mean something,
and once a persistent checkpointer (or the real
`services/orchestrator-worker`) makes an actual graph resume possible.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Approval


class ApprovalNotFoundError(Exception):
    """Raised when an approvals id doesn't exist — the route layer
    turns this into a 404."""


def create_approval(db: Session, *, project_id: str, stage: str) -> Approval:
    """Always starts `pending` — decide_approval() is the only way to
    move it out of that state."""
    approval = Approval(project_id=project_id, stage=stage, status="pending")
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


def get_approval(db: Session, approval_id: str) -> Approval | None:
    return db.get(Approval, approval_id)


def list_approvals_for_project(db: Session, project_id: str) -> list[Approval]:
    # `approvals` has no created_at column (docs/database.md — not added
    # here since that's a schema change beyond this feature's scope).
    # Ordering by decided_at puts NULL (still-pending) rows first on
    # both SQLite and Postgres, which conveniently surfaces the row a
    # caller most likely wants — "is there something waiting on me?" —
    # without a dedicated "pending first" query.
    return list(
        db.scalars(select(Approval).where(Approval.project_id == project_id).order_by(Approval.decided_at))
    )


def decide_approval(db: Session, approval_id: str, *, status: str, notes: str | None = None) -> Approval:
    """`status` is one of "approved"/"rejected"/"edited" (docs/api.md's
    approval state machine — "edited" is what `request-edit` sets, since
    the notes describe what needs to change, not a final accept/reject).
    Raises `ApprovalNotFoundError` if `approval_id` doesn't exist."""
    approval = db.get(Approval, approval_id)
    if approval is None:
        raise ApprovalNotFoundError(approval_id)
    approval.status = status
    approval.notes = notes
    approval.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(approval)
    return approval
