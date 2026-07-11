"""Project routes — see docs/api.md 'REST — core routes'."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.models import AgentEvent, AgentRun, Project
from app.schemas import AgentEventOut, ProjectCreate, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["projects"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    project = Project(
        title=payload.title,
        status="draft",
        source_type=payload.source_type,
        source_url=payload.source_url,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.get("/{project_id}/timeline", response_model=list[AgentEventOut])
def get_project_timeline(project_id: str, db: Session = Depends(get_db)) -> list[AgentEvent]:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    run_ids = [r.id for r in db.scalars(select(AgentRun).where(AgentRun.project_id == project_id))]
    if not run_ids:
        return []
    events = db.scalars(
        select(AgentEvent).where(AgentEvent.run_id.in_(run_ids)).order_by(AgentEvent.created_at)
    ).all()
    return list(events)
