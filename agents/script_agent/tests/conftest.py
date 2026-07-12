"""Path setup mirroring agents/research_agent/tests/conftest.py."""

from __future__ import annotations

import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = TESTS_ROOT.parents[2]

for p in (REPO_ROOT, REPO_ROOT / "packages" / "core", REPO_ROOT / "providers" / "llm"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
