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
