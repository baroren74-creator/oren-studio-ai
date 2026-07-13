"""Pydantic request/response models for the REST API — see docs/api.md.

Kept separate from app.models (SQLAlchemy ORM) on purpose: the API
contract and the storage schema are allowed to diverge, and conflating
them makes both harder to change independently.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str | None = None
    source_type: str
    source_url: str


class ProjectOut(BaseModel):
    id: str
    title: str | None
    status: str
    source_type: str | None
    source_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentEventOut(BaseModel):
    id: str
    run_id: str
    event_type: str
    payload: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentRunOut(BaseModel):
    id: str
    project_id: str
    agent_name: str
    status: str
    cost_usd: float | None
    tokens_used: int | None
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class KnowledgeSearchResultOut(BaseModel):
    """One semantic-search hit — see app.services.knowledge's module
    docstring for why this is Qdrant's own payload rather than a
    Postgres-hydrated row (Source persistence isn't wired up yet)."""

    text: str
    score: float
    payload: dict


class StyleProfileCreate(BaseModel):
    """Phase 3.1's manual one-time questionnaire, submitted as one
    request — see docs/agents.md's Script Agent section / scripts/
    seed_style_profile.py for Oren's actual v0 answers."""

    tone_notes: str | None = None
    opening_patterns: list[str] = []
    closing_patterns: list[str] = []
    avg_length_seconds: float | None = None
    vocabulary_notes: dict | None = None


class StyleProfileOut(BaseModel):
    id: str
    version: int
    tone_notes: str | None
    opening_patterns: list[str] | None
    closing_patterns: list[str] | None
    avg_length_seconds: float | None
    vocabulary_notes: dict | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class ScriptResultOut(BaseModel):
    hook: str | None
    body: str | None
    cta: str | None
    caption: str | None
    title: str | None
    hashtags: list[str] | None


class StoryboardSceneOut(BaseModel):
    """One scene from workflows/storyboard.py's generate_storyboard() —
    see that module's docstring for why `visual_ref` is always null for
    now (no asset library/B-roll search wired up yet)."""

    order: int
    description: str
    duration: float
    caption_cue: str | None
    visual_ref: str | None


class ProjectRunOut(BaseModel):
    """Response for `POST /api/projects/{id}/run` — see
    app.services.orchestrator's module docstring for what this endpoint
    actually does (a synchronous, single-process, v0 graph run, not the
    eventual services/orchestrator-worker)."""

    run_id: str
    events: list[str]
    rejected: bool
    interrupted: bool
    idea_score: float | None
    research_note_id: str | None
    script_id: str | None
    script: ScriptResultOut | None
    approval_id: str | None = None
    total_cost_usd: float = 0.0
    storyboard_id: str | None = None
    storyboard_scenes: list[StoryboardSceneOut] | None = None


class PromptCreate(BaseModel):
    """POST /api/prompt-library — starts a new prompt at version 1."""

    name: str
    category: str | None = None
    prompt_text: str | None = None


class PromptVersionCreate(BaseModel):
    """POST /api/prompt-library/{id}/versions — edits a prompt by
    creating the next version in its chain. `name` isn't accepted here:
    a version can't switch families, see app.services.prompt_library."""

    prompt_text: str | None = None
    category: str | None = None


class PromptOut(BaseModel):
    id: str
    name: str
    category: str | None
    prompt_text: str | None
    version: int
    parent_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApprovalDecision(BaseModel):
    """Body for request-edit (approve/reject take no body — see
    app.routers.approvals)."""

    notes: str | None = None


class ApprovalOut(BaseModel):
    id: str
    project_id: str
    stage: str
    status: str
    notes: str | None
    decided_at: datetime | None

    model_config = {"from_attributes": True}
