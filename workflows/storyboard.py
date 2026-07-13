"""Storyboard generation — docs/roadmap.md Phase 3.7.

Not a registered Agent (docs/agents.md's Agent Registry / packages/core's
Agent protocol) — like workflows/idea_scoring.py, this is a custom
LLM-prompting module wired directly into workflows/graph.py's
storyboard_node, not a swappable provider behind the registry.
docs/open-source-landscape.md section 4 found no mature OSS library that
turns a written script into a shot-by-shot scene breakdown, so this is a
real implementation, not a wrapper.

Input is the Script Agent's output (hook/body/cta — see
agents/script_agent/agent.py); output is a structured, ordered list of
scenes, each a JSON-serializable dict matching docs/database.md's
`storyboards.scenes` shape ([{order, description, visual_ref, duration}])
plus a `caption_cue` field docs/roadmap.md 3.7 explicitly calls for
("structured JSON: scene, duration, visual instruction, caption cue").
`visual_ref` is always None here — there is no asset library or B-roll
search wired up yet (that's Recording/Video Agent territory, still Stub
Agents); a human (Oren) or a later phase fills that in.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# providers/llm is a sibling package, not installed via the (not-yet-set-up)
# workspace package manager — same sys.path shim as workflows/idea_scoring.py
# and agents/research_agent/agent.py, see those files' comments for when
# this goes away.
_PROVIDERS_LLM = Path(__file__).resolve().parents[1] / "providers" / "llm"
if str(_PROVIDERS_LLM) not in sys.path:
    sys.path.insert(0, str(_PROVIDERS_LLM))

from llm_provider import LLMError, LLMMessage, complete

# Soft cap, not enforced by the LLM call itself — a short-video script
# (Phase 3.1's style_avg_length_seconds default is well under 2 minutes)
# has no business needing more than this many distinct scenes. Guards
# against a malformed/runaway response silently producing a 200-scene
# storyboard nobody asked for; see _parse_scenes.
MAX_SCENES = 20

SYSTEM_PROMPT = (
    "You are the Storyboard module inside Oren Studio AI, a personal "
    "Hebrew tech-content studio that turns a short video script into a "
    "shot-by-shot scene breakdown. You will be given a script (hook, "
    "body, call-to-action). Break it into a small, ordered sequence of "
    "scenes that together cover the whole script — typically 3 to 8 "
    "scenes for a short-form video.\n\n"
    "Respond with ONLY a JSON object, no other text, in exactly this "
    'shape: {"scenes": [{"order": <int, starting at 1>, '
    '"description": "<one or two sentences: what should be shown on '
    'screen — the visual instruction, e.g. \\"screen recording of the '
    'terminal running the install command\\">", '
    '"duration": <estimated seconds this scene takes, a positive '
    'number>, "caption_cue": "<short on-screen text/caption for this '
    'scene, or null if none>"}, ...]}. '
    "Scenes must be ordered starting at 1 with no gaps, and their "
    "durations should roughly sum to a short-form video's length."
)


@dataclass
class StoryboardResult:
    scenes: list[dict] = field(default_factory=list)
    generated_by: str = "storyboard@0.1.0"
    # Cost of the one LLM call this function makes — same pattern as
    # workflows/idea_scoring.py's IdeaScore.cost_usd/tokens_used, read
    # back out via llm_provider.complete()'s LLMResponse and surfaced to
    # workflows/graph.py's agent_costs / apps/api's agent_runs table.
    cost_usd: float = 0.0
    tokens_used: int = 0


class StoryboardError(RuntimeError):
    """Raised on LLM failure or an unparseable response — callers
    (workflows/graph.py's storyboard_node) catch this specifically, same
    pattern as IdeaScoringError/LLMError elsewhere (docs/standards.md
    section 8)."""


def _extract_json(text: str) -> dict:
    """Same defensive markdown-fence stripping as
    workflows/idea_scoring.py's _extract_json — LLMs occasionally wrap
    JSON in a code fence despite being told not to."""
    stripped = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise StoryboardError(f"storyboard response was not valid JSON: {exc}") from exc


def _parse_scenes(parsed: dict) -> list[dict]:
    raw_scenes = parsed.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise StoryboardError("storyboard response had no non-empty 'scenes' list")
    if len(raw_scenes) > MAX_SCENES:
        raise StoryboardError(f"storyboard response had {len(raw_scenes)} scenes, over the {MAX_SCENES} cap")

    scenes: list[dict] = []
    for i, raw in enumerate(raw_scenes, start=1):
        if not isinstance(raw, dict):
            raise StoryboardError(f"scene {i} was not a JSON object: {raw!r}")
        description = raw.get("description")
        if not description or not str(description).strip():
            raise StoryboardError(f"scene {i} is missing a non-empty 'description'")
        try:
            duration = float(raw.get("duration"))
        except (TypeError, ValueError) as exc:
            raise StoryboardError(f"scene {i}'s 'duration' was not a number: {raw.get('duration')!r}") from exc
        if duration <= 0:
            raise StoryboardError(f"scene {i}'s 'duration' must be positive, got {duration}")
        # Trust the LLM's stated order for readability but don't depend on
        # it being correct — always renumber sequentially from 1 in the
        # order scenes were returned, same "don't let the model own an
        # invariant we can enforce in code" reasoning as
        # workflows/idea_scoring.py clamping out-of-range scores.
        caption_cue = raw.get("caption_cue")
        scenes.append(
            {
                "order": i,
                "description": str(description).strip(),
                "duration": duration,
                "caption_cue": str(caption_cue).strip() if caption_cue else None,
                "visual_ref": None,
            }
        )
    return scenes


def generate_storyboard(
    *,
    hook: str | None,
    body: str | None,
    cta: str | None = None,
    title: str | None = None,
    model: str | None = None,
) -> StoryboardResult:
    """Turn a drafted script (Script Agent output — hook/body/cta) into a
    structured, ordered scene breakdown.

    Raises StoryboardError (never a bare Exception) on LLM failure or a
    malformed/empty response — callers should treat that the same way a
    "failed" AgentOutput is treated: don't guess a storyboard, don't
    persist a partial one."""
    parts = [p.strip() for p in (hook, body, cta) if p and p.strip()]
    if not parts:
        raise StoryboardError("cannot storyboard a script with no hook, body, or cta")

    user_content = "\n\n".join(parts)
    if title:
        user_content = f"Title: {title.strip()}\n\n{user_content}"

    try:
        response = complete(
            [
                LLMMessage(role="system", content=SYSTEM_PROMPT),
                LLMMessage(role="user", content=user_content),
            ],
            model=model,
            max_tokens=1200,
            temperature=0.4,  # a little creative headroom for shot ideas, still mostly structured
        )
    except LLMError as exc:
        raise StoryboardError(f"storyboard LLM call failed: {exc}") from exc

    parsed = _extract_json(response.text)
    scenes = _parse_scenes(parsed)

    return StoryboardResult(
        scenes=scenes,
        generated_by=f"storyboard@0.1.0:{response.model}",
        cost_usd=response.cost_usd,
        tokens_used=response.input_tokens + response.output_tokens,
    )


__all__ = ["StoryboardResult", "StoryboardError", "generate_storyboard", "MAX_SCENES", "SYSTEM_PROMPT"]
