"""Script Agent test suite — docs/roadmap.md Phase 3.2-3.4.

complete() (providers/llm -> LiteLLM -> Anthropic) is mocked, same
reasoning as agents/research_agent/tests/test_agent.py's module
docstring: no real API key exists in this sandbox.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import patch

import pytest

import agents.script_agent.agent as sa_module
from core.schemas.agent import AgentInput
from llm_provider import LLMError, LLMResponse

AGENT = sa_module.agent

FAKE_SCRIPT_JSON = json.dumps(
    {
        "hook": "ידעתם שאפשר לתרגם קוד לוידאו תוך שנייה?",
        "body": "הכלי הזה לוקח repo של GitHub ובונה ממנו וידאו קצר אוטומטית.",
        "cta": "אהבתם, רוצים עוד? תעקבו",
        "caption": "כלי מטורף שממיר GitHub repo לוידאו",
        "title": "מ-GitHub לוידאו תוך שניות",
        "hashtags": ["#opensource", "#devtools", "#ai"],
    },
    ensure_ascii=False,
)


def _input(payload: dict) -> AgentInput:
    return AgentInput(run_id=uuid.uuid4(), project_id=uuid.uuid4(), payload=payload)


def _fake_response(text: str = FAKE_SCRIPT_JSON) -> LLMResponse:
    return LLMResponse(
        text=text,
        model="anthropic/claude-3-5-sonnet-20241022",
        input_tokens=200,
        output_tokens=150,
        cost_usd=0.004,
    )


@pytest.mark.asyncio
async def test_skips_when_no_research_summary():
    out = await AGENT.run(_input({}))
    assert out.status == "skipped"
    assert out.next_event is None
    assert "no research_summary" in out.result["reason"]


@pytest.mark.asyncio
async def test_skips_when_research_summary_is_blank():
    out = await AGENT.run(_input({"research_summary": "   "}))
    assert out.status == "skipped"


@pytest.mark.asyncio
async def test_happy_path_returns_all_six_fields():
    with patch.object(sa_module, "complete", return_value=_fake_response()) as mock_complete:
        out = await AGENT.run(
            _input(
                {
                    "research_summary": "A tool that converts GitHub repos into short videos.",
                    "research_key_points": ["Uses gitingest", "Outputs mp4"],
                }
            )
        )

    mock_complete.assert_called_once()
    assert out.status == "success"
    assert out.next_event == "script.drafted"
    assert out.result["hook"].startswith("ידעתם")
    assert out.result["cta"] == "אהבתם, רוצים עוד? תעקבו"
    assert out.result["hashtags"] == ["#opensource", "#devtools", "#ai"]

    assert out.cost.tokens_used == 350
    assert out.cost.cost_usd == pytest.approx(0.004)
    assert out.cost.provider == "anthropic/claude-3-5-sonnet-20241022"


@pytest.mark.asyncio
async def test_style_profile_fields_are_folded_into_the_system_prompt():
    captured_messages = []

    def _capture(messages, **kwargs):
        captured_messages.extend(messages)
        return _fake_response()

    with patch.object(sa_module, "complete", side_effect=_capture):
        await AGENT.run(
            _input(
                {
                    "research_summary": "A demo tool.",
                    "style_tone_notes": "energetic and fast",
                    "style_opening_patterns": ["הי חברים תראו מה מצאתי"],
                    "style_closing_patterns": ["אהבתם, רוצים עוד? תעקבו"],
                    "style_avg_length_seconds": 37.5,
                }
            )
        )

    system_message = captured_messages[0]
    assert system_message.role == "system"
    assert "energetic and fast" in system_message.content
    assert "הי חברים תראו מה מצאתי" in system_message.content
    assert "38 seconds" in system_message.content or "37 seconds" in system_message.content


@pytest.mark.asyncio
async def test_works_without_any_style_profile_fields():
    """Phase 3.1's questionnaire is one-time but not mandatory-before-
    first-use — the Agent must still produce a reasonable prompt using
    only the PRD-level style guide."""
    with patch.object(sa_module, "complete", return_value=_fake_response()) as mock_complete:
        out = await AGENT.run(_input({"research_summary": "A demo tool."}))

    system_message = mock_complete.call_args.args[0][0]
    assert "short, fast, clear, technical" in system_message.content
    assert out.status == "success"


@pytest.mark.asyncio
async def test_llm_failure_is_caught_cleanly():
    with patch.object(sa_module, "complete", side_effect=LLMError("provider down")):
        out = await AGENT.run(_input({"research_summary": "A demo tool."}))

    assert out.status == "failed"
    assert "provider down" in out.result["reason"]
    assert out.next_event is None


@pytest.mark.asyncio
async def test_non_json_response_fails_cleanly():
    with patch.object(sa_module, "complete", return_value=_fake_response("not json at all")):
        out = await AGENT.run(_input({"research_summary": "A demo tool."}))

    assert out.status == "failed"
    assert "not valid JSON" in out.result["reason"]


@pytest.mark.asyncio
async def test_missing_required_field_fails_cleanly():
    incomplete = json.dumps({"hook": "h", "body": "b", "cta": "c", "caption": "cap", "title": "t"})
    with patch.object(sa_module, "complete", return_value=_fake_response(incomplete)):
        out = await AGENT.run(_input({"research_summary": "A demo tool."}))

    assert out.status == "failed"
    assert "hashtags" in out.result["reason"]


@pytest.mark.asyncio
async def test_markdown_fence_is_stripped():
    fenced = f"```json\n{FAKE_SCRIPT_JSON}\n```"
    with patch.object(sa_module, "complete", return_value=_fake_response(fenced)):
        out = await AGENT.run(_input({"research_summary": "A demo tool."}))

    assert out.status == "success"


@pytest.mark.asyncio
async def test_hashtags_not_a_list_fails_cleanly():
    bad = json.dumps(
        {
            "hook": "h",
            "body": "b",
            "cta": "c",
            "caption": "cap",
            "title": "t",
            "hashtags": "#not-a-list",
        }
    )
    with patch.object(sa_module, "complete", return_value=_fake_response(bad)):
        out = await AGENT.run(_input({"research_summary": "A demo tool."}))

    assert out.status == "failed"
    assert "hashtags was not a list" in out.result["reason"]
