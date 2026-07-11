"""Canonical event types — see docs/api.md 'Event types'.

This is the single source of truth for event names. Every Agent's
`AgentOutput.next_event` and every entry written to `agent_events` must
use one of these values — do not invent a new event string inline
anywhere else in the codebase; add it here first (see CONTRIBUTING.md).
"""

from __future__ import annotations

from enum import Enum


class EventType(str, Enum):
    SOURCE_INGESTED = "source.ingested"
    RESEARCH_COMPLETED = "research.completed"
    IDEA_SCORED = "idea.scored"
    IDEA_REJECTED = "idea.rejected"  # ADR-003: cost gate, stops the pipeline
    SCRIPT_DRAFTED = "script.drafted"
    SCRIPT_APPROVED = "script.approved"  # Approval Gate #1 (optional)
    STORYBOARD_READY = "storyboard.ready"
    ASSETS_READY = "assets.ready"
    RECORDING_REQUESTED = "recording.requested"
    RECORDING_COMPLETED = "recording.completed"
    AVATAR_REQUESTED = "avatar.requested"
    AVATAR_COMPLETED = "avatar.completed"
    VOICE_COMPLETED = "voice.completed"
    VIDEO_RENDERED = "video.rendered"
    CAPTIONS_GENERATED = "captions.generated"
    THUMBNAIL_GENERATED = "thumbnail.generated"
    CAPTION_TEXT_READY = "caption.text.ready"
    FINAL_REVIEW_REQUESTED = "final_review.requested"  # Approval Gate #2 (mandatory)
    PUBLISH_APPROVED = "publish.approved"  # export folder + preview ready, ADR-011
    PUBLISH_COMPLETED = "publish.completed"  # Oren confirms manual upload, ADR-011
    PUBLISH_FAILED = "publish.failed"

    # Generic per-agent failure suffix pattern: "<domain>.failed" — agents
    # emit these dynamically (f"{stage}.failed"); retry policy in the
    # Orchestrator (docs/standards.md section 8) reacts to the suffix,
    # not to a fixed enum member, since the failing stage varies.
