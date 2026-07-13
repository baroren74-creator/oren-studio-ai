"""Project routes — see docs/api.md 'REST — core routes'."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_api_key
from app.models import AgentEvent, AgentRun, Project
from app.schemas import AgentEventOut, ApprovalOut, ProjectCreate, ProjectOut, ProjectRunOut, StoryboardOut
from app.services.approvals import list_approvals_for_project
from app.services.orchestrator import ProjectNotFoundError, run_project
from app.services.storyboard import get_latest_storyboard_for_project

router = APIRouter(prefix="/api/projects", tags=["projects"], dependencies=[Depends(require_api_key)])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    project = Project(
        title=payload.title,
        status="draft",
        source_type=payload.source_type,
        source_url=payload.source_url,
        source_text=payload.source_text,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)) -> list[Project]:
    # Most-recently-created first — apps/web's Projects page uses this
    # to show "what have I already started" (a real gap found live: the
    # page only had a New Project form, no way back to an existing one).
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())))


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


@router.get("/{project_id}/approvals", response_model=list[ApprovalOut])
def get_project_approvals(project_id: str, db: Session = Depends(get_db)) -> list:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return list_approvals_for_project(db, project_id)


@router.get("/{project_id}/storyboard", response_model=StoryboardOut)
def get_project_storyboard(project_id: str, db: Session = Depends(get_db)):
    # Phase 3.8: the real Storyboard view needs to survive a page
    # reload — ProjectRunOut.storyboard_scenes only lives as long as a
    # POST .../run response does. See
    # app.services.storyboard.get_latest_storyboard_for_project's
    # docstring for how "latest" is resolved.
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    storyboard = get_latest_storyboard_for_project(db, project_id)
    if storyboard is None:
        raise HTTPException(status_code=404, detail="no storyboard yet for this project")
    return storyboard


@router.post("/{project_id}/run", response_model=ProjectRunOut)
def run_project_route(project_id: str, db: Session = Depends(get_db)) -> dict:
    # See app.services.orchestrator's module docstring: this runs the
    # full studio graph synchronously, inside this request — a
    # deliberate v0 shortcut, not the eventual services/orchestrator-
    # worker. Requires real ANTHROPIC_API_KEY/VOYAGE_API_KEY in the
    # environment to produce real output; without them every real Agent
    # call fails cleanly (status="failed", not a crash) and this
    # endpoint still returns 200 with an empty script.
    try:
        return run_project(db, project_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=404, detail="project not found")
