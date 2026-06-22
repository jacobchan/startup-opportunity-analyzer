"""Tests for shared LLM factory."""

from unittest.mock import patch

from src.config.settings import build_llm


def test_build_llm_uses_deepseek_branch(monkeypatch):
    """When LLM_MODEL contains 'deepseek', build_llm routes through the
    DeepSeek-compatible constructor (api_key + base_url).
    """
    monkeypatch.setenv("LLM_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://example.com/v1")

    # build_llm imports LLM inside the function, so patch the source module.
    with patch("crewai.LLM") as MockLLM:
        MockLLM.return_value = "fake-llm"
        result = build_llm()

    MockLLM.assert_called_once_with(
        model="deepseek-v4-pro",
        api_key="test-key",
        base_url="https://example.com/v1",
    )
    assert result == "fake-llm"


def test_build_llm_falls_through_for_anthropic(monkeypatch):
    """Non-deepseek models just get the LLM(model=...) constructor."""
    monkeypatch.setenv("LLM_MODEL", "anthropic/claude-sonnet-4-6")

    with patch("crewai.LLM") as MockLLM:
        MockLLM.return_value = "anthropic-llm"
        result = build_llm()

    MockLLM.assert_called_once_with(model="anthropic/claude-sonnet-4-6")
    assert result == "anthropic-llm"
