"""Script Agent — see docs/agents.md.

Phase 3.2-3.4 (docs/roadmap.md): real logic. The roadmap splits this
into three sub-steps (Hook generator / Body+CTA / Caption+Title+Hashtags)
for planning granularity, but they're implemented here as a single
structured LLM call producing all six fields together — same
architectural choice as workflows/idea_scoring.py combining four rubric
criteria into one call rather than four: the fields aren't independent
(a caption references the hook, hashtags follow from the body's topic),
and docs/agents.md's roster already describes this as one Agent's
responsibility, not three. `docs/database.md`'s `scripts` row stores all
six fields together too.

Writes in Hebrew — Research Agent's summary/key_points are deliberately
English (see agents/research_agent/agent.py's system prompts: "Script
Agent handles Hebrew translation later"), and Oren's actual style_profile
opening/closing patterns (Phase 3.1) are Hebrew. Uses `docs/vision.md`'s
style guide (short, fast, clear, technical, not exhausting, hook within
3 seconds) plus whatever style_profile fields the caller passes in;
works with sensible PRD-only defaults if no style_profile exists yet
(the questionnaire is one-time but not mandatory-before-first-use).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# providers/llm is a sibling package, not installed via the (not-yet-set-up)
# workspace package manager — same sys.path shim as agents/research_agent/
# agent.py.
_PROVIDERS_LLM = Path(__file__).resolve().parents[2] / "providers" / "llm"
if str(_PROVIDERS_LLM) not in sys.path:
    sys.path.insert(0, str(_PROVIDERS_LLM))

from core.registry import default_registry
from core.schemas.agent import AgentInput, AgentOutput, CostInfo
from llm_provider import LLMError, LLMMessage, complete

NAME = "script_agent"
VERSION = "0.1.0"

REQUIRED_FIELDS: tuple[str, ...] = ("hook", "body", "cta", "caption", "title", "hashtags")

BASE_STYLE_GUIDE = (
    "Style guide (docs/vision.md): short, fast, clear, technical, not "
    "exhausting. The hook must land within the first 3 seconds — no "
    "slow build-up. Write in Hebrew."
)

SYSTEM_PROMPT_TEMPLATE = (
    "You are the Script Agent inside Oren Studio AI, a personal Hebrew "
    "tech-content studio. Given a research summary about a tool, "
    "project, or technology, write a short-form video script in Oren's "
    "voice.\n\n{style_guide}\n\n"
    "Respond with ONLY a JSON object, no other text, in exactly this "
    'shape: {{"hook": "<opening line, lands in the first 3 seconds>", '
    '"body": "<the main explanation, concrete and specific>", '
    '"cta": "<closing call to action>", '
    '"caption": "<social post caption, can restate the hook/body '
    'briefly>", "title": "<short video title>", '
    '"hashtags": ["<tag1>", "<tag2>", ...]}}. '
    "All six fields are required. hashtags should each include a "
    "leading '#' and be relevant to the specific topic, not generic."
)


class ScriptAgentError(RuntimeError):
    """Raised on LLM failure or an unparseable script response —
    mirrors IdeaScoringError's per-module typed-error convention
    (workflows/idea_scoring.py)."""


def _build_style_guide(payload: dict) -> str:
    """Fold BASE_STYLE_GUIDE together with whatever style_profile fields
    the caller passed in (workflows/graph.py's script_node — see that
    node's comment for where these come from). Every style_profile field
    is optional; a missing one is simply omitted, not treated as an
    error — Phase 3.1's questionnaire being one-time-but-not-mandatory
    means this Agent must still produce something reasonable before it's
    ever been run."""
    lines = [BASE_STYLE_GUIDE]

    tone_notes = payload.get("style_tone_notes")
    if tone_notes:
        lines.append(f"Oren's tone: {tone_notes}")

    opening_patterns = payload.get("style_opening_patterns")
    if opening_patterns:
        examples = " / ".join(f'"{p}"' for p in opening_patterns)
        lines.append(f"Examples of hooks Oren likes (match this energy, don't copy verbatim): {examples}")

    closing_patterns = payload.get("style_closing_patterns")
    if closing_patterns:
        examples = " / ".join(f'"{p}"' for p in closing_patterns)
        lines.append(f"Examples of CTAs Oren likes (match this energy, don't copy verbatim): {examples}")

    avg_length_seconds = payload.get("style_avg_length_seconds")
    if avg_length_seconds:
        lines.append(f"Target video length: about {avg_length_seconds:.0f} seconds — keep the script that tight.")

    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    """Same defensive markdown-fence stripping as
    workflows/idea_scoring.py's _extract_json — not lenient about
    anything else."""
    stripped = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL)
    if fence:
        stripped = fence.group(1)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ScriptAgentError(f"script response was not valid JSON: {exc}") from exc


class ScriptAgent:
    name = NAME
    version = VERSION

    async def run(self, input: AgentInput) -> AgentOutput:
        summary = input.payload.get("research_summary")
        if not summary or not summary.strip():
            return AgentOutput(
                status="skipped",
                result={"reason": "no research_summary to write a script from"},
                next_event=None,
            )

        key_points = input.payload.get("research_key_points") or []
        user_content = summary.strip()
        if key_points:
            user_content += "\n\nKey points:\n" + "\n".join(f"- {p}" for p in key_points)

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(style_guide=_build_style_guide(input.payload))

        try:
            response = complete(
                [
                    LLMMessage(role="system", content=system_prompt),
                    LLMMessage(role="user", content=user_content),
                ],
                max_tokens=900,
                temperature=0.8,  # creative writing, unlike idea_scoring's 0.2 rubric judgment
            )
        except LLMError as exc:
            return AgentOutput(status="failed", result={"reason": f"script LLM call failed: {exc}"})

        try:
            parsed = _extract_json(response.text)
        except ScriptAgentError as exc:
            return AgentOutput(status="failed", result={"reason": str(exc)})

        missing = [f for f in REQUIRED_FIELDS if f not in parsed]
        if missing:
            return AgentOutput(
                status="failed",
                result={"reason": f"script response missing required field(s): {', '.join(missing)}"},
            )

        hashtags = parsed["hashtags"]
        if not isinstance(hashtags, list):
            return AgentOutput(status="failed", result={"reason": f"hashtags was not a list: {hashtags!r}"})

        result = {
            "hook": str(parsed["hook"]),
            "body": str(parsed["body"]),
            "cta": str(parsed["cta"]),
            "caption": str(parsed["caption"]),
            "title": str(parsed["title"]),
            "hashtags": [str(h) for h in hashtags],
        }

        return AgentOutput(
            status="success",
            result=result,
            cost=CostInfo(
                tokens_used=response.input_tokens + response.output_tokens,
                cost_usd=response.cost_usd,
                provider=response.model,
            ),
            next_event="script.drafted",
        )


agent = ScriptAgent()
default_registry.register(NAME, lambda: agent)
