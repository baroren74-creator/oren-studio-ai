"""Persistence for the style profile — docs/database.md's `style_profile`
table, Phase 3.1's "manual one-time questionnaire" (tone, length,
favorite openers/closers). The Script Agent (Phase 3.2-3.4) reads the
current (highest-version) row to write in Oren's voice.

Versioned rather than updated in place: a new questionnaire pass (or an
edit to the answers) creates a new row with `version = previous + 1`,
so `Script Agent` runs from before a style change keep their original
`style_profile_id` (docs/database.md's `scripts.style_profile_id`)
meaningfully pointing at what was actually used at the time, not a
silently-mutated row.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import StyleProfile


def create_style_profile(
    db: Session,
    *,
    tone_notes: str | None = None,
    opening_patterns: list[str] | None = None,
    closing_patterns: list[str] | None = None,
    avg_length_seconds: float | None = None,
    vocabulary_notes: dict | None = None,
) -> StyleProfile:
    """Create a new style_profile row at the next version number."""
    current_max = db.scalar(select(func.max(StyleProfile.version)))
    next_version = (current_max or 0) + 1

    profile = StyleProfile(
        version=next_version,
        tone_notes=tone_notes,
        opening_patterns=opening_patterns or [],
        closing_patterns=closing_patterns or [],
        avg_length_seconds=avg_length_seconds,
        vocabulary_notes=vocabulary_notes,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def get_current_style_profile(db: Session) -> StyleProfile | None:
    """The highest-version row, or None if the questionnaire has never
    been run — callers (e.g. Script Agent) must handle that case rather
    than assume a style profile always exists."""
    return db.scalar(select(StyleProfile).order_by(StyleProfile.version.desc()).limit(1))
