"""SQLAlchemy models — see docs/database.md.

Phase 1 scope (docs/roadmap.md 1.8) was exactly: projects, sources,
agent_runs, agent_events, approvals. `research_notes` was added in Phase
2.3 alongside the real Research Agent (agents/research_agent/agent.py),
`style_profile` in Phase 3.1 alongside the style questionnaire, `scripts`
in Phase 3.2-3.4 alongside the real Script Agent, `prompt_library` in
Phase 3.5 alongside its CRUD UI, `storyboards` in Phase 3.7 alongside the
Storyboard module (workflows/storyboard.py) — each the first table added
incrementally as the feature that needs it landed, per the Phase 1 note
below. The rest of docs/database.md's schema (ideas, assets, videos,
publications, memory_entries, favorite_tools, brand_assets) is still
added incrementally in later phases as those features are built — not
all at once here.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="draft")
    # draft|researching|scripting|producing|review|published|archived
    source_type: Mapped[str | None] = mapped_column(String)
    # github|youtube|reel|post|tweet|website|idea
    source_url: Mapped[str | None] = mapped_column(String)
    # Phase 3.9: only meaningful when source_type is reel|post|tweet — the
    # caption/transcript pasted in manually, since there's no reliable,
    # ToS-clean automated fetch for those source types (see
    # agents/research_agent/agent.py's module docstring). Not in
    # docs/database.md's original minimal `projects` listing — added here
    # the same "this file may add bookkeeping/feature columns beyond the
    # doc's schema sketch" way apps/api/app/models.py's Storyboard.created_at
    # already does.
    source_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    sources: Mapped[list["Source"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    approvals: Mapped[list["Approval"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    research_notes: Mapped[list["ResearchNote"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    scripts: Mapped[list["Script"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    type: Mapped[str | None] = mapped_column(String)  # repo|video|article|post
    raw_url: Mapped[str | None] = mapped_column(String)
    fetched_content: Mapped[dict | None] = mapped_column(JSON)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped["Project"] = relationship(back_populates="sources")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    agent_name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="running")  # running|success|failed|needs_approval
    input: Mapped[dict | None] = mapped_column(JSON)
    output: Mapped[dict | None] = mapped_column(JSON)
    cost_usd: Mapped[float | None] = mapped_column(Numeric)
    tokens_used: Mapped[int | None] = mapped_column()
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped["Project"] = relationship(back_populates="agent_runs")
    events: Mapped[list["AgentEvent"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"))
    event_type: Mapped[str] = mapped_column(String)  # see docs/api.md Event types / core.events.EventType
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    run: Mapped["AgentRun"] = relationship(back_populates="events")


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    stage: Mapped[str] = mapped_column(String)  # script|storyboard|final_video|publish
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|approved|rejected|edited
    notes: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project: Mapped["Project"] = relationship(back_populates="approvals")


class ResearchNote(Base):
    """Persisted output of a Research Agent run (docs/database.md) — one
    row per successful `status="success"` AgentOutput from
    agents/research_agent/agent.py. `interest_score`/`scored_by` are
    nullable because Phase 2.3's Research Agent doesn't score ideas
    itself; Phase 2.6's idea-scoring rubric (docs/agents.md) fills those
    in on a later pass over this same row, not a new one."""

    __tablename__ = "research_notes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    summary: Mapped[str | None] = mapped_column(Text)
    key_points: Mapped[list | None] = mapped_column(JSON)
    interest_score: Mapped[float | None] = mapped_column(Numeric)  # ADR-003 gate, filled in by Phase 2.6
    scored_by: Mapped[str | None] = mapped_column(String)  # agent version, e.g. "research_agent@0.2.0"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped["Project"] = relationship(back_populates="research_notes")


class StyleProfile(Base):
    """Oren's writing-voice profile (docs/database.md) — Phase 3.1's
    "manual one-time questionnaire" (tone, length, favorite openers/
    closers), which the Script Agent (Phase 3.2-3.4) reads to write in
    his style rather than a generic one. Versioned, not updated in place
    — a new questionnaire pass creates a new row (higher `version`); the
    Script Agent always reads the highest version
    (`GET /api/style-profile/current`).

    `opening_patterns`/`closing_patterns` are `TEXT[]` in docs/database.md
    but stored here as JSON lists — same engine-agnostic simplification
    ResearchNote.key_points already uses (JSON works identically on
    SQLite in tests and Postgres in production; native Postgres ARRAY
    doesn't exist on SQLite)."""

    __tablename__ = "style_profile"  # matches docs/database.md's exact (singular) table name

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    version: Mapped[int] = mapped_column()
    tone_notes: Mapped[str | None] = mapped_column(Text)
    opening_patterns: Mapped[list | None] = mapped_column(JSON)
    closing_patterns: Mapped[list | None] = mapped_column(JSON)
    avg_length_seconds: Mapped[float | None] = mapped_column(Numeric)
    vocabulary_notes: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Script(Base):
    """Persisted output of a Script Agent run (docs/database.md) — one
    row per successful `status="success"` AgentOutput from
    agents/script_agent/agent.py. `style_profile_id` is nullable: the
    Script Agent works even with no style_profile yet (see that Agent's
    module docstring), so a script written before the questionnaire was
    ever run has nothing to point at."""

    __tablename__ = "scripts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"))
    hook: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str | None] = mapped_column(Text)
    cta: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    hashtags: Mapped[list | None] = mapped_column(JSON)  # TEXT[] in docs/database.md — same JSON simplification
    style_profile_id: Mapped[str | None] = mapped_column(ForeignKey("style_profile.id"))
    version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped["Project"] = relationship(back_populates="scripts")
    storyboards: Mapped[list["Storyboard"]] = relationship(back_populates="script", cascade="all, delete-orphan")


class Storyboard(Base):
    """Persisted output of the Storyboard module (docs/database.md) — one
    row per successful `workflows/storyboard.py.generate_storyboard()`
    call for a given Script. `scenes` stores the module's ordered list of
    `{order, description, duration, caption_cue, visual_ref}` dicts
    verbatim as JSON — `JSONB` in docs/database.md, same engine-agnostic
    `JSON` simplification `ResearchNote.key_points`/`Script.hashtags`
    already use (works identically on SQLite in tests and Postgres in
    production).

    One script can in principle get more than one storyboard (e.g. a
    re-run after editing the script) — no uniqueness constraint on
    `script_id`, same "re-running is the recovery path, not editing a
    row in place" reasoning as Script/ResearchNote.

    `created_at` isn't in docs/database.md's minimal `storyboards`
    listing but is added here for the same reason every other table in
    this file has one (ordering "which storyboard is latest" without a
    separate `version` column, matching Script/ResearchNote's own
    columns) — the doc lists the columns that matter for the schema
    design; this file is allowed to add bookkeeping columns like this
    one."""

    __tablename__ = "storyboards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    script_id: Mapped[str] = mapped_column(ForeignKey("scripts.id"))
    scenes: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    script: Mapped["Script"] = relationship(back_populates="storyboards")


class PromptLibraryEntry(Base):
    """One version of one prompt (docs/database.md's `prompt_library`) —
    Phase 3.5. Versioned via a `parent_id` chain, not an in-place update
    (docs/architecture.md section 9.5: "Versioning for the Style Guide
    and Prompt Library is already in the schema (version, parent_id) —
    make sure the UI shows a Diff between versions, not just an
    'update'"). Editing a prompt inserts a new row with `parent_id`
    pointing at the row being edited and `version = parent.version + 1`;
    the old row is never mutated or deleted, so the full history is
    always reconstructible by following `parent_id` back to a row with
    `parent_id IS NULL` (`version == 1`).

    `name` identifies a prompt "family" across versions (every row in
    one version chain shares the same `name`) — this is an
    application-level convention enforced in
    `app/services/prompt_library.py`, not a DB constraint, matching how
    `style_profile` also enforces its versioning invariants in the
    service layer rather than in SQL."""

    __tablename__ = "prompt_library"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String)
    prompt_text: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(default=1)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("prompt_library.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
