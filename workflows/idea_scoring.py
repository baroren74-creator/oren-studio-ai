"""Idea Scoring rubric — docs/agents.md 'Idea scoring rubric', ADR-003.

Not a registered Agent (docs/agents.md's Agent Registry / packages/core's
Agent protocol) — like the future Storyboard step (Phase 3.7), this is a
custom LLM-prompting module wired directly into workflows/graph.py's
idea_scoring_node, not a swappable provider behind the registry.

ADR-003 is explicit that `interest_score` must come from a *written*
rubric, not a bare "rate this idea 1-100" prompt. This module enforces
that in two ways: the four criteria below are named and weighted in code
(not left to the LLM to invent), and the final score is *summed by this
module*, not asked of the LLM directly — the LLM's job is only to judge
each named criterion independently and explain why.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# providers/llm is a sibling package, not installed via the (not-yet-set-up)
# workspace package manager — same sys.path shim as agents/research_agent/
# agent.py, see that file's comment for when this goes away.
_PROVIDERS_LLM = Path(__file__).resolve().parents[1] / "providers" / "llm"
if str(_PROVIDERS_LLM) not in sys.path:
    sys.path.insert(0, str(_PROVIDERS_LLM))

from llm_provider import LLMError, LLMMessage, complete

# Each criterion is scored 0-25 by the LLM; the four sum to a 0-100
# `interest_score`, matching workflows/graph.py's IDEA_SCORE_THRESHOLD
# (50.0 — i.e. an idea needs to look at least "half good" to proceed).
MAX_PER_CRITERION = 25
CRITERIA: tuple[str, ...] = (
    "novelty",  # Is this fresh, or already covered to death?
    "audience_relevance",  # Fits Oren's tech-content channel and likely audience.
    "source_reliability",  # Does the source look mature/credible (docs, real usage), not a toy/abandoned repo?
    "visual_potential",  # Does it lend itself to a short, visual, demo-able video?
)

SYSTEM_PROMPT = (
    "You are the Idea Scoring rubric inside Oren Studio AI, a personal "
    "Hebrew tech-content studio. Score the given research summary against "
    "exactly these four criteria, 0-25 points each:\n"
    "- novelty: is this fresh/uncommon, or something already covered "
    "extensively elsewhere?\n"
    "- audience_relevance: does this fit a tech-focused short-video "
    "channel (developer tools, AI, open source, practical demos)?\n"
    "- source_reliability: does the source look mature and credible "
    "(real documentation, apparent real-world usage), not a toy, "
    "abandoned, or low-effort project?\n"
    "- visual_potential: does this lend itself to a short, visual, "
    "demo-able video (something to show on screen), rather than being "
    "purely abstract/textual?\n\n"
    "Respond with ONLY a JSON object, no other text, in exactly this "
    'shape: {"novelty": <0-25 int>, "audience_relevance": <0-25 int>, '
    '"source_reliability": <0-25 int>, "visual_potential": <0-25 int>, '
    '"rationale": {"novelty": "<one sentence>", "audience_relevance": '
    '"<one sentence>", "source_reliability": "<one sentence>", '
    '"visual_potential": "<one sentence>"}}. '
    "Do not include a total — it is computed separately."
)


@dataclass
class IdeaScore:
    total: float
    breakdown: dict[str, int] = field(default_factory=dict)
    rationale: dict[str, str] = field(default_factory=dict)
    scored_by: str = "idea_scoring@0.1.0"


class IdeaScoringError(RuntimeError):
    """Raised on LLM failure or an unparseable rubric response — callers
    (workflows/graph.py's idea_scoring_node) catch this specifically,
    same pattern as GitHubSourceError/LLMError elsewhere (docs/
    standards.md section 8)."""


def _extract_json(text: str) -> dict:
    """LLMs occasionally wrap JSON in a markdown code fence despite being
    told not to — strip that defensively rather than failing scoring shut
    on a cosmetic formatting slip. Not lenient about anything else: a
    genuinely malformed response still raises IdeaScoringError."""
    stripped = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise IdeaScoringError(f"rubric response was not valid JSON: {exc}") from exc


def score_idea(*, summary: str, key_points: list[str] | None = None, model: str | None = None) -> IdeaScore:
    """Score a Research Agent summary against the written rubric above.

    Raises IdeaScoringError (never a bare Exception) on LLM failure or a
    malformed response — callers should treat that the same way a
    "failed" AgentOutput is treated: don't guess a score, don't proceed
    into expensive stages (ADR-003's whole point)."""
    if not summary or not summary.strip():
        raise IdeaScoringError("cannot score an idea with an empty research summary")

    user_content = summary.strip()
    if key_points:
        user_content += "\n\nKey points:\n" + "\n".join(f"- {p}" for p in key_points)

    try:
        response = complete(
            [
                LLMMessage(role="system", content=SYSTEM_PROMPT),
                LLMMessage(role="user", content=user_content),
            ],
            model=model,
            max_tokens=500,
            temperature=0.2,  # low — this is a rubric judgment, not creative writing
        )
    except LLMError as exc:
        raise IdeaScoringError(f"idea scoring LLM call failed: {exc}") from exc

    parsed = _extract_json(response.text)

    breakdown: dict[str, int] = {}
    for criterion in CRITERIA:
        if criterion not in parsed:
            raise IdeaScoringError(f"rubric response missing required criterion '{criterion}'")
        try:
            value = int(parsed[criterion])
        except (TypeError, ValueError) as exc:
            raise IdeaScoringError(f"criterion '{criterion}' was not an integer: {parsed[criterion]!r}") from exc
        # Clamp rather than reject on a slightly-out-of-range score — the
        # rubric bounds are a scoring convention, not worth failing an
        # otherwise-usable judgment over an LLM writing 26 instead of 25.
        breakdown[criterion] = max(0, min(MAX_PER_CRITERION, value))

    rationale = {c: str(parsed.get("rationale", {}).get(c, "")) for c in CRITERIA}
    total = float(sum(breakdown.values()))

    return IdeaScore(
        total=total,
        breakdown=breakdown,
        rationale=rationale,
        scored_by=f"idea_scoring@0.1.0:{response.model}",
    )


__all__ = ["IdeaScore", "IdeaScoringError", "score_idea", "CRITERIA", "MAX_PER_CRITERION", "SYSTEM_PROMPT"]
