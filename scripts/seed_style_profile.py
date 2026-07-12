#!/usr/bin/env python3
"""Seed the v0 style_profile row from Oren's Phase 3.1 questionnaire
answers (docs/agents.md's Script Agent section, docs/roadmap.md 3.1).

Run once against a live, migrated apps/api database:

    cd apps/api
    python3 -m alembic upgrade head        # make sure style_profile exists
    python3 ../../scripts/seed_style_profile.py

Talks directly to app.services.style_profile / app.db, the same modules
apps/api itself uses — not the HTTP API — so it works whether or not the
server process is currently running. Safe to re-run: create_style_profile
always inserts a new version rather than overwriting, so running this
twice just creates v1 and v2 with identical content (harmless, if
slightly redundant) rather than corrupting anything.
"""

from __future__ import annotations

import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1] / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db import SessionLocal  # noqa: E402
from app.services.style_profile import create_style_profile  # noqa: E402

# Oren's actual answers, collected in chat during Phase 3.1 (2026-07-12).
TONE_NOTES = (
    "Energetic and fast-paced, but also professional and precise, with a "
    "friendly/conversational feel — a mix of all three, not one single "
    "register. Videos are short (30-45 seconds), so tone needs to land "
    "immediately, no slow build-up."
)
OPENING_PATTERNS = [
    "הי חברים תראו מה מצאתי",
    "ידעתם שיש כזה דבר?",
]
CLOSING_PATTERNS = [
    "אהבתם, רוצים עוד? תעקבו",
    "ללינק כתבו לי בתגובות",
]
AVG_LENGTH_SECONDS = 37.5  # midpoint of Oren's stated 30-45s range


def main() -> None:
    db = SessionLocal()
    try:
        profile = create_style_profile(
            db,
            tone_notes=TONE_NOTES,
            opening_patterns=OPENING_PATTERNS,
            closing_patterns=CLOSING_PATTERNS,
            avg_length_seconds=AVG_LENGTH_SECONDS,
        )
        print(f"Created style_profile version {profile.version} (id={profile.id})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
