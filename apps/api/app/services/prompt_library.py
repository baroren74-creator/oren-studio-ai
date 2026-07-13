"""Persistence for the Prompt Library — docs/database.md's
`prompt_library` table, Phase 3.5. CRUD with versioning: editing a
prompt never mutates its row in place, it inserts a new row with
`parent_id` pointing at the row being edited (docs/architecture.md
section 9.5 — the UI must show a Diff between versions, not silently
overwrite, which is only possible if old versions stay intact).

`name` identifies a version "family": every row sharing a `name` is one
version chain, walkable from any row back to the one with
`parent_id IS None` (`version == 1`). This is an application-level
convention enforced here, not a DB constraint — same choice
`style_profile`'s versioning already made (see that service module).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PromptLibraryEntry


class PromptNotFoundError(Exception):
    """Raised when a prompt_library id doesn't exist — the route layer
    turns this into a 404."""


def create_prompt(
    db: Session,
    *,
    name: str,
    category: str | None = None,
    prompt_text: str | None = None,
) -> PromptLibraryEntry:
    """Start a new version chain: version 1, no parent."""
    entry = PromptLibraryEntry(name=name, category=category, prompt_text=prompt_text, version=1, parent_id=None)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def create_new_version(
    db: Session,
    *,
    parent_id: str,
    prompt_text: str | None = None,
    category: str | None = None,
) -> PromptLibraryEntry:
    """Edit a prompt by inserting the next version in its chain.
    `name` is always inherited from the parent (a version can't switch
    families); `category` may be overridden, and defaults to the
    parent's if not given. Raises `PromptNotFoundError` if `parent_id`
    doesn't exist."""
    parent = db.get(PromptLibraryEntry, parent_id)
    if parent is None:
        raise PromptNotFoundError(parent_id)

    entry = PromptLibraryEntry(
        name=parent.name,
        category=category if category is not None else parent.category,
        prompt_text=prompt_text,
        version=parent.version + 1,
        parent_id=parent.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def get_prompt(db: Session, prompt_id: str) -> PromptLibraryEntry | None:
    return db.get(PromptLibraryEntry, prompt_id)


def list_current_prompts(db: Session) -> list[PromptLibraryEntry]:
    """One row per family — the highest-version row for each distinct
    `name`. Small, single-user dataset (ADR: this whole system is built
    for one person), so this reduces in Python rather than reaching for
    a window-function query that would need to special-case SQLite vs
    Postgres — same "keep it simple for one user" reasoning used
    throughout this codebase."""
    rows = db.scalars(select(PromptLibraryEntry).order_by(PromptLibraryEntry.name, PromptLibraryEntry.version)).all()
    latest_by_name: dict[str, PromptLibraryEntry] = {}
    for row in rows:
        latest_by_name[row.name] = row  # rows are version-ordered, so the last write per name wins
    return sorted(latest_by_name.values(), key=lambda r: r.name)


def get_prompt_history(db: Session, prompt_id: str) -> list[PromptLibraryEntry]:
    """Full version chain for the family `prompt_id` belongs to, oldest
    first — so the UI can diff each version against the one before it.
    Raises `PromptNotFoundError` if `prompt_id` doesn't exist."""
    anchor = db.get(PromptLibraryEntry, prompt_id)
    if anchor is None:
        raise PromptNotFoundError(prompt_id)
    rows = db.scalars(
        select(PromptLibraryEntry)
        .where(PromptLibraryEntry.name == anchor.name)
        .order_by(PromptLibraryEntry.version)
    ).all()
    return list(rows)


def delete_prompt_family(db: Session, prompt_id: str) -> None:
    """Deletes every version sharing this prompt's `name` — "delete this
    prompt" removes its whole history, not just one version, matching
    the CRUD UI's mental model (there's one prompt, edited over time),
    not a version-by-version deletion tool. Raises `PromptNotFoundError`
    if `prompt_id` doesn't exist."""
    anchor = db.get(PromptLibraryEntry, prompt_id)
    if anchor is None:
        raise PromptNotFoundError(prompt_id)
    # Newest-first: each row's parent_id FK must not be deleted while
    # something still references it, so children go before parents.
    rows = db.scalars(
        select(PromptLibraryEntry)
        .where(PromptLibraryEntry.name == anchor.name)
        .order_by(PromptLibraryEntry.version.desc())
    ).all()
    for row in rows:
        db.delete(row)
    db.commit()
