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


def test_run_deliberation_marks_partial_when_r1_completed():
    """If the engine fails after R1 produced outputs, the run should
    be marked 'partial' (not 'failed') so the UI knows R1 results are
    available for inspection.
    """
    with _patch_engine() as MockEngine, \
         patch("src.web.runner.update_run_status") as mock_status, \
         patch("src.web.runner.get_session"), \
         patch("src.web.runner._persist_r1_outputs"), \
         patch("src.web.runner._persist_final_report"):
        engine = MockEngine.return_value
        engine.run_round1.return_value = None
        engine.run_round2.side_effect = RuntimeError("R2 failed")
        engine.state.r1_outputs = {"market_analyst": {"tam": "100"}}
        engine.state.r3_report = None

        events = []
        with pytest.raises(RuntimeError):
            run_deliberation("run-1", "x", events.append)

    # The status call should have used 'partial' (because r1 has outputs).
    status_args = [c.args[2] for c in mock_status.call_args_list]
    assert "partial" in status_args

    # And the SSE event must include partial=True.
    failed_events = [e for e in events if e.get("type") == "run.failed"]
    assert failed_events, "no run.failed event published"
    assert failed_events[0]["partial"] is True


def test_run_deliberation_marks_failed_when_no_r1_output():
    """A crash before any R1 output lands means we have no partial
    results to expose, so the run is just 'failed'.
    """
    with _patch_engine() as MockEngine, \
         patch("src.web.runner.update_run_status") as mock_status, \
         patch("src.web.runner.get_session"), \
         patch("src.web.runner._persist_r1_outputs"), \
         patch("src.web.runner._persist_final_report"):
        engine = MockEngine.return_value
        engine.run_round1.side_effect = RuntimeError("LLM down at start")
        engine.state.r1_outputs = {}
        engine.state.r3_report = None

        events = []
        with pytest.raises(RuntimeError):
            run_deliberation("run-1", "x", events.append)

    status_args = [c.args[2] for c in mock_status.call_args_list]
    assert "failed" in status_args
    assert "partial" not in status_args

    failed_events = [e for e in events if e.get("type") == "run.failed"]
    assert failed_events[0]["partial"] is False


def test_run_deliberation_publishes_run_start():
    """run.start is the first event in the SSE stream so consumers can
    know the deliberation is live before the first agent.start arrives.
    """
    with _patch_engine() as MockEngine, \
         patch("src.web.runner.update_run_status"), \
         patch("src.web.runner.get_session"), \
         patch("src.web.runner._persist_r1_outputs"), \
         patch("src.web.runner._persist_final_report"):
        engine = MockEngine.return_value
        engine.run_round1.return_value = None
        engine.run_round2.return_value = []
        engine.run_round3.return_value = {"decision": "Go"}
        engine.state.r1_outputs = {}
        engine.state.r3_report = {"decision": "Go"}

        events = []
        run_deliberation("run-1", "AI Agent 平台", events.append)

    start_events = [e for e in events if e.get("type") == "run.start"]
    assert len(start_events) == 1
    assert start_events[0]["startup_idea"] == "AI Agent 平台"
    # run.start must be the first event in the stream so the UI can
    # confirm the run is alive immediately.
    assert events[0].get("type") == "run.start"


def test_resume_deliberation_publishes_failure_with_partial_flag():
    """If resume fails after R1 produced outputs, the run is partial and
    the SSE event must carry partial=True so the UI can offer a partial
    result view.
    """
    fake_run = MagicMock()
    fake_run.startup_idea = "AI Agent"
    with _patch_engine() as MockEngine, \
         patch("src.web.runner.update_run_status") as mock_status, \
         patch("src.web.runner.get_session"), \
         patch("src.web.runner._persist_r1_outputs"), \
         patch("src.web.runner._persist_final_report"), \
         patch("src.web.runner.get_run", return_value=fake_run):
        engine = MockEngine.return_value
        engine.resume.side_effect = RuntimeError("R2 boom")
        engine.state.r1_outputs = {"market_analyst": {"tam": "100"}}

        events = []
        with pytest.raises(RuntimeError):
            resume_deliberation("run-1", events.append)

    status_args = [c.args[2] for c in mock_status.call_args_list]
    assert "partial" in status_args
    failed = [e for e in events if e.get("type") == "run.failed"]
    assert failed[0]["partial"] is True
    assert "R2 boom" in failed[0]["error"]


def test_resume_deliberation_persists_r1_completed_during_resume():
    """If R1 finishes during a resume (e.g. crash on round 0), the
    runner should mirror the R1 outputs into the legacy column for
    frontend restoration.
    """
    fake_run = MagicMock()
    fake_run.startup_idea = "AI Agent"
    with _patch_engine() as MockEngine, \
         patch("src.web.runner.update_run_status"), \
         patch("src.web.runner.get_session"), \
         patch("src.web.runner._persist_r1_outputs") as mock_persist_r1, \
         patch("src.web.runner._persist_final_report"), \
         patch("src.web.runner.get_run", return_value=fake_run):
        engine = MockEngine.return_value
        engine.resume.return_value = {"decision": "Go"}
        # Simulate: pre-resume R1 was empty; resume added market_analyst.
        # We do this by tracking the dict identity: pre_r1 sees the
        # initial empty dict, then resume mutates it before _persist.
        engine.state.r1_outputs = {}
        engine.state.r3_report = {"decision": "Go"}

        # Make resume() add an entry to r1_outputs to mimic a fresh R1
        # finishing during resume.
        def fake_resume():
            engine.state.r1_outputs["market_analyst"] = {"tam": "100"}
            return {"decision": "Go"}
        engine.resume.side_effect = fake_resume

        resume_deliberation("run-1", lambda e: None)

    # _persist_r1_outputs must have been called for the legacy column
    mock_persist_r1.assert_called_once()
