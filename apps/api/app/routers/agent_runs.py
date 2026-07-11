"""Agent run routes — powers the Ops view (docs/roadmap.md 1.17) and
manual/debug single-agent runs (docs/api.md).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.models import AgentRun
from app.schemas import AgentRunOut

router = APIRouter(prefix="/api/agent-runs", tags=["agent-runs"], dependencies=[Depends(require_api_key)])


@router.get("", response_model=list[AgentRunOut])
def list_agent_runs(db: Session = Depends(get_db)) -> list[AgentRun]:
    return list(db.scalars(select(AgentRun).order_by(AgentRun.started_at.desc())).all())


@router.get("/{run_id}", response_model=AgentRunOut)
def get_agent_run(run_id: str, db: Session = Depends(get_db)) -> AgentRun:
    run = db.get(AgentRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="agent run not found")
    return run
