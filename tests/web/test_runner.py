"""Tests for the background runner that drives the deliberation engine."""

from unittest.mock import MagicMock, patch

import pytest

from src.web.runner import run_deliberation, resume_deliberation


def _patch_engine():
    return patch("src.web.runner.DeliberationEngine")


def test_run_deliberation_invokes_rounds_in_order():
    with _patch_engine() as MockEngine, \
         patch("src.web.runner.update_run_status"), \
         patch("src.web.runner.get_session"), \
         patch("src.web.runner._persist_r1_outputs"), \
         patch("src.web.runner._persist_final_report"):
        engine = MockEngine.return_value
        engine.run_round1.return_value = None
        engine.run_round2.return_value = []
        engine.run_round3.return_value = {"decision": "Go"}
        engine.state.r1_outputs = {"market_analyst": {"tam": "100"}}
        engine.state.r3_report = {"decision": "Go"}

        events = []
        result = run_deliberation(
            run_id="run-1",
            startup_idea="AI Agent 平台",
            event_publisher=events.append,
        )

    assert engine.run_round1.called
    assert engine.run_round2.called
    assert engine.run_round3.called
    assert result["decision"] == "Go"
    assert any(e.get("type") == "run.complete" for e in events)


def test_run_deliberation_returns_final_report():
    with _patch_engine() as MockEngine, \
         patch("src.web.runner.update_run_status"), \
         patch("src.web.runner.get_session"), \
         patch("src.web.runner._persist_r1_outputs"), \
         patch("src.web.runner._persist_final_report"):
        engine = MockEngine.return_value
        engine.run_round1.return_value = None
        engine.run_round2.return_value = []
        engine.run_round3.return_value = {"decision": "No-Go"}
        engine.state.r1_outputs = {}
        engine.state.r3_report = {"decision": "No-Go"}

        result = run_deliberation("run-1", "x", lambda e: None)
    assert result["decision"] == "No-Go"


def test_run_deliberation_publishes_failure_on_exception():
    with _patch_engine() as MockEngine, \
         patch("src.web.runner.update_run_status"), \
         patch("src.web.runner.get_session"), \
         patch("src.web.runner._persist_r1_outputs"), \
         patch("src.web.runner._persist_final_report"):
        engine = MockEngine.return_value
        engine.run_round1.side_effect = RuntimeError("LLM down")

        events = []
        with pytest.raises(RuntimeError, match="LLM down"):
            run_deliberation("run-1", "x", events.append)

    assert any(e.get("type") == "run.failed" for e in events)


def test_resume_deliberation_returns_engine_report():
    fake_run = MagicMock()
    fake_run.startup_idea = "AI Agent"
    with _patch_engine() as MockEngine, \
         patch("src.web.runner.update_run_status"), \
         patch("src.web.runner.get_session"), \
         patch("src.web.runner._persist_r1_outputs"), \
         patch("src.web.runner._persist_final_report"), \
         patch("src.web.runner.get_run", return_value=fake_run):
        engine = MockEngine.return_value
        engine.resume.return_value = {"decision": "Conditional-Go"}
        engine.state.r1_outputs = {}
        engine.state.r3_report = {"decision": "Conditional-Go"}

        result = resume_deliberation("run-1", lambda e: None)
    assert result["decision"] == "Conditional-Go"


def test_resume_deliberation_raises_for_missing_run():
    with patch("src.web.runner.get_run", return_value=None):
        with pytest.raises(ValueError, match="not found"):
            resume_deliberation("run-missing", lambda e: None)
