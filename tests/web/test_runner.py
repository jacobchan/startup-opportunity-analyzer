from unittest.mock import MagicMock, patch


def test_run_deliberation_emits_round_transitions():
    with patch("src.crew.StartupAnalyzerCrew") as MockCrew, \
         patch("src.web.runner.update_run_status"), \
         patch("src.web.runner.get_session"):
        mock_instance = MagicMock()
        mock_instance.run_round1.return_value = {"market_analyst": {"tam": "100"}}
        mock_instance.run_round2.return_value = [{"challenge_id": "ch-1"}]
        mock_instance.run_round3.return_value = {"decision": "Go"}
        MockCrew.return_value = mock_instance

        events = []
        from src.web.runner import run_deliberation
        result = run_deliberation(
            run_id="run-1",
            startup_idea="AI Agent 平台",
            event_publisher=events.append,
        )

        transitions = [e.to_round for e in events if hasattr(e, "to_round")]
        assert transitions == ["round1", "round2", "round3"]
        assert result["decision"] == "Go"


def test_run_deliberation_returns_final_report():
    with patch("src.crew.StartupAnalyzerCrew") as MockCrew, \
         patch("src.web.runner.update_run_status"), \
         patch("src.web.runner.get_session"):
        mock_instance = MagicMock()
        mock_instance.run_round1.return_value = {}
        mock_instance.run_round2.return_value = []
        mock_instance.run_round3.return_value = {"decision": "No-Go"}
        MockCrew.return_value = mock_instance

        from src.web.runner import run_deliberation
        result = run_deliberation("run-1", "x", lambda e: None)
        assert "decision" in result
