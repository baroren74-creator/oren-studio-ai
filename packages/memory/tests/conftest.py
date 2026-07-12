"""Path setup mirroring agents/research_agent/tests/conftest.py — this
package lives outside providers/llm, which memory.store needs (both
directly and via its own internal sys.path shim)."""

from __future__ import annotations

import sys
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = TESTS_ROOT.parent
REPO_ROOT = PACKAGE_ROOT.parents[1]

for p in (PACKAGE_ROOT, REPO_ROOT / "providers" / "llm"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
