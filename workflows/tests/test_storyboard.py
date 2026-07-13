"""workflows/storyboard.py — docs/roadmap.md Phase 3.7.

All tests mock the LLM call (workflows.storyboard.complete) — no real
network/API key needed, same reasoning as workflows/tests/
test_idea_scoring.py: this suite should run in CI without secrets.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

import workflows.storyboard as storyboard_module
from llm_provider import LLMError, LLMResponse

VALID_JSON = (
    '{"scenes": ['
    '{"order": 1, "description": "Terminal running the install command.", '
    '"duration": 4.5, "caption_cue": "npm install"}, '
    '{"order": 2, "description": "Browser showing the running app.", '
    '"duration": 6, "caption_cue": null}'
    "]}"
)


def _fake_response(text: str) -> LLMResponse:
    return LLMResponse(text=text, model="anthropic/claude-3-5-sonnet-20241022", input_tokens=200, output_tokens=100, cost_usd=0.002)


def test_generate_storyboard_returns_ordered_scenes():
    with patch.object(storyboard_module, "complete", return_value=_fake_response(VALID_JSON)) as mock_complete:
        result = storyboard_module.generate_storyboard(hook="Ever wanted X?", body="Here's how.", cta="Try it now.")

    mock_complete.assert_called_once()
    assert len(result.scenes) == 2
    assert result.scenes[0] == {
        "order": 1,
        "description": "Terminal running the install command.",
        "duration": 4.5,
        "caption_cue": "npm install",
        "visual_ref": None,
    }
    assert result.scenes[1]["caption_cue"] is None
    assert result.generated_by.startswith("storyboard@0.1.0:")
    assert result.cost_usd == 0.002
    assert result.tokens_used == 300


def test_generate_storyboard_renumbers_sequentially_regardless_of_stated_order():
    text = VALID_JSON.replace('"order": 1', '"order": 5').replace('"order": 2', '"order": 9')
    with patch.object(storyboard_module, "complete", return_value=_fake_response(text)):
        result = storyboard_module.generate_storyboard(hook="H", body="B")

    assert [s["order"] for s in result.scenes] == [1, 2]


def test_generate_storyboard_strips_markdown_code_fence():
    fenced = f"```json\n{VALID_JSON}\n```"
    with patch.object(storyboard_module, "complete", return_value=_fake_response(fenced)):
        result = storyboard_module.generate_storyboard(hook="H", body="B")

    assert len(result.scenes) == 2


def test_generate_storyboard_rejects_no_content():
    with pytest.raises(storyboard_module.StoryboardError, match="no hook, body, or cta"):
        storyboard_module.generate_storyboard(hook=None, body=None, cta=None)


def test_generate_storyboard_wraps_llm_error():
    with patch.object(storyboard_module, "complete", side_effect=LLMError("boom")):
        with pytest.raises(storyboard_module.StoryboardError, match="LLM call failed"):
            storyboard_module.generate_storyboard(hook="H", body="B")


def test_generate_storyboard_rejects_non_json_response():
    with patch.object(storyboard_module, "complete", return_value=_fake_response("not json at all")):
        with pytest.raises(storyboard_module.StoryboardError, match="not valid JSON"):
            storyboard_module.generate_storyboard(hook="H", body="B")


def test_generate_storyboard_rejects_empty_scenes_list():
    with patch.object(storyboard_module, "complete", return_value=_fake_response('{"scenes": []}')):
        with pytest.raises(storyboard_module.StoryboardError, match="no non-empty 'scenes' list"):
            storyboard_module.generate_storyboard(hook="H", body="B")


def test_generate_storyboard_rejects_missing_scenes_key():
    with patch.object(storyboard_module, "complete", return_value=_fake_response("{}")):
        with pytest.raises(storyboard_module.StoryboardError, match="no non-empty 'scenes' list"):
            storyboard_module.generate_storyboard(hook="H", body="B")


def test_generate_storyboard_rejects_too_many_scenes():
    scenes = [{"order": i, "description": "x", "duration": 1} for i in range(1, storyboard_module.MAX_SCENES + 2)]
    import json

    text = json.dumps({"scenes": scenes})
    with patch.object(storyboard_module, "complete", return_value=_fake_response(text)):
        with pytest.raises(storyboard_module.StoryboardError, match="over the"):
            storyboard_module.generate_storyboard(hook="H", body="B")


def test_generate_storyboard_rejects_scene_missing_description():
    with patch.object(
        storyboard_module, "complete", return_value=_fake_response('{"scenes": [{"order": 1, "duration": 2}]}')
    ):
        with pytest.raises(storyboard_module.StoryboardError, match="missing a non-empty 'description'"):
            storyboard_module.generate_storyboard(hook="H", body="B")


def test_generate_storyboard_rejects_non_numeric_duration():
    text = '{"scenes": [{"order": 1, "description": "d", "duration": "long"}]}'
    with patch.object(storyboard_module, "complete", return_value=_fake_response(text)):
        with pytest.raises(storyboard_module.StoryboardError, match="was not a number"):
            storyboard_module.generate_storyboard(hook="H", body="B")


def test_generate_storyboard_rejects_non_positive_duration():
    text = '{"scenes": [{"order": 1, "description": "d", "duration": 0}]}'
    with patch.object(storyboard_module, "complete", return_value=_fake_response(text)):
        with pytest.raises(storyboard_module.StoryboardError, match="must be positive"):
            storyboard_module.generate_storyboard(hook="H", body="B")
