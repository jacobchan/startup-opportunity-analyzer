"""Tests for the engine's safe template formatter."""

from src.deliberation.engine import _format_description, _SafeFormatDict


def test_safe_format_replaces_known_keys():
    out = _format_description(
        "Idea: {startup_idea}\nR1: {round1_outputs}",
        startup_idea="AI Agent",
        round1_outputs="{}",
    )
    assert "AI Agent" in out
    assert "{}" in out


def test_safe_format_leaves_unknown_placeholders_intact():
    out = _format_description(
        "Idea: {startup_idea}\nR2: {round2_challenges}",
        startup_idea="x",
    )
    assert "x" in out
    # Unknown placeholder preserved verbatim so the LLM still sees it.
    assert "{round2_challenges}" in out


def test_safe_format_empty_when_no_kwargs():
    out = _format_description("static {startup_idea}")
    assert out == "static {startup_idea}"


def test_safe_format_dict_returns_braced_placeholder_for_missing_key():
    d = _SafeFormatDict(startup_idea="x")
    assert d["startup_idea"] == "x"
    assert d["round1_outputs"] == "{round1_outputs}"


def test_parse_json_output_handles_markdown_fences():
    from src.deliberation.engine import _parse_json_output
    assert _parse_json_output('```json\n{"x": 1}\n```') == {"x": 1}


def test_parse_json_output_handles_plain_json():
    from src.deliberation.engine import _parse_json_output
    assert _parse_json_output('{"x": 1}') == {"x": 1}


def test_parse_json_output_returns_error_dict_on_invalid_json():
    from src.deliberation.engine import _parse_json_output
    out = _parse_json_output("not json at all")
    assert out["parse_error"] is True
    assert "not json" in out["raw_output"]
