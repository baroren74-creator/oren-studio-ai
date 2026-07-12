"""workflows/idea_scoring.py — docs/agents.md 'Idea scoring rubric',
docs/roadmap.md Phase 2.6/2.7, ADR-003.

All tests mock the LLM call (workflows.idea_scoring.complete) — no real
network/API key needed, same reasoning as agents/research_agent/tests/
test_agent.py: this suite should run in CI without secrets.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

import workflows.idea_scoring as scoring_module
from llm_provider import LLMError, LLMResponse

VALID_JSON = (
    '{"novelty": 20, "audience_relevance": 22, "source_reliability": 18, '
    '"visual_potential": 15, "rationale": {"novelty": "Fresh angle.", '
    '"audience_relevance": "Fits the channel.", "source_reliability": '
    '"Well documented.", "visual_potential": "Good demo potential."}}'
)


def _fake_response(text: str) -> LLMResponse:
    return LLMResponse(text=text, model="anthropic/claude-3-5-sonnet-20241022", input_tokens=100, output_tokens=50, cost_usd=0.001)


def test_score_idea_sums_criteria_and_returns_breakdown():
    with patch.object(scoring_module, "complete", return_value=_fake_response(VALID_JSON)) as mock_complete:
        score = scoring_module.score_idea(summary="A neat CLI tool for X.", key_points=["fast", "no deps"])

    mock_complete.assert_called_once()
    assert score.total == 20 + 22 + 18 + 15
    assert score.breakdown == {
        "novelty": 20,
        "audience_relevance": 22,
        "source_reliability": 18,
        "visual_potential": 15,
    }
    assert score.rationale["novelty"] == "Fresh angle."
    assert score.scored_by.startswith("idea_scoring@0.1.0:")


def test_score_idea_strips_markdown_code_fence():
    fenced = f"```json\n{VALID_JSON}\n```"
    with patch.object(scoring_module, "complete", return_value=_fake_response(fenced)):
        score = scoring_module.score_idea(summary="A neat CLI tool for X.")

    assert score.total == 75


def test_score_idea_clamps_out_of_range_values():
    text = VALID_JSON.replace('"novelty": 20', '"novelty": 99').replace('"visual_potential": 15', '"visual_potential": -5')
    with patch.object(scoring_module, "complete", return_value=_fake_response(text)):
        score = scoring_module.score_idea(summary="A neat CLI tool for X.")

    assert score.breakdown["novelty"] == 25  # clamped to MAX_PER_CRITERION
    assert score.breakdown["visual_potential"] == 0  # clamped to 0


def test_score_idea_rejects_empty_summary():
    with pytest.raises(scoring_module.IdeaScoringError, match="empty"):
        scoring_module.score_idea(summary="")


def test_score_idea_wraps_llm_error():
    with patch.object(scoring_module, "complete", side_effect=LLMError("boom")):
        with pytest.raises(scoring_module.IdeaScoringError, match="LLM call failed"):
            scoring_module.score_idea(summary="A neat CLI tool for X.")


def test_score_idea_rejects_non_json_response():
    with patch.object(scoring_module, "complete", return_value=_fake_response("not json at all")):
        with pytest.raises(scoring_module.IdeaScoringError, match="not valid JSON"):
            scoring_module.score_idea(summary="A neat CLI tool for X.")


def test_score_idea_rejects_missing_criterion():
    incomplete = '{"novelty": 20, "audience_relevance": 22, "source_reliability": 18}'
    with patch.object(scoring_module, "complete", return_value=_fake_response(incomplete)):
        with pytest.raises(scoring_module.IdeaScoringError, match="missing required criterion"):
            scoring_module.score_idea(summary="A neat CLI tool for X.")


def test_score_idea_rejects_non_integer_criterion():
    bad = VALID_JSON.replace('"novelty": 20', '"novelty": "high"')
    with patch.object(scoring_module, "complete", return_value=_fake_response(bad)):
        with pytest.raises(scoring_module.IdeaScoringError, match="not an integer"):
            scoring_module.score_idea(summary="A neat CLI tool for X.")
